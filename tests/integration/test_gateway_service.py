from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from universal_project_gateway.evidence import EVIDENCE_FILES
from universal_project_gateway.service import GatewayService


def _prepare_python_job(gateway: GatewayService) -> str:
    prepared = gateway.prepare_task(
        "python-demo",
        "Change the greeting and run the tests",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
    )
    assert prepared["job"]["status"] == "prepared"
    assert prepared["intent"]["risk_level"] == "R2"
    assert prepared["intent"]["required_validation"] == ["test"]
    workspace = Path(prepared["workspace"])
    assert workspace.is_dir()
    assert workspace.name == "workspace"
    return prepared["job"]["job_id"]


def test_python_service_vertical_slice_isolated_diff_validation_and_evidence(
    gateway_factory: Callable[[str], tuple[GatewayService, Path]],
) -> None:
    gateway, source = gateway_factory("python_demo")
    source_target = source / "src" / "greeting.py"
    source_before = source_target.read_bytes()
    job_id = _prepare_python_job(gateway)

    inspected = gateway.read_workspace_file(job_id, "src/greeting.py")
    assert 'return "Hello"' in inspected["content"]

    edited = gateway.replace_workspace_text(
        job_id,
        "src/greeting.py",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )
    assert edited["path"] == "src/greeting.py"
    assert edited["replacements"] == 1
    assert source_target.read_bytes() == source_before

    diff = gateway.get_diff(job_id)
    assert diff["stale_source_warning"] is False
    assert [(item["path"], item["change_type"]) for item in diff["files_changed"]] == [
        ("src/greeting.py", "modified")
    ]
    assert 'return "Hello from UPG"' in diff["patch"]
    assert "diff --git a/src/greeting.py b/src/greeting.py" in diff["patch"]

    validation = gateway.validate(job_id)
    assert validation["passed"] is True
    assert validation["evidence_verified"] is True
    assert validation["counts"] == {
        "passed": 1,
        "failed": 0,
        "skipped": 0,
        "not_run": 0,
    }
    check = validation["checks"][0]
    assert check["action"] == "test"
    assert check["status"] == "passed"
    assert check["returncode"] == 0
    assert check["argv"][1:3] == ["-m", "unittest"]
    assert Path(check["cwd"]) == gateway.config.workspaces_root / job_id / "workspace"

    evidence = gateway.get_evidence(job_id)
    evidence_path = Path(evidence["path"])
    assert evidence["verified"] is True
    assert {path.name for path in evidence_path.iterdir()} == {
        *EVIDENCE_FILES,
        "manifest.sha256.json",
    }
    checksum_manifest = json.loads(
        (evidence_path / "manifest.sha256.json").read_text(encoding="utf-8")
    )
    assert set(checksum_manifest["files"]) == set(EVIDENCE_FILES)
    assert (evidence_path / "patch.diff").read_text(encoding="utf-8") == diff["patch"]
    operations = json.loads((evidence_path / "operations.json").read_text(encoding="utf-8"))
    event_types = {event["event_type"] for event in operations}
    assert {
        "job_created",
        "status_transition",
        "workspace_file_read",
        "workspace_text_replaced",
        "workspace_diff_computed",
    } <= event_types
    final_report = json.loads((evidence_path / "final_report.json").read_text(encoding="utf-8"))
    assert final_report["success"] is True
    assert final_report["status"] == "completed"
    assert source_target.read_bytes() == source_before


def test_mandatory_validation_failure_is_terminal_and_still_checksummed(
    gateway_factory: Callable[[str], tuple[GatewayService, Path]],
) -> None:
    gateway, _ = gateway_factory("python_demo")
    job_id = _prepare_python_job(gateway)

    validation = gateway.validate(job_id)

    assert validation["passed"] is False
    assert validation["evidence_verified"] is True
    assert validation["counts"]["failed"] == 1
    inspected = gateway.inspect_job(job_id)
    assert inspected["job"]["status"] == "failed"
    assert inspected["job"]["error_code"] == "VALIDATION_FAILED"
    assert gateway.get_evidence(job_id)["verified"] is True
