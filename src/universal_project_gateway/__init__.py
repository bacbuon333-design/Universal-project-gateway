"""Universal Project Gateway public package surface."""

from .config import GatewayConfig
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
    "CommandSpec",
    "GatewayConfig",
    "GatewayError",
    "Job",
    "JobEvent",
    "JobStatus",
    "NormalizedIntent",
    "PolicyDecision",
    "ProjectManifest",
    "ProjectRecord",
    "RiskLevel",
]

__version__ = "0.1.0"
