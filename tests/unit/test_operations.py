from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from universal_project_gateway import operations
from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.jobs import JobStore
from universal_project_gateway.operations import OperationsError, cleanup, doctor, status

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _runtime_config(tmp_path: Path) -> GatewayConfig:
    return replace(
        GatewayConfig.from_root(REPOSITORY_ROOT),
        registry_path=REPOSITORY_ROOT / "registry" / "projects.yaml",
        database_path=tmp_path / "var" / "gateway.db",
        workspaces_root=tmp_path / "workspaces" / "jobs",
        artifacts_root=tmp_path / "artifacts" / "jobs",
        intelligence_root=tmp_path / "var" / "project_intelligence",
    )


def _create_job(store: JobStore, job_id: str, status_name: str) -> None:
    store.create(
        "universal-project-gateway",
        f"Operator test for {job_id}",
        {"risk_level": "R0", "target_scope": []},
        status=status_name,
        job_id=job_id,
    )


def test_doctor_reports_pass_warn_and_fail_without_initializing_runtime(tmp_path: Path) -> None:
    config = GatewayConfig.from_root(tmp_path)

    result = doctor(config)

    statuses = {item["status"] for item in result["checks"]}
    assert {"PASS", "WARN", "FAIL"}.issubset(statuses)
    assert result["status"] == "FAIL"
    assert not config.database_path.exists()
    assert not config.workspaces_root.exists()
    assert not config.artifacts_root.exists()


def test_doctor_warns_when_head_is_beyond_nearest_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        operations,
        "_git_status",
        lambda _root: {
            "available": True,
            "version": "git version test",
            "branch": "audit/local-v02-readiness",
            "dirty": False,
            "dirty_entry_count": 0,
            "origin": "https://example.invalid/repository",
            "tag": None,
            "nearest_tag": "v0.1.8",
            "checkpoint_status": "ahead",
            "commits_since_nearest_tag": 1,
        },
    )

    result = doctor(GatewayConfig.from_root(tmp_path))
    checkpoint = next(item for item in result["checks"] if item["name"] == "git_checkpoint")

    assert checkpoint["status"] == "WARN"
    assert "1 commit(s) beyond nearest checkpoint v0.1.8" in checkpoint["message"]
    assert checkpoint["details"]["exact"] is False


def test_doctor_passes_when_head_exactly_matches_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        operations,
        "_git_status",
        lambda _root: {
            "available": True,
            "version": "git version test",
            "branch": "main",
            "dirty": False,
            "dirty_entry_count": 0,
            "origin": "https://example.invalid/repository",
            "tag": "v0.2.0-local",
            "nearest_tag": "v0.2.0-local",
            "checkpoint_status": "exact",
            "commits_since_nearest_tag": 0,
        },
    )

    result = doctor(GatewayConfig.from_root(tmp_path))
    checkpoint = next(item for item in result["checks"] if item["name"] == "git_checkpoint")

    assert checkpoint["status"] == "PASS"
    assert checkpoint["message"] == "HEAD exactly matches checkpoint v0.2.0-local"
    assert checkpoint["details"]["exact"] is True


def test_status_summarizes_registry_jobs_adapters_and_intelligence(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    store = JobStore(config.database_path)
    _create_job(store, "completed-job", "completed")
    _create_job(store, "failed-job", "failed")

    result = status(config)

    assert result["registry"]["project_count"] == 1
    assert result["registry"]["projects"][0]["project_id"] == "universal-project-gateway"
    assert result["jobs"]["by_state"] == {"completed": 1, "failed": 1}
    assert result["jobs"]["latest_completed"]["job_id"] == "completed-job"
    assert result["jobs"]["latest_failed"]["job_id"] == "failed-job"
    assert {item["adapter_id"] for item in result["adapters"]["items"]} == {
        "node",
        "python",
    }
    assert result["intelligence"]["freshness_basis"] == "cache_age_only_no_source_rescan"
    assert result["sandbox"]["default_backend_id"] == "unsafe-local-subprocess"
    assert result["evidence"]["schema_version"] == "2.0"


def test_cleanup_dry_run_preserves_terminal_job_directories(tmp_path: Path) -> None:
    config = _runtime_config(tmp_path)
    store = JobStore(config.database_path)
    _create_job(store, "old-completed", "completed")
    workspace = config.workspaces_root / "old-completed"
    artifact = config.artifacts_root / "old-completed"
    workspace.mkdir(parents=True)
    artifact.mkdir(parents=True)
    (workspace / "keep.txt").write_text("workspace", encoding="utf-8")
    (artifact / "keep.txt").write_text("artifact", encoding="utf-8")

    result = cleanup(config, dry_run=True, keep_last=0)

    assert result["dry_run"] is True
    assert result["candidate_count"] == 2
    assert result["deleted_count"] == 0
    assert workspace.is_dir()
    assert artifact.is_dir()


def test_cleanup_refuses_a_root_that_overlaps_registered_source(tmp_path: Path) -> None:
    config = replace(
        _runtime_config(tmp_path),
        workspaces_root=REPOSITORY_ROOT,
    )

    with pytest.raises(OperationsError, match="protected") as raised:
        cleanup(config, dry_run=True, workspaces=True, artifacts=False)

    assert raised.value.code == "CLEANUP_ROOT_PROTECTED"


def test_windows_operator_scripts_exist_and_pull_helper_is_conservative() -> None:
    doctor_script = REPOSITORY_ROOT / "DOCTOR_GATEWAY.bat"
    pull_script = REPOSITORY_ROOT / "PULL_AND_VERIFY.bat"

    assert doctor_script.is_file()
    assert pull_script.is_file()
    content = pull_script.read_text(encoding="utf-8")
    assert "git status --porcelain" in content
    assert "if errorlevel 1 goto status_failed" in content
    assert 'set "CURRENT_BRANCH="' in content
    assert "if not defined CURRENT_BRANCH goto branch_failed" in content
    assert "git pull --ff-only origin main" in content
    assert "call VERIFY_GATEWAY.bat" in content

    verify_content = (REPOSITORY_ROOT / "VERIFY_GATEWAY.bat").read_text(encoding="utf-8")
    assert "sys.version_info >= (3, 11)" in verify_content
