"""Sandbox execution contracts without granting public command authority."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ..contracts import EXECUTION_CONTRACT_VERSION
from ..models import GatewayError, json_ready, utc_now


class SandboxError(GatewayError):
    """Structured refusal or failure at the sandbox backend boundary."""

    default_code = "SANDBOX_ERROR"


@dataclass(frozen=True, slots=True)
class SandboxExecutionRequest:
    """One adapter-authorized action submitted to a prepared sandbox.

    This is an internal Runner/runtime contract. It is deliberately not
    exposed through the service, CLI, or MCP surfaces as a generic executor.
    """

    action: str
    argv: tuple[str, ...]
    cwd: Path
    timeout_seconds: int
    environment: Mapping[str, str] = field(default_factory=dict)
    environment_filtered: bool = True
    network_policy: str = "unrestricted"

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": EXECUTION_CONTRACT_VERSION,
            "action": self.action,
            "argv": list(self.argv),
            "cwd": str(self.cwd),
            "timeout_seconds": self.timeout_seconds,
            "environment_names": sorted(self.environment),
            "environment_filtered": self.environment_filtered,
            "network_policy": self.network_policy,
        }


@dataclass(frozen=True, slots=True)
class SandboxExecutionResult:
    """Backward-compatible command result plus explicit sandbox metadata."""

    action: str
    status: str
    argv: tuple[str, ...]
    cwd: str
    returncode: int | None
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool = False
    reason_code: str | None = None
    message: str | None = None
    backend_id: str = "unknown"
    safety_level: str = "unknown"
    timeout_seconds: int = 0
    shell_disabled: bool = True
    environment_filtered: bool = False
    network_policy: str = "unrestricted"
    network_policy_enforced: bool = False
    limitation_notes: tuple[str, ...] = ()
    cancelled: bool = False
    artifacts: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    @property
    def success(self) -> bool:
        return self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": EXECUTION_CONTRACT_VERSION,
            "action": self.action,
            "status": self.status,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "duration_seconds": self.duration_seconds,
            "timed_out": self.timed_out,
            "reason_code": self.reason_code,
            "message": self.message,
            "timeout_seconds": self.timeout_seconds,
            "cancelled": self.cancelled,
            "sandbox": {
                "backend_id": self.backend_id,
                "safety_level": self.safety_level,
                "runtime_action": self.action,
                "shell_disabled": self.shell_disabled,
                "environment_filtered": self.environment_filtered,
                "network_policy": self.network_policy,
                "network_policy_enforced": self.network_policy_enforced,
                "limitation_notes": list(self.limitation_notes),
                "artifacts": list(self.artifacts),
            },
        }


@dataclass(slots=True)
class SandboxHandle:
    """Prepared workspace ownership and collected execution metadata."""

    handle_id: str
    workspace_root: Path
    backend_id: str
    safety_level: str
    prepared_at: str = field(default_factory=utc_now)
    snapshot: Mapping[str, Any] = field(default_factory=dict)
    executions: list[SandboxExecutionResult] = field(default_factory=list)
    destroyed: bool = False

    def to_dict(self, *, include_executions: bool = True) -> dict[str, Any]:
        result = {
            "handle_id": self.handle_id,
            "workspace_root": str(self.workspace_root),
            "backend_id": self.backend_id,
            "safety_level": self.safety_level,
            "prepared_at": self.prepared_at,
            "snapshot": json_ready(self.snapshot),
            "destroyed": self.destroyed,
        }
        if include_executions:
            result["executions"] = [execution.to_dict() for execution in self.executions]
        return result


@runtime_checkable
class SandboxBackend(Protocol):
    """Internal execution backend used only after runtime adapter validation."""

    backend_id: str
    safety_level: str
    limitation_notes: tuple[str, ...]

    def prepare(
        self,
        workspace_root: str | Path,
        *,
        snapshot: Mapping[str, Any] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> SandboxHandle: ...

    def execute(
        self,
        handle: SandboxHandle,
        request: SandboxExecutionRequest,
        *,
        should_cancel: Callable[[], bool] | None = None,
    ) -> SandboxExecutionResult: ...

    def collect(self, handle: SandboxHandle) -> Mapping[str, Any]: ...

    def destroy(self, handle: SandboxHandle) -> None: ...


def ensure_sequence(value: Sequence[str]) -> tuple[str, ...]:
    """Normalize a bounded argv sequence for backend implementations."""

    if isinstance(value, (str, bytes)) or not value:
        raise SandboxError("sandbox argv must be a non-empty sequence", code="INVALID_SANDBOX_ARGV")
    result = tuple(value)
    if any(not isinstance(item, str) or not item or "\x00" in item for item in result):
        raise SandboxError(
            "sandbox argv must contain non-empty strings without NUL bytes",
            code="INVALID_SANDBOX_ARGV",
        )
    return result


__all__ = [
    "SandboxBackend",
    "SandboxError",
    "SandboxExecutionRequest",
    "SandboxExecutionResult",
    "SandboxHandle",
    "ensure_sequence",
]
