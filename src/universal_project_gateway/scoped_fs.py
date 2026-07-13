"""Workspace-scoped text file operations.

This module deliberately does not expose a generic filesystem handle.  Every
operation starts from a workspace-relative path, rejects links/reparse points,
and proves containment before touching the filesystem.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from .models import GatewayError

_WINDOWS_REPARSE_POINT = 0x400
_DEFAULT_PROTECTED = (".git",)
_REQUEST_ID_SAFE = re.compile(r"[^a-zA-Z0-9._-]+")
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


class ScopedFileError(GatewayError):
    """A structured denial or failure from a scoped file operation."""

    default_code = "SCOPED_FILE_ERROR"


@dataclass(frozen=True, slots=True)
class FileMetadata:
    path: str
    size: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}


def normalize_relative_path(path: str | os.PathLike[str], *, allow_root: bool = False) -> str:
    """Return a canonical POSIX relative path or raise a structured denial.

    ``pathlib.Path.is_absolute`` alone is insufficient on a different host OS,
    so Windows drive/UNC forms are rejected explicitly as well.
    """

    raw = os.fspath(path)
    if not isinstance(raw, str):
        raise ScopedFileError("path must be text", code="INVALID_PATH_TYPE")
    if "\x00" in raw:
        raise ScopedFileError("path contains a NUL byte", code="INVALID_PATH")

    normalized_slashes = raw.replace("\\", "/")
    if normalized_slashes in {"", "."}:
        if allow_root:
            return "."
        raise ScopedFileError("a file path is required", code="INVALID_PATH")
    if (
        normalized_slashes.startswith("/")
        or normalized_slashes.startswith("//")
        or re.match(r"^[a-zA-Z]:", normalized_slashes)
    ):
        raise ScopedFileError(
            "absolute paths are not permitted",
            code="ABSOLUTE_PATH_FORBIDDEN",
            details={"path": raw},
        )

    pure = PurePosixPath(normalized_slashes)
    if any(part == ".." for part in pure.parts):
        raise ScopedFileError(
            "parent traversal is not permitted",
            code="PATH_TRAVERSAL_FORBIDDEN",
            details={"path": raw},
        )
    parts = tuple(part for part in pure.parts if part not in {"", "."})
    if not parts:
        if allow_root:
            return "."
        raise ScopedFileError("a file path is required", code="INVALID_PATH")
    if any(":" in part for part in parts):
        # Colons are stream delimiters on Windows.  Refusing them everywhere
        # keeps behavior consistent across platforms.
        raise ScopedFileError(
            "colon-delimited paths are not permitted",
            code="INVALID_PATH",
            details={"path": raw},
        )
    for part in parts:
        if part.endswith((" ", ".")) or part.split(".", 1)[0].upper() in _WINDOWS_RESERVED_NAMES:
            raise ScopedFileError(
                "path uses a Windows-reserved or ambiguous name",
                code="INVALID_PATH",
                details={"path": raw},
            )
    return PurePosixPath(*parts).as_posix()


def is_reparse_point(path: Path) -> bool:
    """Return true for symlinks and Windows junction/reparse entries."""

    try:
        if path.is_symlink():
            return True
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        return bool(attributes & _WINDOWS_REPARSE_POINT)
    except OSError:
        return False


def path_matches(relative_path: str, patterns: Iterable[str]) -> bool:
    """Match an exact path, a descendant prefix, or an explicit glob."""

    candidate = relative_path.replace("\\", "/").strip("/")
    folded_candidate = candidate.casefold()
    for raw_pattern in patterns:
        pattern = str(raw_pattern).replace("\\", "/").strip("/")
        if not pattern:
            continue
        folded_pattern = pattern.casefold()
        if any(character in pattern for character in "*?["):
            if fnmatch.fnmatchcase(folded_candidate, folded_pattern):
                return True
            # ``fnmatch`` does not make ``dir/**`` match ``dir`` itself.
            glob_root = folded_pattern.split("*", 1)[0].rstrip("/")
            if glob_root and (
                folded_candidate == glob_root or folded_candidate.startswith(f"{glob_root}/")
            ):
                return True
        elif folded_candidate == folded_pattern or folded_candidate.startswith(
            f"{folded_pattern}/"
        ):
            return True
    return False


class ScopedWorkspace:
    """Safe, text-only operations rooted at one isolated job workspace."""

    def __init__(
        self,
        root: str | os.PathLike[str],
        protected_paths: Iterable[str] = (),
        *,
        max_file_size: int = 1_000_000,
    ) -> None:
        candidate = Path(root).expanduser()
        if not candidate.exists() or not candidate.is_dir():
            raise ScopedFileError(
                "workspace root does not exist",
                code="WORKSPACE_NOT_FOUND",
                details={"root": str(candidate)},
            )
        self.root = candidate.resolve(strict=True)
        self.protected_paths = tuple(dict.fromkeys((*_DEFAULT_PROTECTED, *protected_paths)))
        if max_file_size < 1:
            raise ValueError("max_file_size must be positive")
        self.max_file_size = max_file_size

    def _resolve(
        self,
        relative_path: str | os.PathLike[str],
        *,
        allow_root: bool = False,
        must_exist: bool = False,
    ) -> tuple[str, Path]:
        relative = normalize_relative_path(relative_path, allow_root=allow_root)
        if relative != "." and path_matches(relative, self.protected_paths):
            raise ScopedFileError(
                "the requested path is protected",
                code="PROTECTED_PATH_FORBIDDEN",
                details={"path": relative},
            )

        candidate = self.root if relative == "." else self.root.joinpath(*relative.split("/"))
        # Reject links at any existing hop.  Resolving and checking containment
        # additionally catches an exotic link race or mount escape.
        cursor = self.root
        if relative != ".":
            for part in relative.split("/"):
                cursor = cursor / part
                if cursor.exists() or cursor.is_symlink():
                    if is_reparse_point(cursor):
                        raise ScopedFileError(
                            "symbolic links and reparse points are not accessible",
                            code="LINK_PATH_FORBIDDEN",
                            details={"path": relative},
                        )
                else:
                    break
        resolved = candidate.resolve(strict=False)
        if resolved != self.root and self.root not in resolved.parents:
            raise ScopedFileError(
                "path resolves outside the active workspace",
                code="PATH_ESCAPE_FORBIDDEN",
                details={"path": relative},
            )
        if must_exist and not candidate.exists():
            raise ScopedFileError(
                "workspace path does not exist",
                code="PATH_NOT_FOUND",
                details={"path": relative},
            )
        return relative, candidate

    @staticmethod
    def _read_utf8(path: Path, *, limit: int, relative: str) -> str:
        if not path.is_file():
            raise ScopedFileError(
                "path is not a regular file",
                code="NOT_A_FILE",
                details={"path": relative},
            )
        size = path.stat().st_size
        if size > limit:
            raise ScopedFileError(
                "file exceeds the configured text size limit",
                code="FILE_TOO_LARGE",
                details={"path": relative, "size": size, "limit": limit},
            )
        data = path.read_bytes()
        if b"\x00" in data:
            raise ScopedFileError(
                "binary files are metadata-only in this MVP",
                code="BINARY_FILE_READ_FORBIDDEN",
                details={"path": relative, "size": size},
            )
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ScopedFileError(
                "file is not valid UTF-8 text",
                code="BINARY_FILE_READ_FORBIDDEN",
                details={"path": relative, "size": size},
            ) from exc

    @staticmethod
    def _metadata(relative: str, path: Path) -> FileMetadata:
        data = path.read_bytes()
        return FileMetadata(relative, len(data), hashlib.sha256(data).hexdigest())

    def list_dir(self, relative_path: str | os.PathLike[str] = ".") -> list[dict[str, Any]]:
        relative, directory = self._resolve(relative_path, allow_root=True, must_exist=True)
        if not directory.is_dir():
            raise ScopedFileError(
                "path is not a directory",
                code="NOT_A_DIRECTORY",
                details={"path": relative},
            )
        entries: list[dict[str, Any]] = []
        for child in sorted(directory.iterdir(), key=lambda item: item.name.casefold()):
            child_relative = child.relative_to(self.root).as_posix()
            if path_matches(child_relative, self.protected_paths):
                continue
            linked = is_reparse_point(child)
            entry: dict[str, Any] = {
                "path": child_relative,
                "name": child.name,
                "type": "link" if linked else ("directory" if child.is_dir() else "file"),
            }
            if child.is_file() and not linked:
                entry["size"] = child.stat().st_size
            entries.append(entry)
        return entries

    def read_text(self, relative_path: str | os.PathLike[str]) -> str:
        relative, path = self._resolve(relative_path, must_exist=True)
        return self._read_utf8(path, limit=self.max_file_size, relative=relative)

    def metadata(self, relative_path: str | os.PathLike[str]) -> dict[str, Any]:
        relative, path = self._resolve(relative_path, must_exist=True)
        if path.is_dir():
            return {"path": relative, "type": "directory"}
        if not path.is_file():
            return {"path": relative, "type": "other"}
        size = path.stat().st_size
        digest = hashlib.sha256()
        binary = False
        decoder_bytes = bytearray()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
                if len(decoder_bytes) < 8_192:
                    decoder_bytes.extend(chunk[: 8_192 - len(decoder_bytes)])
                if b"\x00" in chunk:
                    binary = True
        if not binary:
            binary = not _is_utf8(bytes(decoder_bytes))
        return {
            "path": relative,
            "type": "file",
            "size": size,
            "sha256": digest.hexdigest(),
            "binary": binary,
        }

    def _atomic_write(self, relative: str, path: Path, content: str) -> FileMetadata:
        if not isinstance(content, str):
            raise ScopedFileError("content must be text", code="INVALID_CONTENT_TYPE")
        encoded = content.encode("utf-8")
        if len(encoded) > self.max_file_size:
            raise ScopedFileError(
                "content exceeds the configured text size limit",
                code="FILE_TOO_LARGE",
                details={"path": relative, "size": len(encoded), "limit": self.max_file_size},
            )
        path.parent.mkdir(parents=True, exist_ok=True)
        # Re-check the parent after creation so an existing link cannot be used
        # to redirect the temporary file.
        self._resolve(relative)
        descriptor, temp_name = tempfile.mkstemp(prefix=".upg-", dir=path.parent)
        temp_path = Path(temp_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)
        return self._metadata(relative, path)

    def create_text(self, relative_path: str | os.PathLike[str], content: str) -> dict[str, Any]:
        relative, path = self._resolve(relative_path)
        if path.exists():
            raise ScopedFileError(
                "create_text will not overwrite an existing path",
                code="PATH_ALREADY_EXISTS",
                details={"path": relative},
            )
        return self._atomic_write(relative, path, content).to_dict()

    def replace_text(
        self,
        relative_path: str | os.PathLike[str],
        content: str,
        *,
        expected_sha256: str | None = None,
    ) -> dict[str, Any]:
        relative, path = self._resolve(relative_path, must_exist=True)
        if not path.is_file():
            raise ScopedFileError(
                "replace_text requires a regular file",
                code="NOT_A_FILE",
                details={"path": relative},
            )
        # Binary files are metadata-only.  Do not allow a text replacement to
        # silently destroy a binary payload.
        self._read_utf8(path, limit=self.max_file_size, relative=relative)
        if expected_sha256 is not None:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            if actual != expected_sha256:
                raise ScopedFileError(
                    "file changed since it was inspected",
                    code="FILE_PRECONDITION_FAILED",
                    details={"path": relative, "expected": expected_sha256, "actual": actual},
                )
        return self._atomic_write(relative, path, content).to_dict()

    def write_text(
        self,
        relative_path: str | os.PathLike[str],
        content: str,
        *,
        overwrite: bool = True,
    ) -> dict[str, Any]:
        """Compatibility helper selecting create or replace explicitly."""

        relative, path = self._resolve(relative_path)
        if path.exists():
            if not overwrite:
                raise ScopedFileError(
                    "write would overwrite an existing path",
                    code="PATH_ALREADY_EXISTS",
                    details={"path": relative},
                )
            return self.replace_text(relative, content)
        return self.create_text(relative, content)

    def replace_in_text(
        self,
        relative_path: str | os.PathLike[str],
        old: str,
        new: str,
        *,
        max_replacements: int = 100,
    ) -> dict[str, Any]:
        if not old:
            raise ScopedFileError("old text must not be empty", code="INVALID_REPLACEMENT")
        if max_replacements < 1:
            raise ScopedFileError("max_replacements must be positive", code="INVALID_REPLACEMENT")
        current = self.read_text(relative_path)
        occurrences = current.count(old)
        if occurrences == 0:
            raise ScopedFileError("text to replace was not found", code="TEXT_NOT_FOUND")
        if occurrences > max_replacements:
            raise ScopedFileError(
                "replacement exceeds the configured bound",
                code="REPLACEMENT_LIMIT_EXCEEDED",
                details={"occurrences": occurrences, "limit": max_replacements},
            )
        expected = hashlib.sha256(current.encode("utf-8")).hexdigest()
        result = self.replace_text(
            relative_path,
            current.replace(old, new),
            expected_sha256=expected,
        )
        return {**result, "replacements": occurrences}

    def move(
        self,
        source_path: str | os.PathLike[str],
        destination_path: str | os.PathLike[str],
        *,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        source_relative, source = self._resolve(source_path, must_exist=True)
        destination_relative, destination = self._resolve(destination_path)
        if not source.is_file():
            raise ScopedFileError(
                "only regular files may be moved",
                code="NOT_A_FILE",
                details={"path": source_relative},
            )
        self._read_utf8(source, limit=self.max_file_size, relative=source_relative)
        if destination.exists() and not overwrite:
            raise ScopedFileError(
                "destination already exists",
                code="PATH_ALREADY_EXISTS",
                details={"path": destination_relative},
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        self._resolve(destination_relative)
        os.replace(source, destination)
        return {
            "source": source_relative,
            "destination": destination_relative,
            **self._metadata(destination_relative, destination).to_dict(),
        }

    def request_delete(
        self,
        relative_path: str | os.PathLike[str],
        *,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Describe a deletion approval request without deleting anything."""

        relative, path = self._resolve(relative_path, must_exist=True)
        fingerprint = hashlib.sha256(f"{relative}\0{reason or ''}".encode()).hexdigest()[:16]
        request_id = _REQUEST_ID_SAFE.sub("-", f"delete-{fingerprint}")
        return {
            "request_id": request_id,
            "operation": "delete",
            "path": relative,
            "reason": reason,
            "risk_level": "R4",
            "status": "waiting_for_approval",
            "executed": False,
            "message": "Deletion is not executed in this MVP.",
            "path_type": "directory" if path.is_dir() else "file",
        }

    def search(
        self,
        query: str,
        relative_path: str | os.PathLike[str] = ".",
        *,
        case_sensitive: bool = False,
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query or len(query) > 1_000:
            raise ScopedFileError("query must be 1-1000 characters", code="INVALID_SEARCH_QUERY")
        if not 1 <= max_results <= 1_000:
            raise ScopedFileError("max_results must be from 1 to 1000", code="INVALID_SEARCH_LIMIT")
        relative, start = self._resolve(relative_path, allow_root=True, must_exist=True)
        files = (
            [start]
            if start.is_file()
            else list(_safe_workspace_files(start, self.root, self.protected_paths))
        )
        needle = query if case_sensitive else query.casefold()
        results: list[dict[str, Any]] = []
        for path in files:
            if len(results) >= max_results:
                break
            if not path.is_file() or is_reparse_point(path):
                continue
            child_relative = path.relative_to(self.root).as_posix()
            if path_matches(child_relative, self.protected_paths):
                continue
            try:
                content = self._read_utf8(
                    path,
                    limit=self.max_file_size,
                    relative=child_relative,
                )
            except ScopedFileError as exc:
                if exc.code in {"FILE_TOO_LARGE", "BINARY_FILE_READ_FORBIDDEN"}:
                    continue
                raise
            for line_number, line in enumerate(content.splitlines(), 1):
                haystack = line if case_sensitive else line.casefold()
                if needle in haystack:
                    results.append(
                        {"path": child_relative, "line": line_number, "text": line[:500]}
                    )
                    if len(results) >= max_results:
                        break
        return results

    # Service-facing spelling used by the MCP contract.
    search_text = search
    move_file = move


def _is_utf8(data: bytes) -> bool:
    try:
        data.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def _safe_workspace_files(
    root: Path,
    workspace_root: Path,
    protected_paths: Iterable[str],
) -> Iterable[Path]:
    """Walk without following symlinks or Windows junctions."""

    for entry in sorted(os.scandir(root), key=lambda item: item.name.casefold()):
        path = Path(entry.path)
        relative = path.relative_to(workspace_root).as_posix()
        if path_matches(relative, protected_paths):
            continue
        if is_reparse_point(path):
            continue
        if path.is_dir():
            yield from _safe_workspace_files(path, workspace_root, protected_paths)
        elif path.is_file():
            yield path


# Backwards-friendly descriptive alias.
ScopedFileSystem = ScopedWorkspace


__all__ = [
    "FileMetadata",
    "ScopedFileError",
    "ScopedFileSystem",
    "ScopedWorkspace",
    "is_reparse_point",
    "normalize_relative_path",
    "path_matches",
]
