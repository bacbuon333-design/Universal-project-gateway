"""Creation and comparison of isolated per-job workspaces."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import GatewayError
from .scoped_fs import is_reparse_point, path_matches

DEFAULT_EXCLUDED_PATHS = (
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "dist",
    "build",
    "coverage",
    ".coverage",
    "artifacts",
    "workspaces",
    "var",
)
_SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WINDOWS_RESERVED_JOB_IDS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_WINDOWS_STARTUPINFO = getattr(subprocess, "STARTUPINFO", None)


class WorkspaceError(GatewayError):
    default_code = "WORKSPACE_ERROR"


@dataclass(frozen=True, slots=True)
class SnapshotFile:
    path: str
    size: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    job_id: str
    source_root: Path
    workspace_root: Path
    baseline_root: Path
    source_revision: str | None
    files: tuple[SnapshotFile, ...]
    omitted_paths: tuple[dict[str, str], ...]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source_root": str(self.source_root),
            "workspace_root": str(self.workspace_root),
            "source_revision": self.source_revision,
            "files": [item.to_dict() for item in self.files],
            "omitted_paths": list(self.omitted_paths),
            "created_at": self.created_at,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceDiff:
    patch: str
    files_changed: tuple[dict[str, Any], ...]
    stale_source_warning: bool
    stale_source_details: Mapping[str, Any]

    @property
    def changed(self) -> bool:
        return bool(self.files_changed)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patch": self.patch,
            "files_changed": list(self.files_changed),
            "stale_source_warning": self.stale_source_warning,
            "stale_source_details": dict(self.stale_source_details),
        }

    def __str__(self) -> str:
        return self.patch


class WorkspaceManager:
    """Own job directories beneath a configured gateway workspace root."""

    def __init__(self, workspaces_root: str | os.PathLike[str]) -> None:
        self.root = Path(workspaces_root).expanduser().resolve()

    @staticmethod
    def _validate_job_id(job_id: str) -> str:
        if (
            not isinstance(job_id, str)
            or not _SAFE_JOB_ID.fullmatch(job_id)
            or job_id in {".", ".."}
            or job_id.endswith(".")
            or ".." in job_id
            or job_id.split(".", 1)[0].upper() in _WINDOWS_RESERVED_JOB_IDS
        ):
            raise WorkspaceError(
                "job_id must be a filesystem-safe identifier",
                code="INVALID_JOB_ID",
                details={"job_id": str(job_id)},
            )
        return job_id

    def job_root(self, job_id: str) -> Path:
        safe_id = self._validate_job_id(job_id)
        candidate = self.root / safe_id
        resolved = candidate.resolve(strict=False)
        if resolved.parent != self.root:
            raise WorkspaceError("job path escaped workspace root", code="WORKSPACE_PATH_ESCAPE")
        return candidate

    def workspace_path(self, job_id: str) -> Path:
        return self.job_root(job_id) / "workspace"

    def baseline_path(self, job_id: str) -> Path:
        return self.job_root(job_id) / "baseline"

    def metadata_path(self, job_id: str) -> Path:
        return self.job_root(job_id) / "workspace.json"

    def create(
        self,
        job_id: str,
        source_root: str | os.PathLike[str],
        *,
        protected_paths: Iterable[str] = (),
        ignored_paths: Iterable[str] = (),
    ) -> WorkspaceSnapshot:
        """Copy a source tree into an immutable baseline and editable workspace.

        Existing job directories are refused instead of being silently removed.
        Symlinks, junctions, protected paths, dependencies, and build outputs are
        omitted from both copies.
        """

        safe_id = self._validate_job_id(job_id)
        source = Path(source_root).expanduser().resolve(strict=True)
        if not source.is_dir():
            raise WorkspaceError(
                "registered project source must be a directory",
                code="SOURCE_NOT_DIRECTORY",
                details={"source_root": str(source)},
            )
        job_root = self.job_root(safe_id)
        if job_root.exists():
            raise WorkspaceError(
                "a workspace already exists for this job",
                code="WORKSPACE_ALREADY_EXISTS",
                details={"job_id": safe_id},
            )
        self.root.mkdir(parents=True, exist_ok=True)

        patterns = tuple(
            dict.fromkeys((*DEFAULT_EXCLUDED_PATHS, *ignored_paths, *protected_paths))
        )
        staging = Path(tempfile.mkdtemp(prefix=f".{safe_id}-", dir=self.root))
        baseline = staging / "baseline"
        workspace = staging / "workspace"
        omitted: list[dict[str, str]] = []
        try:
            baseline.mkdir()
            self._copy_tree(source, baseline, patterns, omitted)
            workspace.mkdir()
            # The baseline was produced without links, so this second copy cannot
            # escape and ensures the diff has an immutable reference tree.
            self._copy_tree(baseline, workspace, (), [])
            files = tuple(self._snapshot_tree(baseline))
            created_at = datetime.now(UTC).isoformat(timespec="milliseconds").replace(
                "+00:00", "Z"
            )
            source_revision = _git_revision(source)
            metadata = {
                "schema_version": 1,
                "job_id": safe_id,
                "source_root": str(source),
                "source_revision": source_revision,
                "created_at": created_at,
                "exclude_patterns": list(patterns),
                "files": [item.to_dict() for item in files],
                "omitted_paths": sorted(omitted, key=lambda item: (item["path"], item["reason"])),
            }
            _write_json_atomic(staging / "workspace.json", metadata)
            # A rename on one volume makes the job become visible as a complete
            # unit, never as a partially copied workspace.
            staging.rename(job_root)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise

        return WorkspaceSnapshot(
            job_id=safe_id,
            source_root=source,
            workspace_root=job_root / "workspace",
            baseline_root=job_root / "baseline",
            source_revision=source_revision,
            files=files,
            omitted_paths=tuple(metadata["omitted_paths"]),
            created_at=created_at,
        )

    # Compatibility spelling used by some service layers.
    create_workspace = create

    @classmethod
    def _copy_tree(
        cls,
        source: Path,
        destination: Path,
        excluded_patterns: Iterable[str],
        omitted: list[dict[str, str]],
    ) -> None:
        destination.mkdir(parents=True, exist_ok=True)
        for entry in sorted(os.scandir(source), key=lambda item: item.name.casefold()):
            source_path = Path(entry.path)
            relative = source_path.relative_to(source).as_posix()
            # The recursive helper receives a new root, so preserve a logical
            # prefix in the nested implementation below.
            cls._copy_entry(
                original_root=source,
                source_path=source_path,
                destination_root=destination,
                relative=relative,
                excluded_patterns=tuple(excluded_patterns),
                omitted=omitted,
            )

    @classmethod
    def _copy_entry(
        cls,
        *,
        original_root: Path,
        source_path: Path,
        destination_root: Path,
        relative: str,
        excluded_patterns: tuple[str, ...],
        omitted: list[dict[str, str]],
    ) -> None:
        del original_root  # documents that relative is anchored by the caller
        if path_matches(relative, excluded_patterns) or any(
            path_matches(part, DEFAULT_EXCLUDED_PATHS) for part in relative.split("/")
        ):
            omitted.append({"path": relative, "reason": "excluded"})
            return
        if is_reparse_point(source_path):
            omitted.append({"path": relative, "reason": "link_or_reparse_point"})
            return
        destination = destination_root.joinpath(*relative.split("/"))
        try:
            if source_path.is_dir():
                destination.mkdir(parents=True, exist_ok=True)
                for entry in sorted(os.scandir(source_path), key=lambda item: item.name.casefold()):
                    child = Path(entry.path)
                    child_relative = f"{relative}/{entry.name}"
                    cls._copy_entry(
                        original_root=source_path,
                        source_path=child,
                        destination_root=destination_root,
                        relative=child_relative,
                        excluded_patterns=excluded_patterns,
                        omitted=omitted,
                    )
            elif source_path.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination, follow_symlinks=False)
            else:
                omitted.append({"path": relative, "reason": "not_regular_file"})
        except OSError as exc:
            raise WorkspaceError(
                "source project could not be copied safely",
                code="WORKSPACE_COPY_FAILED",
                details={"path": relative, "error": str(exc)},
            ) from exc

    @staticmethod
    def _snapshot_tree(root: Path) -> Iterator[SnapshotFile]:
        for path in _safe_files(root):
            data = path.read_bytes()
            yield SnapshotFile(
                path=path.relative_to(root).as_posix(),
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            )

    def _load_metadata(self, job_id: str) -> dict[str, Any]:
        path = self.metadata_path(job_id)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise WorkspaceError(
                "workspace metadata was not found",
                code="WORKSPACE_NOT_FOUND",
                details={"job_id": job_id},
            ) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkspaceError(
                "workspace metadata is invalid",
                code="WORKSPACE_METADATA_INVALID",
                details={"job_id": job_id},
            ) from exc
        return data

    def source_snapshot(self, job_id: str) -> dict[str, Any]:
        """Return the evidence-safe portion of recorded source metadata."""

        data = self._load_metadata(job_id)
        return {
            key: data[key]
            for key in (
                "schema_version",
                "job_id",
                "source_revision",
                "created_at",
                "files",
                "omitted_paths",
            )
            if key in data
        }

    def stale_source(self, job_id: str) -> dict[str, Any]:
        metadata = self._load_metadata(job_id)
        source = Path(metadata["source_root"]).resolve(strict=False)
        if not source.is_dir():
            return {
                "stale": True,
                "reason": "source_missing",
                "recorded_revision": metadata.get("source_revision"),
                "current_revision": None,
                "changed_paths": [],
            }
        patterns = tuple(metadata.get("exclude_patterns", ()))
        current = {
            item.path: item.sha256 for item in self._snapshot_source(source, patterns)
        }
        recorded = {item["path"]: item["sha256"] for item in metadata.get("files", [])}
        changed_paths = sorted(
            path
            for path in set(current) | set(recorded)
            if current.get(path) != recorded.get(path)
        )
        current_revision = _git_revision(source)
        recorded_revision = metadata.get("source_revision")
        revision_changed = bool(
            recorded_revision and current_revision and recorded_revision != current_revision
        )
        stale = bool(changed_paths or revision_changed)
        return {
            "stale": stale,
            "reason": "source_changed" if stale else "unchanged",
            "recorded_revision": recorded_revision,
            "current_revision": current_revision,
            "changed_paths": changed_paths,
        }

    @classmethod
    def _snapshot_source(
        cls, source: Path, excluded_patterns: tuple[str, ...]
    ) -> Iterator[SnapshotFile]:
        for path in _safe_files(source, excluded_patterns):
            data = path.read_bytes()
            yield SnapshotFile(
                path=path.relative_to(source).as_posix(),
                size=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            )

    def diff(self, job_id: str) -> WorkspaceDiff:
        baseline = self.baseline_path(job_id)
        workspace = self.workspace_path(job_id)
        if not baseline.is_dir() or not workspace.is_dir():
            raise WorkspaceError(
                "workspace or immutable baseline is missing",
                code="WORKSPACE_NOT_FOUND",
                details={"job_id": job_id},
            )
        baseline_files = {path.relative_to(baseline).as_posix(): path for path in _safe_files(baseline)}
        workspace_files = {
            path.relative_to(workspace).as_posix(): path for path in _safe_files(workspace)
        }
        changes: list[dict[str, Any]] = []
        patch_parts: list[str] = []
        for relative in sorted(set(baseline_files) | set(workspace_files)):
            before_path = baseline_files.get(relative)
            after_path = workspace_files.get(relative)
            before = before_path.read_bytes() if before_path else b""
            after = after_path.read_bytes() if after_path else b""
            if before_path and after_path and before == after:
                continue
            change_type = "modified"
            if before_path is None:
                change_type = "added"
            elif after_path is None:
                change_type = "deleted"
            binary = not (_is_text(before) and _is_text(after))
            changes.append(
                {
                    "path": relative,
                    "change_type": change_type,
                    "binary": binary,
                    "before_sha256": hashlib.sha256(before).hexdigest() if before_path else None,
                    "after_sha256": hashlib.sha256(after).hexdigest() if after_path else None,
                    "before_size": len(before) if before_path else None,
                    "after_size": len(after) if after_path else None,
                }
            )
            patch_parts.append(f"diff --git a/{relative} b/{relative}\n")
            if change_type == "added":
                patch_parts.append("new file mode 100644\n")
            elif change_type == "deleted":
                patch_parts.append("deleted file mode 100644\n")
            if binary:
                patch_parts.append(f"Binary files a/{relative} and b/{relative} differ\n")
                continue
            before_text = _normalized_text(before)
            after_text = _normalized_text(after)
            from_name = f"a/{relative}" if before_path else "/dev/null"
            to_name = f"b/{relative}" if after_path else "/dev/null"
            patch_parts.extend(
                difflib.unified_diff(
                    before_text.splitlines(keepends=True),
                    after_text.splitlines(keepends=True),
                    fromfile=from_name,
                    tofile=to_name,
                    lineterm="\n",
                )
            )
        patch = "".join(patch_parts)
        if patch and not patch.endswith("\n"):
            patch += "\n"
        stale = self.stale_source(job_id)
        return WorkspaceDiff(
            patch=patch,
            files_changed=tuple(changes),
            stale_source_warning=bool(stale["stale"]),
            stale_source_details=stale,
        )

    compute_diff = diff

    def write_patch(self, job_id: str, destination: str | os.PathLike[str]) -> WorkspaceDiff:
        result = self.diff(job_id)
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        _write_text_atomic(path, result.patch)
        return result

    def cleanup(self, job_id: str) -> bool:
        """Delete only the gateway-owned job directory, never the source tree."""

        job_root = self.job_root(job_id)
        if not job_root.exists():
            return False
        resolved = job_root.resolve(strict=True)
        if resolved.parent != self.root or resolved == self.root:
            raise WorkspaceError("refusing unsafe workspace cleanup", code="UNSAFE_CLEANUP_PATH")
        shutil.rmtree(resolved)
        return True

    cleanup_workspace = cleanup


def _safe_files(root: Path, excluded_patterns: Iterable[str] = ()) -> Iterator[Path]:
    """Yield regular files without following any link/reparse directory."""

    patterns = tuple(excluded_patterns)

    def visit(directory: Path) -> Iterator[Path]:
        for entry in sorted(os.scandir(directory), key=lambda item: item.name.casefold()):
            path = Path(entry.path)
            relative = path.relative_to(root).as_posix()
            if path_matches(relative, patterns) or any(
                path_matches(part, DEFAULT_EXCLUDED_PATHS) for part in relative.split("/")
            ):
                continue
            if is_reparse_point(path):
                continue
            if path.is_dir():
                yield from visit(path)
            elif path.is_file():
                yield path

    yield from visit(root)


def _is_text(data: bytes) -> bool:
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _normalized_text(data: bytes) -> str:
    return data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")


def _git_revision(root: Path) -> str | None:
    git = shutil.which("git")
    if not git:
        return None
    try:
        result = subprocess.run(
            [git, "rev-parse", "--verify", "HEAD"],
            cwd=root,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
            env=_subprocess_environment(),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _subprocess_environment() -> dict[str, str]:
    allowed = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "HOME", "USERPROFILE")
    return {key: os.environ[key] for key in allowed if key in os.environ}


def _write_json_atomic(path: Path, data: Mapping[str, Any]) -> None:
    serialized = json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    _write_text_atomic(path, serialized)


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".upg-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


__all__ = [
    "DEFAULT_EXCLUDED_PATHS",
    "SnapshotFile",
    "WorkspaceDiff",
    "WorkspaceError",
    "WorkspaceManager",
    "WorkspaceSnapshot",
]
