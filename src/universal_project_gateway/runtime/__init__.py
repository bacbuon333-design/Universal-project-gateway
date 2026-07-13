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
from .registry import (
    AdapterRegistry,
    AdapterRegistryError,
    AdapterResolution,
    built_in_adapter_registry,
)


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
    aliases = {
        "py": "python",
        "javascript": "node",
        "nodejs": "node",
    }
    normalized = aliases.get(project_type.strip().casefold(), project_type.strip().casefold())
    registry = built_in_adapter_registry()
    try:
        capability = registry.resolve_project_type(normalized)
    except AdapterRegistryError as exc:
        raise RuntimeAdapterError(
            "project type does not have an installed runtime adapter",
            code="RUNTIME_ADAPTER_NOT_FOUND",
            details={"project_type": project_type},
        ) from exc
    resolution = AdapterResolution(
        adapter=capability,
        project_type=normalized,
        runtime_action="inspect_environment",
        capability="inspect",
    )
    return registry.create(
        resolution,
        workspace_root,
        commands,
        timeout_seconds=timeout_seconds,
        sandbox_backend=sandbox_backend,
        sandbox_handle=sandbox_handle,
        should_cancel=should_cancel,
    )


get_runtime_adapter = create_runtime_adapter


__all__ = [
    "BaseRuntimeAdapter",
    "AdapterRegistry",
    "AdapterRegistryError",
    "AdapterResolution",
    "CommandResult",
    "NodeAdapter",
    "PythonAdapter",
    "RuntimeAdapter",
    "RuntimeAdapterError",
    "built_in_adapter_registry",
    "create_runtime_adapter",
    "get_runtime_adapter",
]
