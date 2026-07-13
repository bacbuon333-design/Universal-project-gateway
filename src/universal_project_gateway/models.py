"""Typed, JSON-serializable domain models shared by gateway components."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, StrEnum
from pathlib import Path
from typing import Any

JsonMapping = Mapping[str, Any]


def utc_now() -> str:
    """Return a stable UTC timestamp suitable for persistence and JSON."""

    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def json_ready(value: Any) -> Any:
    """Recursively convert gateway values into JSON-compatible primitives."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [json_ready(item) for item in value]
    return value


class GatewayError(Exception):
    """Base exception carrying a stable machine-readable error code."""

    default_code = "GATEWAY_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code or self.default_code
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "details": json_ready(self.details),
        }


class RiskLevel(StrEnum):
    R0 = "R0"
    R1 = "R1"
    R2 = "R2"
    R3 = "R3"
    R4 = "R4"

    @property
    def rank(self) -> int:
        return int(self.value[1])

    @classmethod
    def highest(cls, *levels: RiskLevel) -> RiskLevel:
        return max(levels, key=lambda item: item.rank, default=cls.R0)


class JobStatus(StrEnum):
    QUEUED = "queued"
    PREPARED = "prepared"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PublicationMode(StrEnum):
    NONE = "none"
    LOCAL_COMMIT = "local_commit"
    PUSH = "push"


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """An administrator-defined allowlisted argv invocation."""

    argv: tuple[str, ...]
    timeout_seconds: int = 120
    adapter: str | None = None
    environment: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "argv": list(self.argv),
            "timeout_seconds": self.timeout_seconds,
        }
        if self.adapter is not None:
            result["adapter"] = self.adapter
        if self.environment:
            result["environment"] = list(self.environment)
        return result


@dataclass(frozen=True, slots=True)
class ProjectSources:
    local_path: Path
    github_repository: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "local_path": str(self.local_path),
            "github_repository": self.github_repository,
        }


@dataclass(frozen=True, slots=True)
class ProjectPermissions:
    read: bool
    workspace_write: bool
    validation: bool
    git_publish: bool

    def to_dict(self) -> dict[str, bool]:
        return {
            "read": self.read,
            "workspace_write": self.workspace_write,
            "validation": self.validation,
            "git_publish": self.git_publish,
        }


@dataclass(frozen=True, slots=True)
class ProjectManifest:
    schema_version: str
    project_id: str
    name: str
    description: str
    project_type: str
    sources: ProjectSources
    stack: JsonMapping
    important_paths: tuple[str, ...]
    entrypoints: Any
    memory_files: tuple[str, ...]
    commands: Mapping[str, CommandSpec | None]
    permissions: ProjectPermissions
    protected_paths: tuple[str, ...]
    validation_requirements: tuple[str, ...]
    publication_policy: Mapping[str, bool]
    runtime_adapters: tuple[str, ...]
    state_file: str | None
    manifest_path: Path | None = None

    @property
    def local_path(self) -> Path:
        return self.sources.local_path

    def command(self, action: str) -> CommandSpec | None:
        return self.commands.get(action)

    def to_dict(self, *, include_metadata: bool = False) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "project_type": self.project_type,
            "sources": self.sources.to_dict(),
            "stack": json_ready(self.stack),
            "important_paths": list(self.important_paths),
            "entrypoints": json_ready(self.entrypoints),
            "memory_files": list(self.memory_files),
            "commands": {
                name: command.to_dict() if command is not None else None
                for name, command in self.commands.items()
            },
            "permissions": self.permissions.to_dict(),
            "protected_paths": list(self.protected_paths),
            "validation_requirements": list(self.validation_requirements),
            "publication_policy": dict(self.publication_policy),
            "runtime_adapters": list(self.runtime_adapters),
            "state_file": self.state_file,
        }
        if include_metadata and self.manifest_path is not None:
            result["manifest_path"] = str(self.manifest_path)
        return result


@dataclass(frozen=True, slots=True)
class ManifestValidationIssue:
    code: str
    path: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "path": self.path,
            "field": self.path,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True, slots=True)
class ManifestValidationResult:
    errors: tuple[ManifestValidationIssue, ...] = ()
    warnings: tuple[ManifestValidationIssue, ...] = ()
    manifest: ProjectManifest | None = None

    @property
    def valid(self) -> bool:
        return not self.errors and self.manifest is not None

    @property
    def issues(self) -> tuple[ManifestValidationIssue, ...]:
        return self.errors + self.warnings

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
        }


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    project_id: str
    name: str
    project_type: str
    manifest_path: Path
    local_path: Path
    registered_at: str
    manifest_sha256: str

    def to_dict(self) -> dict[str, str]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "project_type": self.project_type,
            "manifest_path": str(self.manifest_path),
            "local_path": str(self.local_path),
            "registered_at": self.registered_at,
            "manifest_sha256": self.manifest_sha256,
        }


@dataclass(frozen=True, slots=True)
class NormalizedIntent:
    project_id: str
    task_type: str
    target_scope: tuple[str, ...]
    expected_operations: tuple[str, ...]
    risk_level: RiskLevel
    required_validation: tuple[str, ...]
    publication_mode: PublicationMode
    requires_ai_planning: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "task_type": self.task_type,
            "target_scope": list(self.target_scope),
            "expected_operations": list(self.expected_operations),
            "risk_level": self.risk_level.value,
            "required_validation": list(self.required_validation),
            "publication_mode": self.publication_mode.value,
            "requires_ai_planning": self.requires_ai_planning,
        }


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    risk_level: RiskLevel
    reason_code: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_level": self.risk_level.value,
            "reason_code": self.reason_code,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class Job:
    job_id: str
    project_id: str
    user_request: str
    normalized_intent: JsonMapping
    risk_level: RiskLevel
    source_revision: str | None
    workspace_path: Path | None
    status: JobStatus
    created_at: str
    updated_at: str
    validation_summary: JsonMapping | None = None
    evidence_path: Path | None = None
    error_code: str | None = None
    error_message: str | None = None

    @property
    def id(self) -> str:
        return self.job_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "project_id": self.project_id,
            "user_request": self.user_request,
            "normalized_intent": json_ready(self.normalized_intent),
            "risk_level": self.risk_level.value,
            "source_revision": self.source_revision,
            "workspace_path": str(self.workspace_path) if self.workspace_path else None,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "validation_summary": json_ready(self.validation_summary),
            "evidence_path": str(self.evidence_path) if self.evidence_path else None,
            "error_code": self.error_code,
            "error_message": self.error_message,
        }


@dataclass(frozen=True, slots=True)
class JobEvent:
    event_id: int
    job_id: str
    event_type: str
    created_at: str
    details: JsonMapping = field(default_factory=dict)
    from_status: JobStatus | None = None
    to_status: JobStatus | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "job_id": self.job_id,
            "event_type": self.event_type,
            "created_at": self.created_at,
            "details": json_ready(self.details),
            "from_status": self.from_status.value if self.from_status else None,
            "to_status": self.to_status.value if self.to_status else None,
        }


def unique_strings(values: Sequence[str]) -> tuple[str, ...]:
    """Return strings in input order with duplicates removed."""

    return tuple(dict.fromkeys(values))
