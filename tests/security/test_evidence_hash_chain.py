from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from scripts.verify_gateway import verify_bundle
from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.evidence import (
    ATTESTATION_FILE,
    CHAIN_FILE,
    CHECKSUM_FILE,
    COMPATIBILITY_EVIDENCE_FILES,
    EvidenceLedger,
)
from universal_project_gateway.evidence_chain import canonical_json
from universal_project_gateway.service import GatewayService

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _finalized_ledger(tmp_path: Path, job_id: str = "job-chain") -> tuple[EvidenceLedger, Path]:
    ledger = EvidenceLedger(tmp_path / "evidence")
    ledger.initialize(
        job_id,
        task={"job_id": job_id, "project_id": "chain-demo", "status": "completed"},
        source_snapshot={"source_revision": "abc123"},
        validation={
            "passed": True,
            "mandatory": ["test"],
            "counts": {"passed": 1, "failed": 0, "skipped": 0, "not_run": 0},
        },
        environment={
            "sandbox": {
                "backend_id": "unsafe-local-subprocess",
                "safety_level": "unsafe-local",
            }
        },
    )
    ledger.append_event(
        job_id,
        "chain-demo",
        "job_prepared",
        {"status": "prepared"},
        actor="control_plane",
    )
    ledger.append_event(
        job_id,
        "chain-demo",
        "validation_completed",
        {"passed": True, "counts": {"passed": 1}},
        actor="local_runner",
    )
    ledger.finalize(
        job_id,
        final_report={
            "job_id": job_id,
            "project_id": "chain-demo",
            "status": "completed",
            "success": True,
        },
    )
    return ledger, ledger.job_path(job_id)


def _events(evidence_path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (evidence_path / CHAIN_FILE).read_text(encoding="utf-8").splitlines()
    ]


