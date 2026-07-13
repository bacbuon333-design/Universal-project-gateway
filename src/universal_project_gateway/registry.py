"""Persistent, exact-match registry for validated project manifests."""

from __future__ import annotations

import hashlib
import os
import threading
import uuid
from pathlib import Path
from typing import Any

import yaml

from .manifests import ManifestLoader
from .models import GatewayError, ProjectManifest, ProjectRecord, utc_now

REGISTRY_SCHEMA_VERSION = "1.0"


class RegistryError(GatewayError):
    default_code = "REGISTRY_ERROR"


class RegistryCorruptError(RegistryError):
    default_code = "REGISTRY_CORRUPT"


class DuplicateProjectError(RegistryError):
    default_code = "DUPLICATE_PROJECT_ID"


class DuplicateSourcePathError(RegistryError):
    default_code = "DUPLICATE_SOURCE_PATH"


class ProjectNotFoundError(RegistryError):
    default_code = "PROJECT_NOT_FOUND"


class UnregisteredPathError(RegistryError):
    default_code = "UNREGISTERED_PATH"


class RegisteredManifestChangedError(RegistryError):
    default_code = "REGISTERED_MANIFEST_CHANGED"


def _path_key(path: str | os.PathLike[str]) -> str:
    resolved = str(Path(path).expanduser().resolve())
    return os.path.normcase(resolved).casefold()


def _record_path(value: str, path_base: Path) -> Path:
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = path_base / candidate
    return candidate.resolve()


def _record_from_data(data: Any, *, path_base: Path) -> ProjectRecord:
    if not isinstance(data, dict):
        raise RegistryCorruptError("registry project records must be mappings")
    required = {
        "project_id",
        "name",
        "project_type",
        "manifest_path",
        "local_path",
        "registered_at",
        "manifest_sha256",
    }
    missing = required - set(data)
    if missing:
        raise RegistryCorruptError(
            "registry project record is incomplete",
            details={"missing_fields": sorted(missing)},
        )
    if any(not isinstance(data[field], str) or not data[field] for field in required):
        raise RegistryCorruptError("registry project record fields must be non-empty strings")
    digest = data["manifest_sha256"]
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise RegistryCorruptError("registry manifest_sha256 is invalid")
    return ProjectRecord(
        project_id=data["project_id"],
        name=data["name"],
        project_type=data["project_type"],
        manifest_path=_record_path(data["manifest_path"], path_base),
        local_path=_record_path(data["local_path"], path_base),
        registered_at=data["registered_at"],
        manifest_sha256=digest,
    )


