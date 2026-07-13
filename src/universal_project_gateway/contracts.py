"""Versioned public contract identifiers and machine-readable schemas.

The schemas are descriptive compatibility contracts used by UPG itself.  They
deliberately avoid adding a runtime JSON Schema dependency; validation at trust
boundaries remains implemented by the typed manifest, adapter, sandbox, and
evidence components.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Final

MANIFEST_CONTRACT_VERSION: Final = "upg.manifest/v1"
ADAPTER_CONTRACT_VERSION: Final = "upg.adapter/v1"
EXECUTION_CONTRACT_VERSION: Final = "upg.execution/v1"
EVIDENCE_CONTRACT_VERSION: Final = "upg.evidence/v1"

CONTRACT_VERSIONS = MappingProxyType(
    {
        "manifest": MANIFEST_CONTRACT_VERSION,
        "adapter": ADAPTER_CONTRACT_VERSION,
        "execution": EXECUTION_CONTRACT_VERSION,
        "evidence": EVIDENCE_CONTRACT_VERSION,
    }
)


@dataclass(frozen=True, slots=True)
class AdapterCapability:
    """Read-only declaration of one installed runtime adapter."""

    adapter_id: str
    adapter_version: str
    contract_version: str
    supported_project_types: tuple[str, ...]
    supported_platforms: tuple[str, ...]
    capabilities: tuple[str, ...]
    required_tools: tuple[str, ...]
    safety_notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "contract_version": self.contract_version,
            "supported_project_types": list(self.supported_project_types),
            "supported_platforms": list(self.supported_platforms),
            "capabilities": list(self.capabilities),
            "required_tools": list(self.required_tools),
            "safety_notes": list(self.safety_notes),
        }


@dataclass(frozen=True, slots=True)
class AdapterRequirement:
    """Optional manifest expectation for an adapter and its capabilities."""

    adapter_id: str
    contract_version: str
    capabilities: tuple[str, ...]
    adapter_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "adapter_id": self.adapter_id,
            "contract_version": self.contract_version,
            "capabilities": list(self.capabilities),
        }
        if self.adapter_version is not None:
            result["adapter_version"] = self.adapter_version
        return result


_STRING_ARRAY = {"type": "array", "items": {"type": "string"}, "uniqueItems": True}
_ARGV_ARRAY = {"type": "array", "items": {"type": "string"}}

_CONTRACT_SCHEMAS: dict[str, dict[str, Any]] = {
    MANIFEST_CONTRACT_VERSION: {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": MANIFEST_CONTRACT_VERSION,
        "type": "object",
        "required": [
            "schema_version",
            "project_id",
            "project_type",
            "commands",
            "runtime_adapters",
            "validation_requirements",
        ],
        "properties": {
            "contract_version": {"const": MANIFEST_CONTRACT_VERSION},
            "schema_version": {"const": "1.0"},
            "project_id": {"type": "string"},
            "project_type": {"type": "string"},
            "commands": {"type": "object"},
            "runtime_adapters": _STRING_ARRAY,
            "validation_requirements": _STRING_ARRAY,
            "adapter_requirements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["adapter_id", "contract_version", "capabilities"],
                    "properties": {
                        "adapter_id": {"type": "string"},
                        "adapter_version": {"type": "string"},
                        "contract_version": {"const": ADAPTER_CONTRACT_VERSION},
                        "capabilities": _STRING_ARRAY,
                    },
                    "additionalProperties": False,
                },
            },
        },
    },
    ADAPTER_CONTRACT_VERSION: {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": ADAPTER_CONTRACT_VERSION,
        "type": "object",
        "required": [
            "adapter_id",
            "adapter_version",
            "contract_version",
            "supported_project_types",
            "supported_platforms",
            "capabilities",
            "required_tools",
            "safety_notes",
        ],
        "properties": {
            "adapter_id": {"type": "string"},
            "adapter_version": {"type": "string"},
            "contract_version": {"const": ADAPTER_CONTRACT_VERSION},
            "supported_project_types": _STRING_ARRAY,
            "supported_platforms": _STRING_ARRAY,
            "capabilities": _STRING_ARRAY,
            "required_tools": _STRING_ARRAY,
            "safety_notes": _STRING_ARRAY,
        },
        "additionalProperties": False,
    },
    EXECUTION_CONTRACT_VERSION: {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": EXECUTION_CONTRACT_VERSION,
        "type": "object",
        "required": ["contract_version", "action", "status", "argv", "sandbox"],
        "properties": {
            "contract_version": {"const": EXECUTION_CONTRACT_VERSION},
            "action": {"type": "string"},
            "status": {"type": "string"},
            "argv": _ARGV_ARRAY,
            "adapter": {"$ref": ADAPTER_CONTRACT_VERSION},
            "sandbox": {"type": "object"},
        },
    },
    EVIDENCE_CONTRACT_VERSION: {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": EVIDENCE_CONTRACT_VERSION,
        "type": "object",
        "required": [
            "contract_version",
            "evidence_schema_version",
            "job_id",
            "project_id",
            "final_event_hash",
        ],
        "properties": {
            "contract_version": {"const": EVIDENCE_CONTRACT_VERSION},
            "evidence_schema_version": {"type": "string"},
            "job_id": {"type": "string"},
            "project_id": {"type": "string"},
            "final_event_hash": {"type": "string"},
        },
    },
}


def get_contract_schema(contract_version: str) -> dict[str, Any]:
    """Return an isolated schema copy so callers cannot mutate the registry."""

    try:
        return copy.deepcopy(_CONTRACT_SCHEMAS[contract_version])
    except KeyError as exc:
        raise ValueError(f"Unknown UPG contract version: {contract_version}") from exc


__all__ = [
    "ADAPTER_CONTRACT_VERSION",
    "AdapterCapability",
    "AdapterRequirement",
    "CONTRACT_VERSIONS",
    "EVIDENCE_CONTRACT_VERSION",
    "EXECUTION_CONTRACT_VERSION",
    "MANIFEST_CONTRACT_VERSION",
    "get_contract_schema",
]
