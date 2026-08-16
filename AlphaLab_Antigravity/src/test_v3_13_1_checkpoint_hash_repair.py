from __future__ import annotations

from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import tempfile

import create_v3_13_blind_oos_checkpoint as ledger
import audit_v3_13_1_checkpoint_hash_repair as audit

UTC = timezone.utc


def _write(path: Path, obj: dict, crlf: bool = False) -> None:
    text = json.dumps(obj, indent=2, ensure_ascii=False) + "\n"
    if crlf:
        path.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))
    else:
        path.write_bytes(text.encode("utf-8"))


def _checkpoint_obj(sequence: int, created: str, previous_name=None, previous_sha=None, include_scheme=True):
    obj = {
        "sequence": sequence,
        "created_at_utc": created,
        "previous_checkpoint_filename": previous_name,
        "previous_checkpoint_sha256": previous_sha,
    }
    if include_scheme:
        obj["checkpoint_hash_scheme"] = ledger.HASH_SCHEME
    return obj


def test_hash_scheme_is_frozen():
    assert ledger.HASH_SCHEME == "SHA256_UTF8_LF_NORMALIZED_V1"


def test_frozen_genesis_authoritative_hash_is_locked():
    assert ledger.GENESIS_REPO_LF_SHA256 == "b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876"


def test_superseded_local_hash_is_preserved_for_audit_history():
    assert ledger.GENESIS_SUPERSEDED_LOCAL_WORKTREE_SHA256 == "f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b"
    assert ledger.GENESIS_SUPERSEDED_LOCAL_WORKTREE_SHA256 != ledger.GENESIS_REPO_LF_SHA256


def test_real_genesis_recomputes_to_authoritative_canonical_hash():
    out = ledger.verify_frozen_genesis_checkpoint()
    assert out["canonical_sha256"] == ledger.GENESIS_REPO_LF_SHA256
    assert out["filename"] == ledger.GENESIS_FILENAME


def test_crlf_and_lf_have_same_canonical_checkpoint_hash():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        obj = _checkpoint_obj(2, "2026-08-17T00:00:00+00:00", "a.json", "1" * 64)
        lf = d / "lf.json"
        crlf = d / "crlf.json"
        _write(lf, obj, crlf=False)
        _write(crlf, obj, crlf=True)
        assert lf.read_bytes() != crlf.read_bytes()
        assert ledger.checkpoint_sha256(lf) == ledger.checkpoint_sha256(crlf)


def test_bare_cr_is_rejected():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "bad.json"
        p.write_bytes(b'{"x":1}\r')
        try:
            ledger.checkpoint_sha256(p)
        except RuntimeError as exc:
            assert "bare CR" in str(exc)
        else:
            raise AssertionError("Bare CR must fail closed")


def test_binary_writer_emits_lf_only():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "x.json"
        ledger._write_checkpoint_lf(p, {"x": 1, "y": "z"})
        raw = p.read_bytes()
        assert b"\r" not in raw
        assert raw.endswith(b"\n")


def test_two_checkpoint_chain_accepts_canonical_parent_hash_even_if_genesis_worktree_is_crlf():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p1 = d / "000001_20260816T111146Z.json"
        _write(p1, _checkpoint_obj(1, "2026-08-16T11:11:46+00:00", include_scheme=False), crlf=True)
        canonical_parent = ledger.checkpoint_sha256(p1)
        p2 = d / "000002_20260817T111146Z.json"
        _write(p2, _checkpoint_obj(2, "2026-08-17T11:11:46+00:00", p1.name, canonical_parent), crlf=False)
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            out = ledger.validate_checkpoint_chain(datetime(2026, 8, 18, tzinfo=UTC))
            assert out["checkpoint_count"] == 2
            assert out["checkpoint_hash_scheme"] == ledger.HASH_SCHEME
        finally:
            ledger.CHECKPOINT_DIR = old


def test_two_checkpoint_chain_rejects_noncanonical_parent_hash():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p1 = d / "000001_20260816T111146Z.json"
        _write(p1, _checkpoint_obj(1, "2026-08-16T11:11:46+00:00", include_scheme=False), crlf=True)
        wrong_raw_hash = __import__("hashlib").sha256(p1.read_bytes()).hexdigest()
        assert wrong_raw_hash != ledger.checkpoint_sha256(p1)
        p2 = d / "000002_20260817T111146Z.json"
        _write(p2, _checkpoint_obj(2, "2026-08-17T11:11:46+00:00", p1.name, wrong_raw_hash), crlf=False)
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            try:
                ledger.validate_checkpoint_chain(datetime(2026, 8, 18, tzinfo=UTC))
            except RuntimeError as exc:
                assert "parent SHA mismatch" in str(exc)
            else:
                raise AssertionError("Noncanonical parent SHA must fail")
        finally:
            ledger.CHECKPOINT_DIR = old


def test_checkpoint2_requires_embedded_hash_scheme():
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        p1 = d / "000001_20260816T111146Z.json"
        _write(p1, _checkpoint_obj(1, "2026-08-16T11:11:46+00:00", include_scheme=False))
        parent = ledger.checkpoint_sha256(p1)
        p2 = d / "000002_20260817T111146Z.json"
        _write(p2, _checkpoint_obj(2, "2026-08-17T11:11:46+00:00", p1.name, parent, include_scheme=False))
        old = ledger.CHECKPOINT_DIR
        ledger.CHECKPOINT_DIR = d
        try:
            try:
                ledger.validate_checkpoint_chain(datetime(2026, 8, 18, tzinfo=UTC))
            except RuntimeError as exc:
                assert "hash scheme mismatch" in str(exc)
            else:
                raise AssertionError("Checkpoint 2 without scheme must fail")
        finally:
            ledger.CHECKPOINT_DIR = old


def test_new_payload_source_records_hash_scheme():
    src = inspect.getsource(ledger.create_checkpoint)
    assert '"checkpoint_hash_scheme": HASH_SCHEME' in src


def test_writer_no_longer_hashes_checkpoint_with_v312_raw_file_hash():
    src = inspect.getsource(ledger.create_checkpoint)
    assert "checkpoint_sha256(path)" in src
    assert "v312.sha256_file(path)" not in src


def test_repair_audit_does_not_create_checkpoint_or_call_exporter():
    src = inspect.getsource(audit)
    assert "create_checkpoint(" not in src
    assert "run_accrual(" not in src
    assert "copy_rates_range(" not in src


def test_repair_audit_has_no_outcome_or_strategy_execution():
    src = inspect.getsource(audit)
    assert "run_strategy(" not in src
    assert "CanonicalV2ExecutionEngine" not in src
    assert '"outcome_metrics_computed": False' in src
    assert '"strategy_executed": False' in src
    assert '"strategy_design_authorized": False' in src


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"PASS: {t.__name__}")
    print(f"All {len(tests)} V3.13.1 tests passed")
