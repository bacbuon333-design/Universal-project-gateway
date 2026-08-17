from __future__ import annotations

"""ALAB-M1-MECH-003 matched observational control research package."""

from .control_study import (
    EXPERIMENT_ID,
    detect_breach_events,
    build_counterfactual_frame,
    add_frozen_cem_strata,
    compute_cem_weights,
    estimate_matched_effects,
    day_block_bootstrap_5m,
)

__all__ = [
    "EXPERIMENT_ID",
    "detect_breach_events",
    "build_counterfactual_frame",
    "add_frozen_cem_strata",
    "compute_cem_weights",
    "estimate_matched_effects",
    "day_block_bootstrap_5m",
]
