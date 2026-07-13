"""Runtime adapter selection without exposing arbitrary command execution."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from ..sandbox import SandboxBackend, SandboxHandle
from .base import (
    BaseRuntimeAdapter,
    CommandResult,
    RuntimeAdapter,
    RuntimeAdapterError,
)
from .node_adapter import NodeAdapter
from .python_adapter import PythonAdapter


def create_runtime_adapter(
    project_type: str,
    workspace_root: str | os.PathLike[str],
    commands: Mapping[str, Any] | Any,
    *,
    timeout_seconds: int = 120,
    sandbox_backend: SandboxBackend | None = None,
    sandbox_handle: SandboxHandle | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> RuntimeAdapter:
    normalized = project_type.strip().casefold()
    if normalized in {"python", "py"}:
        return PythonAdapter(
            workspace_root,
            commands,
            timeout_seconds=timeout_seconds,
            sandbox_backend=sandbox_backend,
            sandbox_handle=sandbox_handle,
            should_cancel=should_cancel,
        )
    if normalized in {"node", "nodejs", "javascript"}:
        return NodeAdapter(
            workspace_root,
            commands,
            timeout_seconds=timeout_seconds,
            sandbox_backend=sandbox_backend,
            sandbox_handle=sandbox_handle,
            should_cancel=should_cancel,
        )
    raise RuntimeAdapterError(
        "project type does not have an installed runtime adapter",
        code="RUNTIME_ADAPTER_NOT_FOUND",
        details={"project_type": project_type},
    )


get_runtime_adapter = create_runtime_adapter


__all__ = [
    "BaseRuntimeAdapter",
    "CommandResult",
    "NodeAdapter",
    "PythonAdapter",
    "RuntimeAdapter",
    "RuntimeAdapterError",
    "create_runtime_adapter",
    "get_runtime_adapter",
]
