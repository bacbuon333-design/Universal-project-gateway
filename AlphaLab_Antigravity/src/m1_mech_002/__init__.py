from __future__ import annotations

"""ALAB-M1-MECH-002 market-state transition research package.

Development-only research on the frozen 2018-2025 GOLD M1 dataset.
No strategy, broker execution, or 2015-2017 holdout access is authorized.
"""

from .state_engine import (
    DEVELOPMENT_START_UTC,
    DEVELOPMENT_END_UTC,
    EXPECTED_DATA_SHA256,
    HORIZONS_MINUTES,
    build_mechanism_event_frame,
    add_gap_aware_state_labels,
    summarize_tail_distribution,
)

__all__ = [
    "DEVELOPMENT_START_UTC",
    "DEVELOPMENT_END_UTC",
    "EXPECTED_DATA_SHA256",
    "HORIZONS_MINUTES",
    "build_mechanism_event_frame",
    "add_gap_aware_state_labels",
    "summarize_tail_distribution",
]
