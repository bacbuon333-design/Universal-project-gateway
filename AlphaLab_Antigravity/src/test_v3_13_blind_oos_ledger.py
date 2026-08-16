from __future__ import annotations

from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import tempfile

import pandas as pd

import create_v3_13_blind_oos_checkpoint as ledger
import fresh_oos_v312_contract as v312

UTC = timezone.utc


def _write_checkpoint(directory: Path, sequence: int, stamp: str, previous_name=None, previous_sha=None, payload_sequence=None):
    name = f"{sequence:06d}_{stamp}.json"
    created = datetime.strptime(stamp, "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    obj = {
        "sequence": sequence if payload_sequence is None else payload_sequence,
        "created_at_utc": created.isoformat(),
        "previous_checkpoint_filename": previous_name,
        "previous_checkpoint_sha256": previous_sha,
    }
    p = directory / name
    p.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")
    return p, v312.sha256_file(p)


def test_v312_parent_and_cutoff_are_frozen():
    assert ledger.V312_FINAL_SHA == "c1d7ba04aeb3b5bbc275a1a223c9d2bb5624a315"
    assert v312.CANONICAL_FREEZE_CUTOFF == pd.Timestamp("2026-08-14T23:30:00Z")


def test_maturity_contract_is_unchanged_from_v312():
    assert (v312.MIN_COMPLETE_QUARTERS, v312.MIN_C1_EVENTS, v312.MIN_C4_EVENTS) == (8, 160, 100)
    assert (v312.MIN_C1_PER_QUARTER, v312.MIN_C4_PER_QUARTER) == (10, 5)


def test_checkpoint_filename_is_deterministic():
    ts = pd.Timestamp("2026-08-16T11:00:00Z")
    assert ledger._checkpoint_filename(7, ts) == "000007_20260816T110000Z.json"


def test_empty_chain_is_valid():
    with tempfile.TemporaryDirectory() as td:
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = Path(td)
        try:
            out = ledger.validate_checkpoint_chain(datetime(2026, 8, 16, 12, 0, tzinfo=UTC))
            assert out["checkpoint_count"] == 0
            assert out["latest_checkpoint_sha256"] is None
        finally:
            ledger.CHECKPOINT_DIR = old


def test_genesis_checkpoint_requires_null_parent_and_validates():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p1, sha1 = _write_checkpoint(d, 1, "20260816T110000Z")
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            out = ledger.validate_checkpoint_chain(datetime(2026, 8, 16, 12, 0, tzinfo=UTC))
            assert out["checkpoint_count"] == 1
            assert out["latest_checkpoint_filename"] == p1.name
            assert out["latest_checkpoint_sha256"] == sha1
        finally:
            ledger.CHECKPOINT_DIR = old


def test_two_checkpoint_hash_chain_validates():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p1, sha1 = _write_checkpoint(d, 1, "20260816T110000Z")
        p2, sha2 = _write_checkpoint(d, 2, "20260817T110000Z", p1.name, sha1)
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            out = ledger.validate_checkpoint_chain(datetime(2026, 8, 18, 12, 0, tzinfo=UTC))
            assert out["checkpoint_count"] == 2
            assert out["latest_checkpoint_sha256"] == sha2
            assert out["latest_checkpoint_filename"] == p2.name
        finally:
            ledger.CHECKPOINT_DIR = old


def test_broken_parent_sha_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p1, _ = _write_checkpoint(d, 1, "20260816T110000Z")
        _write_checkpoint(d, 2, "20260817T110000Z", p1.name, "0" * 64)
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            try:
                ledger.validate_checkpoint_chain(datetime(2026, 8, 18, 12, 0, tzinfo=UTC))
            except RuntimeError as exc:
                assert "parent SHA mismatch" in str(exc)
            else:
                raise AssertionError("Broken checkpoint chain must fail")
        finally:
            ledger.CHECKPOINT_DIR = old


def test_sequence_gap_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_checkpoint(d, 2, "20260817T110000Z")
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            try:
                ledger.validate_checkpoint_chain(datetime(2026, 8, 18, 12, 0, tzinfo=UTC))
            except RuntimeError as exc:
                assert "sequence gap/duplicate" in str(exc)
            else:
                raise AssertionError("Sequence gap must fail")
        finally:
            ledger.CHECKPOINT_DIR = old


def test_payload_sequence_mismatch_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_checkpoint(d, 1, "20260816T110000Z", payload_sequence=9)
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            try:
                ledger.validate_checkpoint_chain(datetime(2026, 8, 18, 12, 0, tzinfo=UTC))
            except RuntimeError as exc:
                assert "payload sequence mismatch" in str(exc)
            else:
                raise AssertionError("Payload sequence mismatch must fail")
        finally:
            ledger.CHECKPOINT_DIR = old


def test_future_checkpoint_timestamp_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        _write_checkpoint(d, 1, "20260820T110000Z")
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            try:
                ledger.validate_checkpoint_chain(datetime(2026, 8, 18, 12, 0, tzinfo=UTC))
            except RuntimeError as exc:
                assert "future" in str(exc)
            else:
                raise AssertionError("Future checkpoint must fail")
        finally:
            ledger.CHECKPOINT_DIR = old


def test_nonmonotonic_checkpoint_time_fails_closed():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p1, sha1 = _write_checkpoint(d, 1, "20260817T110000Z")
        _write_checkpoint(d, 2, "20260816T110000Z", p1.name, sha1)
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            try:
                ledger.validate_checkpoint_chain(datetime(2026, 8, 18, 12, 0, tzinfo=UTC))
            except RuntimeError as exc:
                assert "strictly increasing" in str(exc)
            else:
                raise AssertionError("Non-monotonic checkpoint time must fail")
        finally:
            ledger.CHECKPOINT_DIR = old


def test_writer_contains_no_trading_engine_path():
    src = inspect.getsource(ledger)
    assert "run_strategy(" not in src
    assert "CanonicalV2ExecutionEngine" not in src


def test_writer_contains_no_forbidden_outcome_tokens():
    src = inspect.getsource(ledger)
    for token in v312.forbidden_outcome_tokens():
        assert token not in src


def test_checkpoint_hardcodes_blind_governance_flags():
    src = inspect.getsource(ledger.create_checkpoint)
    assert '"outcome_metrics_computed": False' in src
    assert '"trading_engine_called": False' in src
    assert '"strategy_executed": False' in src
    assert '"strategy_design_authorized": False' in src
    assert '"same_sample_h226_research_closed": True' in src
    assert '"future_oos_outcome_evaluator_authorized": False' in src


def test_checkpoint_directory_is_separate_from_v312_current_state():
    assert "v3_13/checkpoints" in str(ledger.CHECKPOINT_DIR).replace("\\", "/")
    assert ledger.CHECKPOINT_DIR != v312.OOS_CSV.parent


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.13 tests passed")
