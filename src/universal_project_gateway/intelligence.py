"""Deterministic, bounded project-intelligence summaries and cache storage.

The scanner consumes only a validated manifest and filesystem metadata/content
hashes.  It never imports project modules, runs project commands, follows links,
or reads protected paths.  Cached documents use project-relative paths so their
semantic hashes do not depend on the host checkout location.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .config import GatewayConfig
from .contracts import PROJECT_INTELLIGENCE_CONTRACT_VERSION
from .models import GatewayError, ProjectManifest, utc_now
from .runtime import AdapterRegistry, built_in_adapter_registry
from .scoped_fs import ScopedFileError, is_reparse_point, normalize_relative_path, path_matches
from .workspaces import DEFAULT_EXCLUDED_PATHS

HASH_ALGORITHM = "sha256"
DEFAULT_MAX_FILES = 2_000
DEFAULT_MAX_HASH_BYTES = 32_000_000
DEFAULT_MAX_FILE_BYTES = 2_000_000
MAX_CACHE_BYTES = 2_000_000
_SUMMARY_LIMIT = 100
_SENSITIVE_PATHS = (
    ".env",
    ".env.*",
    "credentials.json",
    "secrets.json",
    "secrets/",
    "credentials/",
    "*.key",
    "*.pem",
    "*.pfx",
    "*.p12",
)
_DEPENDENCY_FILES = {
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "poetry.lock",
    "pdm.lock",
    "uv.lock",
    "pipfile",
    "pipfile.lock",
    "package.json",
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
}
_DOC_NAMES = {"readme", "agents.md", "current_state.json"}
_PYTHON_SUFFIXES = {".py", ".pyi"}
_NODE_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
_GENERIC_SUFFIXES = {
    *_PYTHON_SUFFIXES,
    *_NODE_SUFFIXES,
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".kt",
    ".php",
    ".rb",
    ".rs",
    ".swift",
}


class ProjectIntelligenceError(GatewayError):
    """Structured cache or bounded-scan failure."""

    default_code = "PROJECT_INTELLIGENCE_ERROR"


def canonical_json(value: Any) -> str:
    """Serialize JSON with the canonical rules used for intelligence hashes."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _semantic_cache_hash(document: Mapping[str, Any]) -> str:
    material = {
        key: value
        for key, value in document.items()
        if key not in {"cache_hash", "generated_at"}
    }
    return canonical_sha256(material)