def _refresh_chain_checksum(evidence_path: Path) -> None:
    manifest_path = evidence_path / CHECKSUM_FILE
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["files"][CHAIN_FILE] = hashlib.sha256(
        (evidence_path / CHAIN_FILE).read_bytes()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def test_evidence_chain_and_attestation_are_created_and_verify(tmp_path: Path) -> None:
    ledger, evidence_path = _finalized_ledger(tmp_path)

    events = _events(evidence_path)
    attestation = json.loads((evidence_path / ATTESTATION_FILE).read_text(encoding="utf-8"))
    verification = ledger.verify(evidence_path)
    independent = verify_bundle(evidence_path)

    assert verification.valid is True
    assert verification.chain_checked is True
    assert verification.checked_events == 3
    assert independent["ok"] is True
    assert independent["chain_checked"] is True
    assert independent["events_checked"] == 3
    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert events[-1]["event_type"] == "evidence_finalized"
    assert attestation["final_event_hash"] == events[-1]["event_hash"]
    assert attestation["source_commit"] == "abc123"
    assert attestation["sandbox_backend"] == {
        "backend_id": "unsafe-local-subprocess",
        "safety_level": "unsafe-local",
    }
    assert attestation["signer"]["signature_algorithm"] == "none"
    assert attestation["signer"]["signature"] is None
    for line, event in zip(
        (evidence_path / CHAIN_FILE).read_text(encoding="utf-8").splitlines(),
        events,
        strict=True,
    ):
        assert line == canonical_json(event)


def test_tampered_event_payload_fails_even_if_bundle_checksum_is_refreshed(
    tmp_path: Path,
) -> None:
    ledger, evidence_path = _finalized_ledger(tmp_path)
    events = _events(evidence_path)
    events[0]["payload"]["status"] = "tampered"
    (evidence_path / CHAIN_FILE).write_text(
        "\n".join(canonical_json(event) for event in events) + "\n",
        encoding="utf-8",
    )
    _refresh_chain_checksum(evidence_path)

    verification = ledger.verify(evidence_path)
    independent = verify_bundle(evidence_path)

    assert verification.valid is False
    assert "EVIDENCE_EVENT_PAYLOAD_HASH_MISMATCH" in {
        error["code"] for error in verification.errors
    }
    assert independent["ok"] is False
    assert "payload_hash_mismatch" in {
        failure["reason"] for failure in independent["failures"]
    }


def test_reordered_events_fail_even_if_bundle_checksum_is_refreshed(tmp_path: Path) -> None:
    ledger, evidence_path = _finalized_ledger(tmp_path)
    lines = (evidence_path / CHAIN_FILE).read_text(encoding="utf-8").splitlines()
    lines[0], lines[1] = lines[1], lines[0]
    (evidence_path / CHAIN_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    _refresh_chain_checksum(evidence_path)

    verification = ledger.verify(evidence_path)

    assert verification.valid is False
    codes = {error["code"] for error in verification.errors}
    assert "EVIDENCE_EVENT_SEQUENCE_INVALID" in codes
    assert "EVIDENCE_EVENT_CHAIN_BROKEN" in codes


def test_missing_event_fails_chain_continuity(tmp_path: Path) -> None:
    ledger, evidence_path = _finalized_ledger(tmp_path)
    lines = (evidence_path / CHAIN_FILE).read_text(encoding="utf-8").splitlines()
    del lines[1]
    (evidence_path / CHAIN_FILE).write_text("\n".join(lines) + "\n", encoding="utf-8")
    _refresh_chain_checksum(evidence_path)

    verification = ledger.verify(evidence_path)

    assert verification.valid is False
    assert {error["code"] for error in verification.errors} & {
        "EVIDENCE_EVENT_SEQUENCE_INVALID",
        "EVIDENCE_EVENT_CHAIN_BROKEN",
        "ATTESTATION_FINAL_HASH_MISMATCH",
    }


def test_legacy_twelve_file_checksum_bundle_remains_valid(tmp_path: Path) -> None:
    ledger, evidence_path = _finalized_ledger(tmp_path, "legacy-job")
    (evidence_path / CHAIN_FILE).unlink()
    (evidence_path / ATTESTATION_FILE).unlink()
    checksums = {
        filename: hashlib.sha256((evidence_path / filename).read_bytes()).hexdigest()
        for filename in COMPATIBILITY_EVIDENCE_FILES
    }
    (evidence_path / CHECKSUM_FILE).write_text(
        json.dumps({"algorithm": "sha256", "files": checksums}, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )

    verification = ledger.verify(evidence_path)
    independent = verify_bundle(evidence_path)

    assert verification.valid is True
    assert verification.chain_checked is False
    assert verification.checked_files == 12
    assert independent["ok"] is True
    assert independent["chain_checked"] is False


def test_runner_chain_covers_required_phases_and_sandbox_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source" / "python_demo"
    shutil.copytree(REPOSITORY_ROOT / "fixtures" / "python_demo", source)
    gateway = GatewayService(GatewayConfig.from_root(tmp_path / "gateway"))
    gateway.register_project(source / "PROJECT_MANIFEST.yaml")
    prepared = gateway.prepare_task(
        "python-demo",
        "Change the greeting and preserve chained evidence",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
    )
    job_id = prepared["job"]["job_id"]
    gateway.replace_workspace_text(
        job_id,
        "src/greeting.py",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )

    validation = gateway.validate(job_id)
    evidence = gateway.get_evidence(job_id)

    assert validation["passed"] is True
    assert evidence["verified"] is True
    evidence_path = Path(evidence["path"])
    events = _events(evidence_path)
    event_types = {str(event["event_type"]) for event in events}
    assert {
        "workspace_prepared",
        "job_prepared",
        "file_operation_applied",
        "validation_started",
        "sandbox_execution_collected",
        "validation_completed",
        "patch_generated",
        "job_completed",
        "evidence_finalized",
    } <= event_types
    attestation = json.loads((evidence_path / ATTESTATION_FILE).read_text(encoding="utf-8"))
    assert attestation["sandbox_backend"]["backend_id"] == "unsafe-local-subprocess"
    assert attestation["validation_summary"]["passed"] is True
    assert str(tmp_path) not in (evidence_path / CHAIN_FILE).read_text(encoding="utf-8")
