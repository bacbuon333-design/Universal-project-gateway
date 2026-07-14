"""Universal Project Gateway public package surface."""

from .config import GatewayConfig
from .contracts import (
    ADAPTER_CONTRACT_VERSION,
    CONTRACT_VERSIONS,
    EVIDENCE_CONTRACT_VERSION,
    EXECUTION_CONTRACT_VERSION,
    MANIFEST_CONTRACT_VERSION,
    PROJECT_INTELLIGENCE_CONTRACT_VERSION,
    AdapterCapability,
    AdapterRequirement,
    get_contract_schema,
)
from .models import (
    CommandSpec,
    GatewayError,
    Job,
    JobEvent,
    JobStatus,
    NormalizedIntent,
    PolicyDecision,
    ProjectManifest,
    ProjectRecord,
    RiskLevel,
)

__all__ = [
    "ADAPTER_CONTRACT_VERSION",
    "AdapterCapability",
    "AdapterRequirement",
    "CommandSpec",
    "CONTRACT_VERSIONS",
    "EVIDENCE_CONTRACT_VERSION",
    "EXECUTION_CONTRACT_VERSION",
    "GatewayConfig",
    "GatewayError",
    "Job",
    "JobEvent",
    "JobStatus",
    "MANIFEST_CONTRACT_VERSION",
    "PROJECT_INTELLIGENCE_CONTRACT_VERSION",
    "NormalizedIntent",
    "PolicyDecision",
    "ProjectManifest",
    "ProjectRecord",
    "RiskLevel",
    "get_contract_schema",
]

__version__ = "0.2.0+local"
