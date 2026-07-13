from __future__ import annotations

import json
from pathlib import Path

from universal_project_gateway.evidence import EvidenceLedger


def test_secrets_are_redacted_before_json_logs_and_checksums_are_persisted(
    tmp_path: Path,
) -> None:
    ledger = EvidenceLedger(tmp_path / "evidence")
    job_id = "job-redaction"
    ledger.initialize(job_id)
    secrets = {
        "password": "correct-horse-battery-staple",
        "api_key": "sk-ABCDEFGHIJKLMNOPQRSTUVWX",
        "authorization": "Bearer abcdefghijklmnopqrstuvwxyz",
        "nested": {"token": "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456"},
        "url": "https://alice:hunter2@example.invalid/private",
        "aws": "AKIAABCDEFGHIJKLMNOP",
    }
    ledger.write(job_id, "task.json", secrets)
    ledger.write(
        job_id,
        "stdout.log",
        "password=correct-horse-battery-staple\n"
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz\n"
        "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456\n"
        "url=https://alice:hunter2@example.invalid/private\n"
        "key=AKIAABCDEFGHIJKLMNOP\n",
    )
    ledger.finalize(job_id, final_report={"success": False, "status": "failed"})

    evidence_path = ledger.job_path(job_id)
    verification = ledger.verify(job_id)
    assert verification.valid is True
    combined = "\n".join(
        path.read_text(encoding="utf-8") for path in evidence_path.iterdir() if path.is_file()
    )
    for raw_secret in (
        "correct-horse-battery-staple",
        "sk-ABCDEFGHIJKLMNOPQRSTUVWX",
        "abcdefghijklmnopqrstuvwxyz",
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
        "alice",
        "hunter2",
        "AKIAABCDEFGHIJKLMNOP",
    ):
        assert raw_secret not in combined
    assert "[REDACTED]" in combined
    task = json.loads((evidence_path / "task.json").read_text(encoding="utf-8"))
    assert task["password"] == "[REDACTED]"
    assert task["api_key"] == "[REDACTED]"
    assert task["nested"]["token"] == "[REDACTED]"


def test_checksum_verification_detects_evidence_tampering(tmp_path: Path) -> None:
    ledger = EvidenceLedger(tmp_path / "evidence")
    job_id = "job-tamper"
    ledger.initialize(job_id, task={"request": "safe"})
    ledger.finalize(job_id)
    assert ledger.verify(job_id).valid is True

    (ledger.job_path(job_id) / "task.json").write_text(
        '{"request": "changed after finalization"}\n', encoding="utf-8"
    )

    verification = ledger.verify(job_id)
    assert verification.valid is False
    assert {error["code"] for error in verification.errors} == {"CHECKSUM_MISMATCH"}
