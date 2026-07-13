"""Explicit local sandbox backends with accurately bounded safety claims."""

from __future__ import annotations

import os
import signal
import subprocess
import time
import uuid
from collections.abc import Callable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from ..scoped_fs import is_reparse_point
from .base import (
    SandboxError,
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxHandle,
    ensure_sequence,
)

_RUNTIME_ACTIONS = frozenset(
    {"install", "lint", "test", "build", "smoke_test", "inspect_environment"}
)
_NETWORK_POLICIES = frozenset({"unrestricted", "deny_requested"})
_LOCAL_ENVIRONMENT_ALLOWLIST = frozenset(
    {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "HOME",
        "USERPROFILE",
        "TEMP",
        "TMP",
        "CI",
        "LANG",
        "LC_ALL",
        "NO_COLOR",
        "TERM",
        "TZ",
        "PYTHONDONTWRITEBYTECODE",
        "PYTHONUNBUFFERED",
        "PIP_DISABLE_PIP_VERSION_CHECK",
        "PIP_NO_INPUT",
        "npm_config_audit",
        "npm_config_fund",
        "npm_config_ignore_scripts",
        "npm_config_update_notifier",
    }
)


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


class _LocalBackendBase:
    backend_id = "local-base"
    safety_level = "unknown"
    limitation_notes: tuple[str, ...] = ()

    def prepare(
        self,
        workspace_root: str | Path,
        *,
        snapshot: Mapping[str, Any] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> SandboxHandle:
        if should_cancel is not None and should_cancel():
            raise SandboxError(
                "sandbox preparation was cancelled before workspace validation",
                code="SANDBOX_CANCELLED",
            )
        candidate = Path(workspace_root).expanduser().absolute()
        if is_reparse_point(candidate):
            raise SandboxError(
                "sandbox workspace must not be a symlink or reparse point",
                code="INVALID_SANDBOX_WORKSPACE",
                details={"workspace_root": str(candidate)},
            )
        try:
            root = candidate.resolve(strict=True)
        except OSError as exc:
            raise SandboxError(
                "sandbox workspace does not resolve to an accessible directory",
                code="INVALID_SANDBOX_WORKSPACE",
                details={"workspace_root": str(candidate)},
            ) from exc
        if not root.is_dir():
            raise SandboxError(
                "sandbox workspace must be a real directory",
                code="INVALID_SANDBOX_WORKSPACE",
                details={"workspace_root": str(root)},
            )
        return SandboxHandle(
            handle_id=uuid.uuid4().hex,
            workspace_root=root,
            backend_id=self.backend_id,
            safety_level=self.safety_level,
            snapshot=dict(snapshot or {}),
        )

    def _validate_request(
        self,
        handle: SandboxHandle,
        request: SandboxExecutionRequest,
    ) -> tuple[tuple[str, ...], Path]:
        if handle.destroyed:
            raise SandboxError("sandbox handle has been destroyed", code="SANDBOX_DESTROYED")
        if handle.backend_id != self.backend_id:
            raise SandboxError(
                "sandbox handle belongs to a different backend",
                code="SANDBOX_BACKEND_MISMATCH",
            )
        if request.action not in _RUNTIME_ACTIONS:
            raise SandboxError(
                "sandbox action is not a fixed runtime action",
                code="SANDBOX_ACTION_FORBIDDEN",
                details={"action": request.action},
            )
        argv = ensure_sequence(request.argv)
        if isinstance(request.timeout_seconds, bool) or not 1 <= request.timeout_seconds <= 600:
            raise SandboxError(
                "sandbox timeout must be from 1 to 600 seconds",
                code="INVALID_SANDBOX_TIMEOUT",
            )
        if request.network_policy not in _NETWORK_POLICIES:
            raise SandboxError(
                "sandbox network policy is unknown",
                code="INVALID_NETWORK_POLICY",
                details={"network_policy": request.network_policy},
            )
        cwd_candidate = Path(request.cwd).expanduser().absolute()
        if is_reparse_point(cwd_candidate):
            raise SandboxError(
                "sandbox cwd must not be a symlink or reparse point",
                code="INVALID_SANDBOX_CWD",
                details={"cwd": str(cwd_candidate)},
            )
        try:
            cwd = cwd_candidate.resolve(strict=True)
        except OSError as exc:
            raise SandboxError(
                "sandbox cwd does not resolve to an accessible directory",
                code="INVALID_SANDBOX_CWD",
                details={"cwd": str(cwd_candidate)},
            ) from exc
        try:
            cwd.relative_to(handle.workspace_root)
        except ValueError as exc:
            raise SandboxError(
                "sandbox cwd must remain inside the prepared workspace",
                code="SANDBOX_CWD_OUTSIDE_WORKSPACE",
                details={
                    "cwd": str(cwd),
                    "workspace_root": str(handle.workspace_root),
                },
            ) from exc
        if not cwd.is_dir():
            raise SandboxError(
                "sandbox cwd must be a real workspace directory",
                code="INVALID_SANDBOX_CWD",
                details={"cwd": str(cwd)},
            )
        return argv, cwd

    def _result(
        self,
        request: SandboxExecutionRequest,
        *,
        status: str,
        argv: tuple[str, ...],
        cwd: Path,
        returncode: int | None,
        stdout: str,
        stderr: str,
        duration_seconds: float,
        environment_filtered: bool,
        timed_out: bool = False,
        cancelled: bool = False,
        reason_code: str | None = None,
        message: str | None = None,
    ) -> SandboxExecutionResult:
        return SandboxExecutionResult(
            action=request.action,
            status=status,
            argv=argv,
            cwd=str(cwd),
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=round(duration_seconds, 6),
            timed_out=timed_out,
            cancelled=cancelled,
            reason_code=reason_code,
            message=message,
            backend_id=self.backend_id,
            safety_level=self.safety_level,
            timeout_seconds=request.timeout_seconds,
            shell_disabled=True,
            environment_filtered=environment_filtered,
            network_policy=request.network_policy,
            network_policy_enforced=False,
            limitation_notes=self.limitation_notes,
        )

    def _cancelled_result(
        self,
        request: SandboxExecutionRequest,
        argv: tuple[str, ...],
        cwd: Path,
        *,
        environment_filtered: bool,
    ) -> SandboxExecutionResult:
        return self._result(
            request,
            status="cancelled",
            argv=argv,
            cwd=cwd,
            returncode=None,
            stdout="",
            stderr="",
            duration_seconds=0.0,
            timed_out=False,
            cancelled=True,
            reason_code="SANDBOX_CANCELLED",
            message="Cancellation was observed before process execution.",
            environment_filtered=environment_filtered,
        )

    def collect(self, handle: SandboxHandle) -> Mapping[str, Any]:
        if handle.backend_id != self.backend_id:
            raise SandboxError(
                "sandbox handle belongs to a different backend",
                code="SANDBOX_BACKEND_MISMATCH",
            )
        return {
            **handle.to_dict(include_executions=True),
            "limitation_notes": list(self.limitation_notes),
        }

    def destroy(self, handle: SandboxHandle) -> None:
        if handle.backend_id != self.backend_id:
            raise SandboxError(
                "sandbox handle belongs to a different backend",
                code="SANDBOX_BACKEND_MISMATCH",
            )
        handle.destroyed = True


class UnsafeLocalSandboxBackend(_LocalBackendBase):
    """Compatibility backend preserving the original subprocess.run behavior.

    Despite the interface name, this backend is not an OS sandbox. It relies on
    adapter allowlists, exact cwd, filtered env input, and subprocess timeout.
    """

    backend_id = "unsafe-local-subprocess"
    safety_level = "unsafe-local"
    limitation_notes = (
        "No kernel-level filesystem, process, user, resource, or network isolation.",
        "Timeout does not guarantee descendant process-tree cleanup.",
        "Use only with trusted local projects during development.",
    )

    def execute(
        self,
        handle: SandboxHandle,
        request: SandboxExecutionRequest,
        *,
        should_cancel: Callable[[], bool] | None = None,
    ) -> SandboxExecutionResult:
        argv, cwd = self._validate_request(handle, request)
        if should_cancel is not None and should_cancel():
            result = self._cancelled_result(
                request,
                argv,
                cwd,
                environment_filtered=request.environment_filtered,
            )
            handle.executions.append(result)
            return result
        start = time.monotonic()
        try:
            completed = subprocess.run(
                list(argv),
                cwd=cwd,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=request.timeout_seconds,
                check=False,
                env=dict(request.environment),
            )
            result = self._result(
                request,
                status="passed" if completed.returncode == 0 else "failed",
                argv=argv,
                cwd=cwd,
                returncode=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                duration_seconds=time.monotonic() - start,
                reason_code=None if completed.returncode == 0 else "COMMAND_FAILED",
                message=(
                    None
                    if completed.returncode == 0
                    else "Validation action returned a nonzero exit code."
                ),
                environment_filtered=request.environment_filtered,
            )
        except subprocess.TimeoutExpired as exc:
            result = self._result(
                request,
                status="timed_out",
                argv=argv,
                cwd=cwd,
                returncode=None,
                stdout=_timeout_text(exc.stdout),
                stderr=_timeout_text(exc.stderr),
                duration_seconds=time.monotonic() - start,
                timed_out=True,
                reason_code="COMMAND_TIMEOUT",
                message=f"Action exceeded its {request.timeout_seconds} second timeout.",
                environment_filtered=request.environment_filtered,
            )
        except OSError as exc:
            result = self._result(
                request,
                status="failed",
                argv=argv,
                cwd=cwd,
                returncode=None,
                stdout="",
                stderr=str(exc),
                duration_seconds=time.monotonic() - start,
                reason_code="COMMAND_START_FAILED",
                message="The allowlisted executable could not be started.",
                environment_filtered=request.environment_filtered,
            )
        handle.executions.append(result)
        return result


class LocalProcessSandboxBackend(_LocalBackendBase):
    """Best-effort local process hardening without external dependencies.

    This backend is safer than compatibility mode, but it is still not a
    kernel-enforced sandbox, container, Windows Job Object, cgroup, or network
    namespace.
    """

    backend_id = "local-process-restricted"
    safety_level = "process-restricted"
    limitation_notes = (
        "No kernel-level filesystem or user isolation is provided.",
        "Network deny requests are recorded but cannot be enforced portably.",
        "Descendant cleanup is best effort without Windows Job Objects or Linux cgroups.",
    )

    @staticmethod
    def _filtered_environment(environment: Mapping[str, str]) -> dict[str, str]:
        allowed_names = {name.casefold() for name in _LOCAL_ENVIRONMENT_ALLOWLIST}
        return {
            name: str(value)
            for name, value in environment.items()
            if name.casefold() in allowed_names
        }

    @staticmethod
    def _popen_group_options() -> dict[str, Any]:
        if os.name == "nt":
            return {
                "creationflags": int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)),
            }
        return {"start_new_session": True}

    @staticmethod
    def _terminate_group(process: subprocess.Popen[str]) -> None:
        if process.poll() is not None:
            return
        try:
            if os.name != "nt":
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
        except (OSError, ProcessLookupError):
            with suppress(OSError):
                process.kill()

    def execute(
        self,
        handle: SandboxHandle,
        request: SandboxExecutionRequest,
        *,
        should_cancel: Callable[[], bool] | None = None,
    ) -> SandboxExecutionResult:
        argv, cwd = self._validate_request(handle, request)
        environment = self._filtered_environment(request.environment)
        if should_cancel is not None and should_cancel():
            result = self._cancelled_result(
                request,
                argv,
                cwd,
                environment_filtered=True,
            )
            handle.executions.append(result)
            return result
        start = time.monotonic()
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                list(argv),
                cwd=cwd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                **self._popen_group_options(),
            )
            try:
                stdout, stderr = process.communicate(timeout=request.timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                self._terminate_group(process)
                try:
                    stdout, stderr = process.communicate(timeout=2)
                except subprocess.TimeoutExpired as cleanup_error:
                    self._terminate_group(process)
                    stdout = _timeout_text(cleanup_error.stdout)
                    stderr = _timeout_text(cleanup_error.stderr)
                    for stream in (process.stdout, process.stderr):
                        if stream is not None:
                            with suppress(OSError):
                                stream.close()
                result = self._result(
                    request,
                    status="timed_out",
                    argv=argv,
                    cwd=cwd,
                    returncode=process.returncode,
                    stdout=_timeout_text(exc.stdout) or stdout,
                    stderr=_timeout_text(exc.stderr) or stderr,
                    duration_seconds=time.monotonic() - start,
                    timed_out=True,
                    reason_code="COMMAND_TIMEOUT",
                    message=f"Action exceeded its {request.timeout_seconds} second timeout.",
                    environment_filtered=True,
                )
            else:
                result = self._result(
                    request,
                    status="passed" if process.returncode == 0 else "failed",
                    argv=argv,
                    cwd=cwd,
                    returncode=process.returncode,
                    stdout=stdout,
                    stderr=stderr,
                    duration_seconds=time.monotonic() - start,
                    reason_code=None if process.returncode == 0 else "COMMAND_FAILED",
                    message=(
                        None
                        if process.returncode == 0
                        else "Validation action returned a nonzero exit code."
                    ),
                    environment_filtered=True,
                )
        except OSError as exc:
            if process is not None:
                self._terminate_group(process)
            result = self._result(
                request,
                status="failed",
                argv=argv,
                cwd=cwd,
                returncode=None,
                stdout="",
                stderr=str(exc),
                duration_seconds=time.monotonic() - start,
                reason_code="COMMAND_START_FAILED",
                message="The allowlisted executable could not be started.",
                environment_filtered=True,
            )
        handle.executions.append(result)
        return result


__all__ = ["LocalProcessSandboxBackend", "UnsafeLocalSandboxBackend"]
