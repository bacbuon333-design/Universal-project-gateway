from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_6"
OUT = ROOT / "AlphaLab_Antigravity" / "reports" / "v3_6_1"
KEY = ("1h", "2h", "4h")


def read_timestamp_status() -> str:
    p = OUT / "timestamp_semantics_audit.json"
    if not p.exists():
        return "UNRESOLVED"
    obj = json.loads(p.read_text(encoding="utf-8"))
    return obj.get("decision", {}).get("semantic", "UNRESOLVED")


def frozen_rule_evidence() -> dict:
    b = pd.read_csv(SRC / "lmdc_block_bootstrap.csv").set_index("horizon")
    c = json.loads((SRC / "lmdc_cost_benchmark.json").read_text(encoding="utf-8"))

    ci = {}
    for h in KEY:
        lo = float(b.loc[h, "ci_2.5_pct"])
        hi = float(b.loc[h, "ci_97.5_pct"])
        ci[h] = {"low": lo, "high": hi, "crosses_zero": lo <= 0.0 <= hi}
    rule4 = all(v["crosses_zero"] for v in ci.values())

    cost = float(c["cost_in_atr_units"])
    effect = {
        "1h": float(c["observed_1h_signed_atr_return"]),
        "2h": float(c["observed_2h_signed_atr_return"]),
        "4h": float(c["observed_4h_signed_atr_return"]),
    }
    cost_check = {h: abs(v) < cost for h, v in effect.items()}
    rule5 = all(cost_check.values())

    return {
        "rule4_triggered": rule4,
        "rule4_ci": ci,
        "rule5_triggered": rule5,
        "cost_atr": cost,
        "effects_atr": effect,
        "effect_below_cost": cost_check,
        "any_triggered": rule4 or rule5,
    }


def decide(timestamp: str, ev: dict) -> dict:
    if timestamp == "BAR_OPEN_TIME":
        return {
            "status": "ALIGNMENT_REPRODUCTION_REQUIRED",
            "classification": "WITHDRAW_EXISTING_LABEL_PENDING_EXACT_RERUN",
        }
    if timestamp == "BAR_CLOSE_TIME":
        return {
            "status": "APPLY_FROZEN_ANY_RULE",
            "classification": "LMDC MECHANISM NOT SUPPORTED" if ev["any_triggered"] else "NO_FALSIFICATION_TRIGGERED",
        }
    return {
        "status": "TIMESTAMP_SEMANTICS_UNRESOLVED",
        "classification": "WITHDRAW_EXISTING_LABEL_PENDING_SEMANTIC_PROOF",
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ts = read_timestamp_status()
    ev = frozen_rule_evidence()
    result = {
        "timestamp_semantic": ts,
        "frozen_rule_evidence": ev,
        "decision": decide(ts, ev),
    }
    (OUT / "frozen_verdict_audit.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
