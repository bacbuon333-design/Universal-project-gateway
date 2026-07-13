"""Runtime adapter selection without exposing arbitrary command execution."""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

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
) -> RuntimeAdapter:
    normalized = project_type.strip().casefold()
    if normalized in {"python", "py"}:
        return PythonAdapter(workspace_root, commands, timeout_seconds=timeout_seconds)
    if normalized in {"node", "nodejs", "javascript"}:
        return NodeAdapter(workspace_root, commands, timeout_seconds=timeout_seconds)
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
