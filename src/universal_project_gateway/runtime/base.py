"""Common interface for fixed, manifest-declared runtime actions."""

from __future__ import annotations

import abc
import dataclasses
import os
import re
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from ..models import CommandSpec, GatewayError
from ..sandbox import (
    SandboxBackend,
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxHandle,
    UnsafeLocalSandboxBackend,
)
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


CommandResult = SandboxExecutionResult


class RuntimeAdapter(abc.ABC):
    """Base class exposing fixed action methods instead of generic execution."""

    adapter_name = "base"

    def __init__(
        self,
        workspace_root: str | os.PathLike[str],
        commands: Mapping[str, Any] | Any,
        *,
        timeout_seconds: int = 120,
        sandbox_backend: SandboxBackend | None = None,
        sandbox_handle: SandboxHandle | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> None:
        candidate = Path(workspace_root).expanduser().absolute()
        if is_reparse_point(candidate):
            raise RuntimeAdapterError(
                "runtime working directory must not be a symlink or reparse point",
                code="INVALID_RUNTIME_WORKSPACE",
                details={"workspace_root": str(candidate)},
            )
        root = candidate.resolve(strict=True)
        if not root.is_dir():
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
        self.sandbox_backend = sandbox_backend or UnsafeLocalSandboxBackend()
        self.sandbox_handle = sandbox_handle or self.sandbox_backend.prepare(
            root,
            should_cancel=should_cancel,
        )
        if self.sandbox_handle.workspace_root != root:
            raise RuntimeAdapterError(
                "sandbox handle does not belong to the runtime workspace",
                code="SANDBOX_WORKSPACE_MISMATCH",
            )
        self.should_cancel = should_cancel

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
        request = SandboxExecutionRequest(
            action=action,
            argv=argv,
            cwd=self.workspace_root,
            timeout_seconds=timeout,
            environment=environment,
            environment_filtered=True,
            network_policy="unrestricted",
        )
        return self.sandbox_backend.execute(
            self.sandbox_handle,
            request,
            should_cancel=self.should_cancel,
        )

    def _inspect_runtime(self, argv: tuple[str, ...]) -> CommandResult:
        """Execute one adapter-fixed availability probe through the backend."""

        request = SandboxExecutionRequest(
            action="inspect_environment",
            argv=argv,
            cwd=self.workspace_root,
            timeout_seconds=min(self.timeout_seconds, 10),
            environment=self._environment(CommandSpec(argv)),
            environment_filtered=True,
            network_policy="unrestricted",
        )
        return self.sandbox_backend.execute(
            self.sandbox_handle,
            request,
            should_cancel=self.should_cancel,
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
            backend_id=self.sandbox_backend.backend_id,
            safety_level=self.sandbox_backend.safety_level,
            timeout_seconds=0,
            shell_disabled=True,
            environment_filtered=True,
            network_policy="unrestricted",
            network_policy_enforced=False,
            limitation_notes=self.sandbox_backend.limitation_notes,
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


BaseRuntimeAdapter = RuntimeAdapter


__all__ = [
    "ACTION_NAMES",
    "BaseRuntimeAdapter",
    "CommandResult",
    "RuntimeAdapter",
    "RuntimeAdapterError",
    "safe_relative_argument",
]
