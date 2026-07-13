"""Common interface for fixed, manifest-declared runtime actions."""

from __future__ import annotations

import abc
import dataclasses
import os
import re
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..models import CommandSpec, GatewayError
from ..scoped_fs import is_reparse_point

ACTION_NAMES = ("install", "lint", "test", "build", "smoke_test")
_BASE_ENVIRONMENT_NAMES = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "HOME",
    "USERPROFILE",
    "TEMP",
    "TMP",
)
_OPTIONAL_ENVIRONMENT_NAMES = {"CI", "LANG", "LC_ALL", "NO_COLOR", "TERM", "TZ"}
_DANGEROUS_ARGUMENT = re.compile(r"(?:\r|\n|\x00|&&|\|\||[;|`]|\$\(|>\s*|<\s*)")


class RuntimeAdapterError(GatewayError):
    default_code = "RUNTIME_ADAPTER_ERROR"


@dataclass(frozen=True, slots=True)
class CommandResult:
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

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    @property
    def success(self) -> bool:
        return self.passed

    def to_dict(self) -> dict[str, Any]:
        return {
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
        }


class RuntimeAdapter(abc.ABC):
    """Base class exposing fixed action methods instead of generic execution."""

    adapter_name = "base"

    def __init__(
        self,
        workspace_root: str | os.PathLike[str],
        commands: Mapping[str, Any] | Any,
        *,
        timeout_seconds: int = 120,
    ) -> None:
        root = Path(workspace_root).expanduser().resolve(strict=True)
        if not root.is_dir() or is_reparse_point(root):
            raise RuntimeAdapterError(
                "runtime working directory must be a real workspace directory",
                code="INVALID_RUNTIME_WORKSPACE",
                details={"workspace_root": str(root)},
            )
        if not 1 <= timeout_seconds <= 600:
            raise ValueError("timeout_seconds must be from 1 to 600")
        if hasattr(commands, "commands"):
            commands = commands.commands
        if not isinstance(commands, Mapping):
            raise RuntimeAdapterError("commands must be a mapping", code="INVALID_COMMANDS")
        self.workspace_root = root
        self.commands = dict(commands)
        self.timeout_seconds = timeout_seconds

    @abc.abstractmethod
    def inspect_environment(self) -> dict[str, Any]:
        """Report adapter availability without mutating the workspace."""

    @abc.abstractmethod
    def _validated_argv(self, action: str, spec: CommandSpec) -> tuple[str, ...]:
        """Validate and resolve an administrator-declared command."""

    def install_dependencies(self, *, enabled: bool = False) -> CommandResult:
        if not enabled:
            return self._not_run(
                "install",
                status="skipped",
                reason_code="DEPENDENCY_INSTALL_DISABLED",
                message="Dependency installation is disabled unless explicitly enabled.",
            )
        return self._run_declared("install")

    def run_lint(self) -> CommandResult:
        return self._run_declared("lint")

    def run_tests(self) -> CommandResult:
        return self._run_declared("test")

    def run_build(self) -> CommandResult:
        return self._run_declared("build")

    def run_smoke_test(self) -> CommandResult:
        return self._run_declared("smoke_test")

    def _spec(self, action: str) -> CommandSpec | None:
        raw = self.commands.get(action)
        if raw is None:
            return None
        if isinstance(raw, CommandSpec):
            return raw
        if dataclasses.is_dataclass(raw) and hasattr(raw, "argv"):
            return CommandSpec(
                argv=tuple(str(item) for item in raw.argv),
                timeout_seconds=int(getattr(raw, "timeout_seconds", self.timeout_seconds)),
                adapter=getattr(raw, "adapter", None),
                environment=tuple(getattr(raw, "environment", ())),
            )
        if isinstance(raw, Mapping):
            argv = raw.get("argv")
            if not isinstance(argv, Sequence) or isinstance(argv, (str, bytes)):
                raise RuntimeAdapterError(
                    "declared command must contain an argv list",
                    code="COMMAND_MUST_USE_ARGV",
                    details={"action": action},
                )
            return CommandSpec(
                argv=tuple(str(item) for item in argv),
                timeout_seconds=int(raw.get("timeout_seconds", self.timeout_seconds)),
                adapter=str(raw["adapter"]) if raw.get("adapter") is not None else None,
                environment=tuple(str(item) for item in raw.get("environment", ())),
            )
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            return CommandSpec(tuple(str(item) for item in raw), self.timeout_seconds)
        raise RuntimeAdapterError(
            "declared command must be null, an argv mapping, or CommandSpec",
            code="COMMAND_MUST_USE_ARGV",
            details={"action": action},
        )

    def _run_declared(self, action: str) -> CommandResult:
        if action not in ACTION_NAMES:
            # Kept private so callers cannot turn this into a generic command
            # runner, but also defend the boundary for subclass use.
            raise RuntimeAdapterError(
                "runtime action is not supported",
                code="RUNTIME_ACTION_FORBIDDEN",
                details={"action": action},
            )
        spec = self._spec(action)
        if spec is None:
            return self._not_run(
                action,
                status="not_run",
                reason_code="COMMAND_NOT_DECLARED",
                message="The project manifest does not declare this action.",
            )
        if not spec.argv:
            raise RuntimeAdapterError(
                "declared argv may not be empty",
                code="INVALID_COMMAND_ARGV",
                details={"action": action},
            )
        if spec.adapter and spec.adapter.casefold() not in {
            self.adapter_name.casefold(),
            self.adapter_name.removesuffix("_adapter").casefold(),
        }:
            raise RuntimeAdapterError(
                "command declares a different runtime adapter",
                code="RUNTIME_ADAPTER_MISMATCH",
                details={"action": action, "declared": spec.adapter, "actual": self.adapter_name},
            )
        if any(_DANGEROUS_ARGUMENT.search(argument) for argument in spec.argv):
            raise RuntimeAdapterError(
                "command argv contains a prohibited shell or control token",
                code="UNSAFE_COMMAND_ARGUMENT",
                details={"action": action},
            )
        argv = self._validated_argv(action, spec)
        timeout = spec.timeout_seconds
        if not 1 <= timeout <= 600:
            raise RuntimeAdapterError(
                "command timeout must be from 1 to 600 seconds",
                code="INVALID_COMMAND_TIMEOUT",
                details={"action": action, "timeout_seconds": timeout},
            )
        environment = self._environment(spec)
        start = time.monotonic()
        try:
            completed = subprocess.run(
                list(argv),
                cwd=self.workspace_root,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                env=environment,
            )
        except subprocess.TimeoutExpired as exc:
            duration = round(time.monotonic() - start, 6)
            return CommandResult(
                action=action,
                status="timed_out",
                argv=argv,
                cwd=str(self.workspace_root),
                returncode=None,
                stdout=_timeout_text(exc.stdout),
                stderr=_timeout_text(exc.stderr),
                duration_seconds=duration,
                timed_out=True,
                reason_code="COMMAND_TIMEOUT",
                message=f"Action exceeded its {timeout} second timeout.",
            )
        except OSError as exc:
            duration = round(time.monotonic() - start, 6)
            return CommandResult(
                action=action,
                status="failed",
                argv=argv,
                cwd=str(self.workspace_root),
                returncode=None,
                stdout="",
                stderr=str(exc),
                duration_seconds=duration,
                reason_code="COMMAND_START_FAILED",
                message="The allowlisted executable could not be started.",
            )
        duration = round(time.monotonic() - start, 6)
        return CommandResult(
            action=action,
            status="passed" if completed.returncode == 0 else "failed",
            argv=argv,
            cwd=str(self.workspace_root),
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
            duration_seconds=duration,
            reason_code=None if completed.returncode == 0 else "COMMAND_FAILED",
            message=None if completed.returncode == 0 else "Validation action returned a nonzero exit code.",
        )

    def _environment(self, spec: CommandSpec) -> dict[str, str]:
        environment = {
            name: os.environ[name] for name in _BASE_ENVIRONMENT_NAMES if name in os.environ
        }
        for name in spec.environment:
            if name not in _OPTIONAL_ENVIRONMENT_NAMES:
                raise RuntimeAdapterError(
                    "command requests a non-allowlisted environment variable",
                    code="ENVIRONMENT_VARIABLE_FORBIDDEN",
                    details={"name": name},
                )
            if name in os.environ:
                environment[name] = os.environ[name]
        environment.update(self._fixed_environment())
        return environment

    def _fixed_environment(self) -> dict[str, str]:
        return {"CI": "1", "NO_COLOR": "1"}

    def _not_run(
        self,
        action: str,
        *,
        status: str,
        reason_code: str,
        message: str,
    ) -> CommandResult:
        return CommandResult(
            action=action,
            status=status,
            argv=(),
            cwd=str(self.workspace_root),
            returncode=None,
            stdout="",
            stderr="",
            duration_seconds=0.0,
            reason_code=reason_code,
            message=message,
        )


def safe_relative_argument(argument: str, *, allow_glob: bool = False) -> str:
    """Validate an argv token that denotes a workspace-relative path."""

    value = argument.replace("\\", "/")
    if not value or value.startswith("/") or re.match(r"^[A-Za-z]:", value):
        raise RuntimeAdapterError(
            "command path must be workspace-relative",
            code="COMMAND_PATH_FORBIDDEN",
            details={"argument": argument},
        )
    parts = tuple(part for part in value.split("/") if part not in {"", "."})
    if ".." in parts or any(":" in part for part in parts):
        raise RuntimeAdapterError(
            "command path may not traverse outside the workspace",
            code="COMMAND_PATH_FORBIDDEN",
            details={"argument": argument},
        )
    if not allow_glob and any(character in value for character in "*?["):
        raise RuntimeAdapterError(
            "command path globs are not permitted here",
            code="COMMAND_PATH_FORBIDDEN",
            details={"argument": argument},
        )
    return value


def _timeout_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


BaseRuntimeAdapter = RuntimeAdapter


__all__ = [
    "ACTION_NAMES",
    "BaseRuntimeAdapter",
    "CommandResult",
    "RuntimeAdapter",
    "RuntimeAdapterError",
    "safe_relative_argument",
]
