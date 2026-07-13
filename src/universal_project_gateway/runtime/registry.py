"""Versioned runtime adapter capability registry and deterministic resolution."""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from ..contracts import ADAPTER_CONTRACT_VERSION, AdapterCapability
from ..models import GatewayError, ProjectManifest
from ..sandbox import SandboxBackend, SandboxHandle
from .base import ACTION_NAMES, RuntimeAdapter

_ADAPTER_ID = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")
_ADAPTER_VERSION = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:[-+][A-Za-z0-9.-]+)?$")
_CAPABILITY_BY_ACTION = {
    "install": "install",
    "lint": "lint",
    "test": "test",
    "build": "build",
    "smoke_test": "smoke",
}
_KNOWN_CAPABILITIES = frozenset({"inspect", *_CAPABILITY_BY_ACTION.values()})


class AdapterRegistryError(GatewayError):
    """Structured adapter registration or compatibility failure."""

    default_code = "ADAPTER_REGISTRY_ERROR"


@dataclass(frozen=True, slots=True)
class AdapterCompatibilityIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True, slots=True)
class AdapterResolution:
    """One manifest action resolved to one installed adapter capability."""

    adapter: AdapterCapability
    project_type: str
    runtime_action: str
    capability: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter.adapter_id,
            "adapter_version": self.adapter.adapter_version,
            "contract_version": self.adapter.contract_version,
            "project_type": self.project_type,
            "runtime_action": self.runtime_action,
            "capability": self.capability,
        }


def current_platform_id() -> str:
    if os.name == "nt":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


