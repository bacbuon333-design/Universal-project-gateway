from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from scripts.create_real_project_fixture import PROJECT_ID, UPDATED_GREETING
from scripts.validate_real_project_integration import run_real_project_integration

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_external_real_project_registration_workspace_evidence_and_publication(
    tmp_path: Path,
) -> None:
    external_project = tmp_path / "external-projects" / "hello-web-app"
    runtime_root = tmp_path / "gateway-controlled-runtime"

    report = run_real_project_integration(
        REPOSITORY_ROOT,
        external_project,
        runtime_root=runtime_root,
    )

    assert report["success"] is True
    assert report["external_project"]["project_id"] == PROJECT_ID
    assert Path(report["external_project"]["project_root"]) == external_project
    assert PROJECT_ID in report["registry"]["project_ids"]

    intelligence = report["intelligence"]
    assert Path(intelligence["cache_path"]).is_relative_to(runtime_root)
    assert intelligence["inside_project"] is False
    assert intelligence["context_compact"] is True

    job = report["job"]
    workspace = Path(job["workspace_path"])
    assert workspace.is_relative_to(runtime_root / "workspaces" / "jobs")
    assert not workspace.is_relative_to(external_project)
    assert job["scoped_inspection_succeeded"] is True
    assert job["source_unchanged_before_publish"] is True

    assert report["patch"] == {
        "changed_paths": ["src/hello_web_app.py", "tests/test_app.py"],
        "contains_only_intended_changes": True,
    }
    assert report["validation"]["passed"] is True
    assert report["validation"]["actions"] == ["lint", "test"]
    assert report["validation"]["sandbox_backend_ids"] == [
        "unsafe-local-subprocess",
        "unsafe-local-subprocess",
    ]

    evidence = report["evidence"]
    assert evidence["verified"] is True
    assert evidence["chain_checked"] is True
    assert evidence["files_checked"] == 14
    assert evidence["events_checked"] > 0
    assert evidence["attestation_final_hash_matches"] is True

    publication = report["publication"]
    assert publication["branch"].startswith(f"agent/{job['job_id']}-")
    assert publication["pushed"] is False
    assert publication["idempotent_replay"] is True
    assert publication["main_commit_unchanged"] is True
    assert publication["commit_count"] == 1
    assert publication["remote_count"] == 0

    assert report["cleanup"]["dry_run"] is True
    assert report["cleanup"]["deleted_count"] == 0
    assert report["cleanup"]["external_project_preserved"] is True
    assert external_project.is_dir()

    assert report["operations"]["doctor_status"] in {"PASS", "WARN"}
    assert PROJECT_ID in report["operations"]["status_project_ids"]
    assert report["operations"]["status_job_counts"]["completed"] == 1
    assert UPDATED_GREETING in (external_project / "src" / "hello_web_app.py").read_text(
        encoding="utf-8"
    )
