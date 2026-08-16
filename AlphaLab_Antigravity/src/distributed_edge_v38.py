from __future__ import annotations

"""V3.8 evaluator contract.

V3.8 intentionally reuses the already-audited V3.5 full 14-gate evaluator
without changing any threshold. This wrapper fail-closes if that contract drifts.
"""

from typing import Dict, Tuple
import pandas as pd

from distributed_edge_v35 import (
    EVAL_START,
    EVAL_END,
    EXPECTED_QUARTERS,
    EXPECTED_R4,
    EXPECTED_R8,
    FULL_YEARS,
    evaluate_distribution as _evaluate_distribution,
)

EXPECTED_GATE_NAMES = [
    "gate_A1",
    "gate_A2",
    "gate_A3",
    "gate_A4",
    "gate_B1",
    "gate_B2",
    "gate_D4_1",
    "gate_D4_2",
    "gate_D8_1",
    "gate_D8_2",
    "gate_Y1",
    "gate_Y2",
    "gate_E1",
    "gate_E2",
]


def evaluate_distribution_v38(
    config_id: str,
    raw_trades: pd.DataFrame,
) -> Tuple[Dict, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    result = _evaluate_distribution(config_id, raw_trades)
    summary, eval_trades, qdf, r4, r8, ydf = result

    if EVAL_START != "2018Q2" or EVAL_END != "2026Q2":
        raise RuntimeError("V3.8 evaluation window drift")
    if EXPECTED_QUARTERS != 33 or EXPECTED_R4 != 30 or EXPECTED_R8 != 26:
        raise RuntimeError("V3.8 temporal window count drift")
    if FULL_YEARS != list(range(2019, 2026)):
        raise RuntimeError("V3.8 complete-year contract drift")

    missing = [g for g in EXPECTED_GATE_NAMES if g not in summary]
    if missing:
        raise RuntimeError(f"V3.8 evaluator missing frozen gates: {missing}")

    expected_all = all(bool(summary[g]) for g in EXPECTED_GATE_NAMES)
    if bool(summary.get("all_gates_pass")) != expected_all:
        raise RuntimeError("V3.8 all_gates_pass is not the conjunction of all 14 gates")

    if len(qdf) != 33 or len(r4) != 30 or len(r8) != 26:
        raise RuntimeError("V3.8 evaluator returned wrong temporal table sizes")

    return result
