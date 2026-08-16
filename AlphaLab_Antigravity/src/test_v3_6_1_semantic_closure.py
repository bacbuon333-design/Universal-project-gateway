from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


ts = load("v361_ts", "audit_v3_6_1_timestamp_semantics.py")
vd = load("v361_vd", "evaluate_v3_6_1_frozen_verdict.py")


def test_timestamp_classifier_open_only():
    evidence = {
        "open_time_hits": [{"excerpt": "timestamp is bar open time", "file": "x.py", "pattern": "x"}],
        "close_time_hits": [],
    }
    d = ts.classify(evidence)
    assert d["semantic"] == "BAR_OPEN_TIME"
    assert d["confidence"] == "HIGH"


def test_timestamp_classifier_close_only():
    evidence = {
        "open_time_hits": [],
        "close_time_hits": [{"excerpt": "timestamp is bar close time", "file": "x.py", "pattern": "x"}],
    }
    d = ts.classify(evidence)
    assert d["semantic"] == "BAR_CLOSE_TIME"
    assert d["confidence"] == "HIGH"


def test_timestamp_classifier_conflict_is_ambiguous():
    evidence = {
        "open_time_hits": [{"excerpt": "timestamp is bar open time", "file": "a.py", "pattern": "x"}],
        "close_time_hits": [{"excerpt": "timestamp is bar close time", "file": "b.py", "pattern": "y"}],
    }
    d = ts.classify(evidence)
    assert d["semantic"] == "UNRESOLVED"


def test_timestamp_classifier_cadence_not_semantic_evidence():
    evidence = {"open_time_hits": [], "close_time_hits": []}
    d = ts.classify(evidence)
    assert d["status"] == "TIMESTAMP_SEMANTICS_AMBIGUOUS"


def test_existing_v36_frozen_rules_trigger_from_committed_raw_outputs():
    ev = vd.frozen_rule_evidence()
    assert ev["rule4_triggered"] is True
    assert ev["rule5_triggered"] is True
    assert ev["any_triggered"] is True
    assert all(ev["rule4_ci"][h]["crosses_zero"] for h in vd.KEY)
    assert all(ev["effect_below_cost"][h] for h in vd.KEY)


def test_close_time_applies_any_rule_and_not_supported():
    d = vd.decide("BAR_CLOSE_TIME", {"any_triggered": True})
    assert d["status"] == "APPLY_FROZEN_ANY_RULE"
    assert d["classification"] == "LMDC MECHANISM NOT SUPPORTED"


def test_open_time_requires_exact_alignment_reproduction():
    d = vd.decide("BAR_OPEN_TIME", {"any_triggered": True})
    assert d["status"] == "ALIGNMENT_REPRODUCTION_REQUIRED"


def test_unresolved_timestamp_does_not_choose_post_hoc_convention():
    d = vd.decide("UNRESOLVED", {"any_triggered": True})
    assert d["status"] == "TIMESTAMP_SEMANTICS_UNRESOLVED"


if __name__ == "__main__":
    tests = [
        test_timestamp_classifier_open_only,
        test_timestamp_classifier_close_only,
        test_timestamp_classifier_conflict_is_ambiguous,
        test_timestamp_classifier_cadence_not_semantic_evidence,
        test_existing_v36_frozen_rules_trigger_from_committed_raw_outputs,
        test_close_time_applies_any_rule_and_not_supported,
        test_open_time_requires_exact_alignment_reproduction,
        test_unresolved_timestamp_does_not_choose_post_hoc_convention,
    ]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"\nAll {len(tests)} tests passed successfully!")