def _command_map(
    manifest: ProjectManifest, actions: Iterable[str]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for action in actions:
        command = manifest.command(action)
        if command is not None:
            result[action] = command.to_dict()
    return result


def _relative_manifest_path(manifest: ProjectManifest) -> str:
    if manifest.manifest_path is None:
        return "PROJECT_MANIFEST.yaml"
    try:
        return manifest.manifest_path.relative_to(manifest.local_path).as_posix()
    except ValueError as exc:
        raise ProjectIntelligenceError(
            "manifest must be contained by its registered source root",
            code="INTELLIGENCE_MANIFEST_OUTSIDE_SOURCE",
        ) from exc


def _managed_path_groups(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, list[str]] = {}
    for name, raw_paths in value.items():
        if not isinstance(name, str) or not isinstance(raw_paths, (list, tuple)):
            continue
        paths: list[str] = []
        for raw_path in raw_paths:
            if not isinstance(raw_path, str):
                continue
            try:
                paths.append(normalize_relative_path(raw_path))
            except ScopedFileError:
                continue
        if paths:
            result[name] = list(dict.fromkeys(paths))
    return result


def _dependency_manager_hint(value: Any) -> str | None:
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        return None
    if any(character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._- " for character in value):
        return None
    return value


class ProjectIntelligenceScanner:
    """Build compact rule-based summaries from one registered source tree."""

    def __init__(
        self,
        *,
        adapter_registry: AdapterRegistry | None = None,
        max_files: int = DEFAULT_MAX_FILES,
        max_hash_bytes: int = DEFAULT_MAX_HASH_BYTES,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    ) -> None:
        if min(max_files, max_hash_bytes, max_file_bytes) < 1:
            raise ValueError("project intelligence scan limits must be positive")
        self.adapter_registry = adapter_registry or built_in_adapter_registry()
        self.max_files = max_files
        self.max_hash_bytes = max_hash_bytes
        self.max_file_bytes = max_file_bytes

    def scan(self, manifest: ProjectManifest) -> dict[str, Any]:
        root = manifest.local_path.resolve(strict=True)
        if not root.is_dir() or is_reparse_point(root):
            raise ProjectIntelligenceError(
                "registered source root must be a real directory",
                code="INTELLIGENCE_SOURCE_INVALID",
            )
        files, omitted, hashed_bytes, truncated = self._scan_files(
            root, manifest.protected_paths
        )
        relative_paths = [item["path"] for item in files]
        dependency_files = sorted(
            path
            for path in relative_paths
            if "/" not in path and Path(path).name.casefold() in _DEPENDENCY_FILES
        )
        adapters = []
        for adapter_id in manifest.runtime_adapters:
            capability = self.adapter_registry.get(adapter_id)
            adapters.append(capability.to_dict())

        manifest_path = _relative_manifest_path(manifest)
        fingerprint_material = {
            "schema_version": PROJECT_INTELLIGENCE_CONTRACT_VERSION,
            "project_id": manifest.project_id,
            "manifest_path": manifest_path,
            "files": files,
            "omitted": omitted,
            "limits": {
                "max_files": self.max_files,
                "max_hash_bytes": self.max_hash_bytes,
                "max_file_bytes": self.max_file_bytes,
                "truncated": truncated,
            },
        }
        source_fingerprint = canonical_sha256(fingerprint_material)
        managed_groups = _managed_path_groups(manifest.stack.get("managed_path_groups", {}))
        document: dict[str, Any] = {
            "schema_version": PROJECT_INTELLIGENCE_CONTRACT_VERSION,
            "hash_algorithm": HASH_ALGORITHM,
            "project_id": manifest.project_id,
            "project_name": manifest.name,
            "project_type": manifest.project_type,
            "manifest_path": manifest_path,
            "source_root": ".",
            "important_paths": list(manifest.important_paths),
            "managed_path_groups": managed_groups,
            "protected_paths": list(manifest.protected_paths),
            "entrypoints": dict(manifest.entrypoints),
            "test_commands": _command_map(manifest, ("lint", "test", "smoke_test")),
            "build_commands": _command_map(manifest, ("build",)),
            "validation_commands": _command_map(
                manifest, manifest.validation_requirements
            ),
            "runtime_adapters": list(manifest.runtime_adapters),
            "adapter_capabilities": adapters,
            "dependency_files": dependency_files,
            "dependency_hints": {
                "declared_manager": _dependency_manager_hint(
                    manifest.stack.get("dependency_manager")
                ),
                "files": dependency_files,
                "automatic_installation": False,
            },
            "module_summary": self._module_summary(manifest.project_type, relative_paths),
            "test_summary": self._test_summary(relative_paths, managed_groups),
            "docs_summary": self._docs_summary(relative_paths, managed_groups),
            "risk_notes": self._risk_notes(manifest, truncated, omitted),
            "scan": {
                "files_fingerprinted": len(files),
                "bytes_hashed": hashed_bytes,
                "omitted_path_count": len(omitted),
                "truncated": truncated,
                "limits": {
                    "max_files": self.max_files,
                    "max_hash_bytes": self.max_hash_bytes,
                    "max_file_bytes": self.max_file_bytes,
                },
            },
            "generated_at": utc_now(),
            "source_fingerprint": source_fingerprint,
        }
        document["cache_hash"] = _semantic_cache_hash(document)
        return document

    def _scan_files(
        self, root: Path, protected: tuple[str, ...]
    ) -> tuple[list[dict[str, Any]], list[dict[str, str]], int, bool]:
        files: list[dict[str, Any]] = []
        omitted: list[dict[str, str]] = []
        hashed_bytes = 0
        truncated = False

        def visit(directory: Path) -> bool:
            nonlocal hashed_bytes, truncated
            try:
                entries = sorted(os.scandir(directory), key=lambda item: item.name.casefold())
            except OSError:
                relative = directory.relative_to(root).as_posix() or "."
                omitted.append({"path": relative, "reason": "metadata_unavailable"})
                return True
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                if (
                    path_matches(relative, protected)
                    or path_matches(relative, _SENSITIVE_PATHS)
                    or any(
                        path_matches(part, (*DEFAULT_EXCLUDED_PATHS, *_SENSITIVE_PATHS))
                        for part in relative.split("/")
                    )
                ):
                    omitted.append({"path": relative, "reason": "protected_or_excluded"})
                    continue
                if is_reparse_point(path):
                    omitted.append({"path": relative, "reason": "link_or_reparse_point"})
                    continue
                try:
                    if entry.is_dir(follow_symlinks=False):
                        if not visit(path):
                            return False
                        continue
                    if not entry.is_file(follow_symlinks=False):
                        omitted.append({"path": relative, "reason": "not_regular_file"})
                        continue
                    size = entry.stat(follow_symlinks=False).st_size
                except OSError:
                    omitted.append({"path": relative, "reason": "metadata_unavailable"})
                    continue
                if len(files) >= self.max_files:
                    truncated = True
                    omitted.append({"path": ".", "reason": "file_limit_reached"})
                    return False
                if size > self.max_file_bytes:
                    files.append(
                        {
                            "path": relative,
                            "size": size,
                            "sha256": canonical_sha256(
                                {"path": relative, "size": size, "content": "not_hashed"}
                            ),
                            "content_hashed": False,
                        }
                    )
                    omitted.append({"path": relative, "reason": "per_file_hash_limit"})
                    continue
                if hashed_bytes + size > self.max_hash_bytes:
                    truncated = True
                    files.append(
                        {
                            "path": relative,
                            "size": size,
                            "sha256": canonical_sha256(
                                {"path": relative, "size": size, "content": "not_hashed"}
                            ),
                            "content_hashed": False,
                        }
                    )
                    omitted.append({"path": relative, "reason": "total_hash_limit"})
                    continue
                digest = hashlib.sha256()
                try:
                    with path.open("rb") as stream:
                        for chunk in iter(lambda: stream.read(128_000), b""):
                            digest.update(chunk)
                except OSError:
                    omitted.append({"path": relative, "reason": "content_unavailable"})
                    continue
                hashed_bytes += size
                files.append(
                    {
                        "path": relative,
                        "size": size,
                        "sha256": digest.hexdigest(),
                        "content_hashed": True,
                    }
                )
            return True

        visit(root)
        return files, sorted(omitted, key=lambda item: (item["path"], item["reason"])), hashed_bytes, truncated

    @staticmethod
    def _module_summary(project_type: str, paths: list[str]) -> dict[str, Any]:
        suffixes = (
            _PYTHON_SUFFIXES
            if project_type == "python"
            else (_NODE_SUFFIXES if project_type == "node" else _GENERIC_SUFFIXES)
        )
        source_files = [
            path
            for path in paths
            if Path(path).suffix.casefold() in suffixes
            and path.startswith("src/")
        ]
        packages: set[str] = set()
        modules: list[str] = []
        for path in source_files:
            parts = path.split("/")
            source_index = 0
            if source_index + 1 < len(parts):
                packages.add(parts[source_index + 1].split(".", 1)[0])
            modules.append(path)
        return {
            "language_family": project_type,
            "source_file_count": len(source_files),
            "top_level_packages": sorted(packages)[:_SUMMARY_LIMIT],
            "module_paths": sorted(modules)[:_SUMMARY_LIMIT],
            "truncated": len(modules) > _SUMMARY_LIMIT,
        }

    @staticmethod
    def _test_summary(
        paths: list[str], managed_groups: Mapping[str, list[str]]
    ) -> dict[str, Any]:
        declared = managed_groups.get("tests", [])
        test_roots = tuple(declared) if declared else ("tests", "test", "spec")
        tests = sorted(
            path
            for path in paths
            if path_matches(path, test_roots)
        )
        by_extension = Counter(Path(path).suffix.casefold() or "[none]" for path in tests)
        return {
            "file_count": len(tests),
            "by_extension": dict(sorted(by_extension.items())),
            "paths": tests[:_SUMMARY_LIMIT],
            "truncated": len(tests) > _SUMMARY_LIMIT,
        }

    @staticmethod
    def _docs_summary(
        paths: list[str], managed_groups: Mapping[str, list[str]]
    ) -> dict[str, Any]:
        declared = managed_groups.get("documentation", [])
        docs = sorted(
            path
            for path in paths
            if (declared and path_matches(path, declared))
            or ("/" not in path and Path(path).name.casefold() == "agents.md")
            or (
                not declared
                and (
                    path.casefold().startswith("docs/")
                    or ("/" not in path and Path(path).name.casefold() in _DOC_NAMES)
                    or ("/" not in path and Path(path).stem.casefold() == "readme")
                )
            )
        )
        return {
            "file_count": len(docs),
            "paths": docs[:_SUMMARY_LIMIT],
            "truncated": len(docs) > _SUMMARY_LIMIT,
        }

    @staticmethod
    def _risk_notes(
        manifest: ProjectManifest,
        truncated: bool,
        omitted: list[dict[str, str]],
    ) -> list[str]:
        notes = [
            "Rule-based metadata summary only; no project code was executed.",
            "Protected, sensitive, excluded, and linked paths were not read.",
            "Dependency hints do not authorize installation or network access.",
        ]
        if manifest.protected_paths:
            notes.append(
                f"Manifest protects {len(manifest.protected_paths)} path pattern(s)."
            )
        if truncated:
            notes.append("The bounded fingerprint scan reached a configured limit.")
        if omitted:
            notes.append(f"The scan omitted {len(omitted)} path(s) or metadata entries.")
        return notes


class ProjectIntelligenceCache:
    """Store verified intelligence documents only in Gateway-owned state."""

    def __init__(
        self,
        config: GatewayConfig,
        *,
        scanner: ProjectIntelligenceScanner | None = None,
    ) -> None:
        self.root = config.intelligence_cache_root.resolve()
        self.scanner = scanner or ProjectIntelligenceScanner(
            max_files=max(config.context_max_files * 4, DEFAULT_MAX_FILES),
            max_hash_bytes=max(config.context_max_bytes * 16, DEFAULT_MAX_HASH_BYTES),
            max_file_bytes=config.max_text_file_bytes * 2,
        )

    def path_for(self, project_id: str) -> Path:
        if not project_id or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789_-"
            for character in project_id
        ):
            raise ProjectIntelligenceError(
                "project_id is not safe for cache storage",
                code="INTELLIGENCE_PROJECT_ID_INVALID",
            )
        return self.root / f"{project_id}.json"

    def generate(self, manifest: ProjectManifest) -> dict[str, Any]:
        document = self.scanner.scan(manifest)
        path = self.path_for(manifest.project_id)
        self._write_atomic(path, document)
        return self._result(path, document)

    def get(self, project_id: str) -> dict[str, Any]:
        path = self.path_for(project_id)
        if not path.is_file() or is_reparse_point(path):
            raise ProjectIntelligenceError(
                "project intelligence cache has not been generated",
                code="PROJECT_INTELLIGENCE_NOT_FOUND",
                details={"project_id": project_id},
            )
        return self._result(path, self._read_verified(path, project_id))

    def get_or_generate(self, manifest: ProjectManifest) -> dict[str, Any]:
        try:
            return self.get(manifest.project_id)
        except ProjectIntelligenceError as exc:
            if exc.code != "PROJECT_INTELLIGENCE_NOT_FOUND":
                raise
        return self.generate(manifest)

    def list(self) -> list[dict[str, Any]]:
        if not self.root.is_dir() or is_reparse_point(self.root):
            return []
        results: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.json"), key=lambda item: item.name.casefold()):
            if is_reparse_point(path) or not path.is_file():
                continue
            project_id = path.stem
            document = self._read_verified(path, project_id)
            results.append(
                {
                    "project_id": document["project_id"],
                    "project_name": document["project_name"],
                    "project_type": document["project_type"],
                    "schema_version": document["schema_version"],
                    "source_fingerprint": document["source_fingerprint"],
                    "cache_hash": document["cache_hash"],
                    "generated_at": document["generated_at"],
                    "cache_path": str(path),
                }
            )
        return results

    @staticmethod
    def compact(result: Mapping[str, Any]) -> dict[str, Any]:
        raw = result.get("intelligence", result)
        if not isinstance(raw, Mapping):
            raise ProjectIntelligenceError("invalid intelligence result")
        return {
            "schema_version": raw.get("schema_version"),
            "project_id": raw.get("project_id"),
            "project_type": raw.get("project_type"),
            "cache_hash": raw.get("cache_hash"),
            "source_fingerprint": raw.get("source_fingerprint"),
            "important_paths": list(raw.get("important_paths", ()))[:25],
            "entrypoints": dict(raw.get("entrypoints", {})),
            "runtime_adapters": list(raw.get("runtime_adapters", ())),
            "dependency_files": list(raw.get("dependency_files", ()))[:25],
            "module_summary": dict(raw.get("module_summary", {})),
            "test_summary": dict(raw.get("test_summary", {})),
            "docs_summary": dict(raw.get("docs_summary", {})),
            "risk_notes": list(raw.get("risk_notes", ())),
            "scope_statement": "Compact cached metadata; not full-repository understanding.",
        }

    @staticmethod
    def _result(path: Path, document: Mapping[str, Any]) -> dict[str, Any]:
        return {"cache_path": str(path), "intelligence": dict(document)}

    @staticmethod
    def _read_verified(path: Path, project_id: str) -> dict[str, Any]:
        try:
            if path.stat().st_size > MAX_CACHE_BYTES:
                raise ProjectIntelligenceError(
                    "project intelligence cache exceeds its size limit",
                    code="PROJECT_INTELLIGENCE_CACHE_INVALID",
                )
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ProjectIntelligenceError(
                "project intelligence cache cannot be read",
                code="PROJECT_INTELLIGENCE_CACHE_INVALID",
            ) from exc
        digest_fields_valid = all(
            isinstance(document.get(field), str)
            and len(document[field]) == 64
            and all(character in "0123456789abcdef" for character in document[field])
            for field in ("cache_hash", "source_fingerprint")
        ) if isinstance(document, dict) else False
        if not isinstance(document, dict) or (
            document.get("schema_version") != PROJECT_INTELLIGENCE_CONTRACT_VERSION
            or document.get("project_id") != project_id
            or document.get("hash_algorithm") != HASH_ALGORITHM
            or not isinstance(document.get("project_name"), str)
            or not isinstance(document.get("project_type"), str)
            or not isinstance(document.get("generated_at"), str)
            or not digest_fields_valid
            or document.get("cache_hash") != _semantic_cache_hash(document)
        ):
            raise ProjectIntelligenceError(
                "project intelligence cache failed schema or hash verification",
                code="PROJECT_INTELLIGENCE_CACHE_INVALID",
                details={"project_id": project_id},
            )
        return document

    def _write_atomic(self, path: Path, document: Mapping[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".upg-intel-", dir=self.root)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(document, stream, sort_keys=True, indent=2, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


__all__ = [
    "HASH_ALGORITHM",
    "ProjectIntelligenceCache",
    "ProjectIntelligenceError",
    "ProjectIntelligenceScanner",
    "canonical_json",
    "canonical_sha256",
]
