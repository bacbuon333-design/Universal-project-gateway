"""Bounded, explicit context-pack compilation for one registered project."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from enum import Enum
from pathlib import Path
from typing import Any

from .evidence import redact as redact_evidence
from .scoped_fs import (
    ScopedFileError,
    is_reparse_point,
    normalize_relative_path,
    path_matches,
)
from .workspaces import DEFAULT_EXCLUDED_PATHS

DEFAULT_GATEWAY_RULES = (
    "Operate only inside the active isolated job workspace.",
    "Never access protected paths or credentials.",
    "Run only manifest-declared validation actions through a runtime adapter.",
    "Do not modify the registered source project during normal task execution.",
    "Do not merge, force-push, deploy, or commit to the default branch.",
    "Report commands and validation results exactly; never claim an unrun check passed.",
)
_SENSITIVE_NAMES = (
    ".env",
    ".env.*",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_ed25519",
    "*.pem",
    "*.key",
    "*.pfx",
    "*.p12",
)


class ContextCompiler:
    """Compile a deliberately incomplete, bounded view of a project."""

    def __init__(
        self,
        *,
        max_files: int = 500,
        max_total_bytes: int = 2_000_000,
        max_file_bytes: int = 128_000,
    ) -> None:
        if min(max_files, max_total_bytes, max_file_bytes) < 1:
            raise ValueError("context limits must be positive")
        self.max_files = max_files
        self.max_total_bytes = max_total_bytes
        self.max_file_bytes = max_file_bytes

    def compile(
        self,
        source_root: str | os.PathLike[str],
        manifest: Any,
        intent: Any,
        *,
        target_paths: Iterable[str] = (),
        gateway_rules: Iterable[str] = (),
        output_path: str | os.PathLike[str] | None = None,
    ) -> dict[str, Any]:
        source = Path(source_root).expanduser().resolve(strict=True)
        if not source.is_dir():
            raise ValueError("source_root must be a directory")
        target_paths = tuple(str(path) for path in target_paths)

        manifest_data = _plain(manifest)
        intent_data = _plain(intent)
        protected = tuple(_sequence_field(manifest, manifest_data, "protected_paths"))
        exclusions = tuple(dict.fromkeys((*DEFAULT_EXCLUDED_PATHS, *_SENSITIVE_NAMES)))
        omitted: list[dict[str, str]] = []
        tree: list[dict[str, Any]] = []
        files_by_relative: dict[str, Path] = {}
        truncated = False

        for path, reason in _walk_project(source, exclusions, protected):
            relative = path.relative_to(source).as_posix()
            if reason:
                omitted.append({"path": relative, "reason": reason})
                continue
            if len(tree) >= self.max_files:
                truncated = True
                omitted.append({"path": ".", "reason": "file_limit_reached"})
                break
            try:
                size = path.stat().st_size
            except OSError:
                omitted.append({"path": relative, "reason": "metadata_unavailable"})
                continue
            tree.append(
                {
                    "path": relative,
                    "type": "file",
                    "size": size,
                    "text": _looks_text(path, min(size, self.max_file_bytes + 1)),
                }
            )
            files_by_relative[relative] = path

        selected_requests = _selected_paths(manifest, manifest_data, intent, intent_data, target_paths)
        selected_files: list[dict[str, Any]] = []
        selected_seen: set[str] = set()
        total_bytes = 0
        for requested in selected_requests:
            try:
                relative = normalize_relative_path(requested)
            except ScopedFileError as exc:
                omitted.append({"path": str(requested), "reason": exc.code.lower()})
                continue
            if path_matches(relative, protected):
                omitted.append({"path": relative, "reason": "protected"})
                continue
            if path_matches(relative, exclusions):
                omitted.append({"path": relative, "reason": "excluded"})
                continue
            if relative in selected_seen:
                continue
            selected_seen.add(relative)
            path = files_by_relative.get(relative)
            if path is None:
                candidate = source.joinpath(*relative.split("/"))
                if candidate.is_dir() and not is_reparse_point(candidate):
                    # Directories remain represented by the bounded tree.  Do
                    # not recursively ingest them merely because they were named.
                    selected_files.append({"path": relative, "type": "directory", "content": None})
                else:
                    omitted.append({"path": relative, "reason": "not_found_or_not_regular"})
                continue
            size = path.stat().st_size
            if size > self.max_file_bytes:
                omitted.append({"path": relative, "reason": "per_file_byte_limit"})
                truncated = True
                continue
            if total_bytes + size > self.max_total_bytes:
                omitted.append({"path": relative, "reason": "total_byte_limit"})
                truncated = True
                continue
            data = path.read_bytes()
            if b"\x00" in data:
                omitted.append({"path": relative, "reason": "binary"})
                continue
            try:
                content = data.decode("utf-8")
            except UnicodeDecodeError:
                omitted.append({"path": relative, "reason": "non_utf8"})
                continue
            total_bytes += len(data)
            selected_files.append(
                {
                    "path": relative,
                    "type": "text",
                    "size": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "content": content,
                    "truncated": False,
                }
            )

        state_file = _single_field(manifest, manifest_data, "state_file")
        project_state: Any = None
        if isinstance(state_file, str):
            for selected in selected_files:
                if selected["path"] == state_file and selected.get("content") is not None:
                    try:
                        project_state = json.loads(selected["content"])
                    except json.JSONDecodeError:
                        project_state = {"format": "text", "content": selected["content"]}
                    break

        git_context = _git_context(source)
        if git_context.get("changed_paths"):
            git_context["changed_paths"] = [
                path
                for path in git_context["changed_paths"]
                if not path_matches(path, protected) and not path_matches(path, _SENSITIVE_NAMES)
            ]

        pack: dict[str, Any] = {
            "schema_version": 1,
            "gateway_rules": list(gateway_rules) or list(DEFAULT_GATEWAY_RULES),
            "project_manifest": _redact(manifest_data),
            "project_memory": [
                _redact(item)
                for item in selected_files
                if item["path"] in set(_sequence_field(manifest, manifest_data, "memory_files"))
            ],
            "project_state": _redact(project_state),
            "project_tree": tree,
            "selected_files": [_redact(item) for item in selected_files],
            "requested_target_paths": list(
                _target_paths(intent, intent_data, target_paths)
            ),
            "task_intent": _redact(intent_data),
            "protected_paths": list(protected),
            "required_validation": list(
                _sequence_field(manifest, manifest_data, "validation_requirements")
            ),
            "publication_policy": _redact(
                _single_field(manifest, manifest_data, "publication_policy") or {}
            ),
            "source_git": git_context,
            "limits": {
                "max_files": self.max_files,
                "max_total_bytes": self.max_total_bytes,
                "max_file_bytes": self.max_file_bytes,
                "files_in_tree": len(tree),
                "selected_content_bytes": total_bytes,
            },
            "truncated": truncated,
            "omitted_paths": sorted(
                _deduplicate_omissions(omitted), key=lambda item: (item["path"], item["reason"])
            ),
            "scope_statement": (
                "This is a bounded context pack, not a claim of full-repository understanding."
            ),
        }
        if output_path is not None:
            _write_json_atomic(Path(output_path), pack)
        return pack


# The longer name mirrors the architecture document while the shorter name is
# convenient at service call sites.
ContextPackCompiler = ContextCompiler


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if dataclasses.is_dataclass(value):
        return _plain(dataclasses.asdict(value))
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _plain(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(item) for item in value]
    return value


def _single_field(obj: Any, plain: Any, name: str) -> Any:
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(plain, Mapping):
        return plain.get(name)
    return None


def _sequence_field(obj: Any, plain: Any, name: str) -> tuple[str, ...]:
    value = _single_field(obj, plain, name)
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (list, tuple)):
        return tuple(str(item) for item in value if isinstance(item, (str, Path)))
    return ()


def _target_paths(intent: Any, plain: Any, explicit: Iterable[str]) -> tuple[str, ...]:
    explicit_tuple = tuple(str(path) for path in explicit)
    target_scope = _sequence_field(intent, plain, "target_scope")
    return tuple(dict.fromkeys((*explicit_tuple, *target_scope)))


def _selected_paths(
    manifest: Any,
    manifest_plain: Any,
    intent: Any,
    intent_plain: Any,
    explicit: Iterable[str],
) -> tuple[str, ...]:
    values: list[str] = []
    for field in ("memory_files", "important_paths"):
        values.extend(_sequence_field(manifest, manifest_plain, field))
    state_file = _single_field(manifest, manifest_plain, "state_file")
    if isinstance(state_file, str):
        values.append(state_file)
    values.extend(_target_paths(intent, intent_plain, explicit))
    return tuple(dict.fromkeys(values))


def _walk_project(
    root: Path,
    exclusions: tuple[str, ...],
    protected: tuple[str, ...],
) -> Iterator[tuple[Path, str | None]]:
    def visit(directory: Path) -> Iterator[tuple[Path, str | None]]:
        for entry in sorted(os.scandir(directory), key=lambda item: item.name.casefold()):
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if path_matches(relative, protected):
                yield path, "protected"
                continue
            if path_matches(relative, exclusions) or any(
                path_matches(part, DEFAULT_EXCLUDED_PATHS) for part in relative.split("/")
            ):
                yield path, "excluded"
                continue
            if is_reparse_point(path):
                yield path, "link_or_reparse_point"
                continue
            if path.is_dir():
                yield from visit(path)
            elif path.is_file():
                yield path, None
            else:
                yield path, "not_regular_file"

    yield from visit(root)


def _looks_text(path: Path, read_limit: int) -> bool:
    try:
        with path.open("rb") as stream:
            sample = stream.read(min(read_limit, 8_192))
    except OSError:
        return False
    if b"\x00" in sample:
        return False
    try:
        sample.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _git_context(root: Path) -> dict[str, Any]:
    git = shutil.which("git")
    result: dict[str, Any] = {
        "is_repository": False,
        "revision": None,
        "branch": None,
        "dirty": False,
        "changed_paths": [],
    }
    if not git:
        result["availability"] = "git_not_found"
        return result
    revision = _run_git(git, root, ["rev-parse", "--verify", "HEAD"])
    if revision[0] != 0:
        result["availability"] = "not_a_repository"
        return result
    branch = _run_git(git, root, ["branch", "--show-current"])
    status = _run_git(git, root, ["status", "--porcelain=v1", "-z"])
    changed: list[str] = []
    if status[0] == 0:
        records = [record for record in status[1].split("\x00") if record]
        index = 0
        while index < len(records):
            record = records[index]
            value = record[3:] if len(record) >= 4 else record
            if record[:2] in {"R ", " R", "C ", " C"} and index + 1 < len(records):
                index += 1
                value = records[index]
            changed.append(value.replace("\\", "/"))
            index += 1
    result.update(
        {
            "is_repository": True,
            "revision": revision[1].strip(),
            "branch": branch[1].strip() if branch[0] == 0 else None,
            "dirty": bool(changed),
            "changed_paths": sorted(dict.fromkeys(changed)),
            "availability": "available",
        }
    )
    return result


def _run_git(git: str, root: Path, arguments: list[str]) -> tuple[int, str]:
    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "HOME", "USERPROFILE")
        if key in os.environ
    }
    environment["GIT_TERMINAL_PROMPT"] = "0"
    try:
        completed = subprocess.run(
            [git, *arguments],
            cwd=root,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.SubprocessError):
        return 1, ""
    return completed.returncode, completed.stdout


def _redact(value: Any) -> Any:
    return redact_evidence(value)


def _deduplicate_omissions(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for item in items:
        key = (item["path"], item["reason"])
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".upg-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


__all__ = ["ContextCompiler", "ContextPackCompiler", "DEFAULT_GATEWAY_RULES"]