class ProjectRegistry:
    """YAML-backed project registry containing only non-secret metadata."""

    def __init__(
        self,
        path: str | os.PathLike[str],
        *,
        loader: ManifestLoader | None = None,
        path_base: str | os.PathLike[str] | None = None,
    ) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path_base = (
            Path(path_base).expanduser().resolve()
            if path_base is not None
            else self.path.parent
        )
        self.loader = loader or ManifestLoader()
        self._lock = threading.RLock()

    def _read(self) -> dict[str, ProjectRecord]:
        if not self.path.exists():
            return {}
        try:
            document = yaml.safe_load(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise RegistryCorruptError(f"cannot read project registry: {exc}") from exc
        if document is None:
            return {}
        if not isinstance(document, dict):
            raise RegistryCorruptError("registry root must be a mapping")
        if str(document.get("schema_version", "")) != REGISTRY_SCHEMA_VERSION:
            raise RegistryCorruptError(
                f"registry schema_version must be {REGISTRY_SCHEMA_VERSION!r}"
            )
        raw_projects = document.get("projects", [])
        if isinstance(raw_projects, dict):
            items = []
            for project_id, item in raw_projects.items():
                if not isinstance(item, dict):
                    raise RegistryCorruptError("registry project records must be mappings")
                items.append({"project_id": project_id, **item})
        elif isinstance(raw_projects, list):
            items = raw_projects
        else:
            raise RegistryCorruptError("registry projects must be a list or mapping")

        records: dict[str, ProjectRecord] = {}
        seen_paths: set[str] = set()
        for raw_record in items:
            record = _record_from_data(raw_record, path_base=self.path_base)
            if record.project_id in records:
                raise RegistryCorruptError(
                    "registry contains a duplicate project ID",
                    details={"project_id": record.project_id},
                )
            path_key = _path_key(record.local_path)
            if path_key in seen_paths:
                raise RegistryCorruptError(
                    "registry contains a duplicate local source path",
                    details={"local_path": str(record.local_path)},
                )
            records[record.project_id] = record
            seen_paths.add(path_key)
        return records

    def _write(self, records: dict[str, ProjectRecord]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        document = {
            "schema_version": REGISTRY_SCHEMA_VERSION,
            "projects": [records[project_id].to_dict() for project_id in sorted(records)],
        }
        temporary = self.path.with_name(f".{self.path.name}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary.open("w", encoding="utf-8", newline="\n") as handle:
                yaml.safe_dump(
                    document,
                    handle,
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False,
                )
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            raise RegistryError(f"cannot persist project registry: {exc}") from exc
        finally:
            if temporary.exists():
                temporary.unlink(missing_ok=True)

    def register(self, manifest_source: str | os.PathLike[str] | ProjectManifest) -> ProjectRecord:
        """Validate and atomically register a project.

        Registration is intentionally not idempotent: a repeated ID is an
        explicit error so callers cannot silently replace a trust contract.
        """

        if isinstance(manifest_source, ProjectManifest):
            manifest = manifest_source
            if manifest.manifest_path is None:
                raise RegistryError(
                    "a ProjectManifest must retain manifest_path to be registered",
                    code="MANIFEST_PATH_REQUIRED",
                )
        else:
            manifest = self.loader.load(manifest_source)
        assert manifest.manifest_path is not None
        if not manifest.local_path.is_dir():
            raise RegistryError(
                "registered local source path is not a directory",
                code="SOURCE_PATH_NOT_DIRECTORY",
                details={"local_path": str(manifest.local_path)},
            )
        try:
            digest = hashlib.sha256(manifest.manifest_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise RegistryError(f"cannot hash project manifest: {exc}") from exc
        record = ProjectRecord(
            project_id=manifest.project_id,
            name=manifest.name,
            project_type=manifest.project_type,
            manifest_path=manifest.manifest_path,
            local_path=manifest.local_path,
            registered_at=utc_now(),
            manifest_sha256=digest,
        )
        with self._lock:
            records = self._read()
            if record.project_id in records:
                raise DuplicateProjectError(
                    f"project ID {record.project_id!r} is already registered",
                    details={"project_id": record.project_id},
                )
            record_path_key = _path_key(record.local_path)
            for existing in records.values():
                if _path_key(existing.local_path) == record_path_key:
                    raise DuplicateSourcePathError(
                        "local source path is already registered",
                        details={
                            "local_path": str(record.local_path),
                            "project_id": existing.project_id,
                        },
                    )
            records[record.project_id] = record
            self._write(records)
        return record

    def register_manifest(self, manifest_path: str | os.PathLike[str]) -> ProjectRecord:
        return self.register(manifest_path)

    def list(self) -> list[ProjectRecord]:
        with self._lock:
            records = self._read()
        return [records[project_id] for project_id in sorted(records)]

    def list_projects(self) -> list[ProjectRecord]:
        return self.list()

    def get(self, project_id: str) -> ProjectRecord:
        with self._lock:
            record = self._read().get(project_id)
        if record is None:
            raise ProjectNotFoundError(
                f"project {project_id!r} is not registered",
                details={"project_id": project_id},
            )
        return record

    def get_project(self, project_id: str) -> ProjectRecord:
        return self.get(project_id)

    def resolve_path(self, local_path: str | os.PathLike[str]) -> ProjectRecord:
        requested_key = _path_key(local_path)
        with self._lock:
            records = self._read()
        for record in records.values():
            if _path_key(record.local_path) == requested_key:
                return record
        raise UnregisteredPathError(
            "path does not exactly match a registered project source",
            details={"local_path": str(Path(local_path).expanduser().resolve())},
        )

    def resolve(self, project_id_or_path: str | os.PathLike[str]) -> ProjectRecord:
        if isinstance(project_id_or_path, str):
            with self._lock:
                record = self._read().get(project_id_or_path)
            if record is not None:
                return record
        return self.resolve_path(project_id_or_path)

    def get_manifest(self, project_id: str) -> ProjectManifest:
        record = self.get(project_id)
        try:
            current_digest = hashlib.sha256(record.manifest_path.read_bytes()).hexdigest()
        except OSError as exc:
            raise RegisteredManifestChangedError(
                "registered manifest can no longer be read",
                details={"project_id": project_id, "manifest_path": str(record.manifest_path)},
            ) from exc
        if current_digest != record.manifest_sha256:
            raise RegisteredManifestChangedError(
                "registered manifest changed after registration; review and register it explicitly",
                details={
                    "project_id": project_id,
                    "expected_sha256": record.manifest_sha256,
                    "actual_sha256": current_digest,
                },
            )
        manifest = self.loader.load(record.manifest_path)
        if manifest.project_id != record.project_id or _path_key(manifest.local_path) != _path_key(
            record.local_path
        ):
            raise RegisteredManifestChangedError(
                "registered manifest identity no longer matches the registry record",
                details={"project_id": project_id},
            )
        return manifest