class AdapterRegistry:
    """Register typed adapters and resolve manifest-declared named actions."""

    def __init__(self) -> None:
        self._adapter_types: dict[str, type[RuntimeAdapter]] = {}

    def register(self, adapter_type: type[RuntimeAdapter]) -> None:
        if not isinstance(adapter_type, type) or not issubclass(adapter_type, RuntimeAdapter):
            raise AdapterRegistryError(
                "registered adapter must implement RuntimeAdapter",
                code="INVALID_ADAPTER_TYPE",
            )
        capability = getattr(adapter_type, "capability", None)
        if not isinstance(capability, AdapterCapability):
            raise AdapterRegistryError(
                "adapter must declare an AdapterCapability",
                code="INVALID_ADAPTER_CAPABILITY",
            )
        adapter_id = capability.adapter_id.casefold()
        if not _ADAPTER_ID.fullmatch(adapter_id):
            raise AdapterRegistryError(
                "adapter_id must be lowercase and filesystem-safe",
                code="INVALID_ADAPTER_ID",
                details={"adapter_id": capability.adapter_id},
            )
        if adapter_id != capability.adapter_id or adapter_type.adapter_name != adapter_id:
            raise AdapterRegistryError(
                "adapter capability identity must match adapter_name",
                code="ADAPTER_ID_MISMATCH",
                details={"adapter_id": capability.adapter_id},
            )
        if capability.contract_version != ADAPTER_CONTRACT_VERSION:
            raise AdapterRegistryError(
                "adapter contract version is unsupported",
                code="ADAPTER_CONTRACT_INCOMPATIBLE",
                details={
                    "adapter_id": adapter_id,
                    "contract_version": capability.contract_version,
                    "supported": ADAPTER_CONTRACT_VERSION,
                },
            )
        if not _ADAPTER_VERSION.fullmatch(capability.adapter_version):
            raise AdapterRegistryError(
                "adapter_version must be a semantic version",
                code="INVALID_ADAPTER_VERSION",
                details={"adapter_id": adapter_id},
            )
        if not capability.supported_project_types or not capability.supported_platforms:
            raise AdapterRegistryError(
                "adapter must declare project types and platforms",
                code="INVALID_ADAPTER_CAPABILITY",
                details={"adapter_id": adapter_id},
            )
        unknown_capabilities = set(capability.capabilities) - _KNOWN_CAPABILITIES
        if not capability.capabilities or unknown_capabilities:
            raise AdapterRegistryError(
                "adapter declares an unsupported capability name",
                code="INVALID_ADAPTER_CAPABILITY",
                details={
                    "adapter_id": adapter_id,
                    "unknown_capabilities": sorted(unknown_capabilities),
                },
            )
        if adapter_id in self._adapter_types:
            raise AdapterRegistryError(
                "adapter_id is already registered",
                code="DUPLICATE_ADAPTER_ID",
                details={"adapter_id": adapter_id},
            )
        self._adapter_types[adapter_id] = adapter_type

    def get(self, adapter_id: str) -> AdapterCapability:
        normalized = adapter_id.strip().casefold()
        try:
            return self._adapter_types[normalized].capability
        except KeyError as exc:
            raise AdapterRegistryError(
                "runtime adapter is not registered",
                code="ADAPTER_NOT_REGISTERED",
                details={"adapter_id": adapter_id},
            ) from exc

    def list_capabilities(self) -> tuple[AdapterCapability, ...]:
        return tuple(
            self._adapter_types[adapter_id].capability
            for adapter_id in sorted(self._adapter_types)
        )

    def resolve(self, manifest: ProjectManifest, action: str) -> AdapterResolution:
        if action not in ACTION_NAMES:
            raise AdapterRegistryError(
                "runtime action is not part of the execution contract",
                code="ADAPTER_CAPABILITY_UNKNOWN",
                details={"action": action},
            )
        capability_name = _CAPABILITY_BY_ACTION[action]
        command = manifest.command(action)
        declared = command.adapter.casefold() if command and command.adapter else None
        candidate_ids = (declared,) if declared else manifest.runtime_adapters
        platform_id = current_platform_id()
        compatible: list[AdapterCapability] = []
        for adapter_id in candidate_ids:
            capability = self.get(adapter_id)
            if manifest.project_type not in {
                value.casefold() for value in capability.supported_project_types
            }:
                continue
            if platform_id not in {value.casefold() for value in capability.supported_platforms}:
                continue
            if capability_name not in capability.capabilities:
                continue
            compatible.append(capability)
        if not compatible:
            raise AdapterRegistryError(
                "no declared adapter supports this project type, platform, and capability",
                code="ADAPTER_CAPABILITY_INCOMPATIBLE",
                details={
                    "action": action,
                    "capability": capability_name,
                    "project_type": manifest.project_type,
                    "platform": platform_id,
                    "declared_adapters": list(candidate_ids),
                },
            )
        if len(compatible) > 1:
            exact = [item for item in compatible if item.adapter_id == manifest.project_type]
            if len(exact) == 1:
                compatible = exact
            else:
                raise AdapterRegistryError(
                    "multiple adapters match; declare commands.<action>.adapter explicitly",
                    code="ADAPTER_RESOLUTION_AMBIGUOUS",
                    details={
                        "action": action,
                        "adapter_ids": sorted(item.adapter_id for item in compatible),
                    },
                )
        return AdapterResolution(
            adapter=compatible[0],
            project_type=manifest.project_type,
            runtime_action=action,
            capability=capability_name,
        )

    def resolve_project_type(self, project_type: str) -> AdapterCapability:
        normalized = project_type.strip().casefold()
        platform_id = current_platform_id()
        compatible = [
            capability
            for capability in self.list_capabilities()
            if normalized in {item.casefold() for item in capability.supported_project_types}
            and platform_id in {item.casefold() for item in capability.supported_platforms}
        ]
        if len(compatible) != 1:
            raise AdapterRegistryError(
                "project type does not resolve to exactly one installed runtime adapter",
                code=(
                    "ADAPTER_NOT_REGISTERED"
                    if not compatible
                    else "ADAPTER_RESOLUTION_AMBIGUOUS"
                ),
                details={"project_type": project_type},
            )
        return compatible[0]

    def create(
        self,
        resolution: AdapterResolution,
        workspace_root: str | os.PathLike[str],
        commands: Mapping[str, Any] | Any,
        *,
        timeout_seconds: int = 120,
        sandbox_backend: SandboxBackend | None = None,
        sandbox_handle: SandboxHandle | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> RuntimeAdapter:
        adapter_type = self._adapter_types[resolution.adapter.adapter_id]
        return adapter_type(
            workspace_root,
            commands,
            timeout_seconds=timeout_seconds,
            sandbox_backend=sandbox_backend,
            sandbox_handle=sandbox_handle,
            should_cancel=should_cancel,
        )

    def validate_manifest(self, manifest: ProjectManifest) -> tuple[AdapterCompatibilityIssue, ...]:
        issues: list[AdapterCompatibilityIssue] = []
        for index, adapter_id in enumerate(manifest.runtime_adapters):
            try:
                capability = self.get(adapter_id)
            except AdapterRegistryError:
                issues.append(
                    AdapterCompatibilityIssue(
                        "UNKNOWN_RUNTIME_ADAPTER",
                        f"runtime_adapters[{index}]",
                        f"runtime adapter {adapter_id!r} is not registered",
                    )
                )
                continue
            if manifest.project_type not in {
                value.casefold() for value in capability.supported_project_types
            }:
                issues.append(
                    AdapterCompatibilityIssue(
                        "INCOMPATIBLE_RUNTIME_ADAPTER",
                        f"runtime_adapters[{index}]",
                        f"adapter {adapter_id!r} does not support project_type {manifest.project_type!r}",
                    )
                )

        for index, requirement in enumerate(manifest.adapter_requirements):
            path = f"adapter_requirements[{index}]"
            if requirement.adapter_id not in manifest.runtime_adapters:
                issues.append(
                    AdapterCompatibilityIssue(
                        "ADAPTER_REQUIREMENT_NOT_DECLARED",
                        f"{path}.adapter_id",
                        "required adapter must also appear in runtime_adapters",
                    )
                )
                continue
            try:
                capability = self.get(requirement.adapter_id)
            except AdapterRegistryError:
                continue
            if requirement.contract_version != capability.contract_version:
                issues.append(
                    AdapterCompatibilityIssue(
                        "ADAPTER_CONTRACT_INCOMPATIBLE",
                        f"{path}.contract_version",
                        f"adapter requires contract {capability.contract_version!r}",
                    )
                )
            if (
                requirement.adapter_version is not None
                and requirement.adapter_version != capability.adapter_version
            ):
                issues.append(
                    AdapterCompatibilityIssue(
                        "ADAPTER_VERSION_INCOMPATIBLE",
                        f"{path}.adapter_version",
                        f"installed adapter version is {capability.adapter_version!r}",
                    )
                )
            for capability_name in requirement.capabilities:
                normalized = _CAPABILITY_BY_ACTION.get(capability_name, capability_name)
                if normalized not in capability.capabilities:
                    issues.append(
                        AdapterCompatibilityIssue(
                            "ADAPTER_CAPABILITY_UNSUPPORTED",
                            f"{path}.capabilities",
                            f"adapter {requirement.adapter_id!r} does not support {capability_name!r}",
                        )
                    )

        for action, command in manifest.commands.items():
            if command is None:
                continue
            try:
                self.resolve(manifest, action)
            except AdapterRegistryError as exc:
                issues.append(
                    AdapterCompatibilityIssue(
                        exc.code,
                        f"commands.{action}.adapter",
                        exc.message,
                    )
                )
        return tuple(issues)


def built_in_adapter_registry() -> AdapterRegistry:
    """Create a fresh registry containing only reviewed built-in adapters."""

    from .node_adapter import NodeAdapter
    from .python_adapter import PythonAdapter

    registry = AdapterRegistry()
    registry.register(PythonAdapter)
    registry.register(NodeAdapter)
    return registry


__all__ = [
    "AdapterCompatibilityIssue",
    "AdapterRegistry",
    "AdapterRegistryError",
    "AdapterResolution",
    "built_in_adapter_registry",
    "current_platform_id",
]
