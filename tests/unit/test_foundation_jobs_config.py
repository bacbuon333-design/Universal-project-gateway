from __future__ import annotations

from pathlib import Path

import pytest

from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.jobs import (
    InvalidJobTransitionError,
    InvalidJobUpdateError,
    JobStore,
)
from universal_project_gateway.models import JobStatus, NormalizedIntent, PublicationMode, RiskLevel


def _intent() -> NormalizedIntent:
    return NormalizedIntent(
        project_id="python-demo",
        task_type="modification",
        target_scope=("src/greeting.py",),
        expected_operations=("read_files", "write_files"),
        risk_level=RiskLevel.R1,
        required_validation=("test",),
        publication_mode=PublicationMode.NONE,
    )


def _prepare_job(store: JobStore, job_id: str, *, worker_id: str = "test-worker") -> None:
    claimed = store.claim(job_id, worker_id)
    preparing = store.transition(
        job_id,
        JobStatus.PREPARING,
        worker_id=worker_id,
        lease_token=claimed.lease_token,
    )
    store.transition(
        job_id,
        JobStatus.PREPARED,
        worker_id=worker_id,
        lease_token=preparing.lease_token,
    )


def test_foundation_config_is_side_effect_free_until_explicitly_initialized(
    tmp_path: Path,
) -> None:
    root = tmp_path / "gateway"
    config = GatewayConfig.from_root(root)

    assert not root.exists()
    assert config.database_path == root.resolve() / "var" / "gateway.db"
    assert config.workspaces_root == root.resolve() / "workspaces" / "jobs"

    config.ensure_runtime_dirs()
    assert config.registry_path.parent.is_dir()
    assert config.database_path.parent.is_dir()
    assert config.workspaces_root.is_dir()
    assert config.artifacts_root.is_dir()


def test_foundation_job_store_persists_job_updates_and_events(tmp_path: Path) -> None:
    database = tmp_path / "gateway.db"
    store = JobStore(database)
    job = store.create(
        "python-demo",
        "Change the greeting",
        _intent(),
        job_id="job_001",
    )

    assert job.status is JobStatus.QUEUED
    assert job.normalized_intent["risk_level"] == "R1"
    workspace = tmp_path / "workspace"
    store.update(job.job_id, workspace_path=workspace, source_revision="abc123")
    store.record_event(job.job_id, "workspace_created", {"path": str(workspace)})
    _prepare_job(store, job.job_id)
    claimed = store.claim(job.job_id, "validation-worker", expected_statuses=(JobStatus.PREPARED,))
    validating = store.transition(
        job.job_id,
        JobStatus.VALIDATING,
        worker_id="validation-worker",
        lease_token=claimed.lease_token,
    )
    completed = store.transition(
        job.job_id,
        JobStatus.COMPLETED,
        worker_id="validation-worker",
        lease_token=validating.lease_token,
        validation_summary={"passed": True},
        evidence_path=tmp_path / "evidence",
    )

    reloaded = JobStore(database).get(job.job_id)
    events = JobStore(database).list_events(job.job_id)
    assert reloaded == completed
    assert reloaded.workspace_path == workspace.resolve()
    assert reloaded.validation_summary == {"passed": True}
    assert [event.event_type for event in events] == [
        "job_created",
        "job_updated",
        "workspace_created",
        "job_claimed",
        "status_transition",
        "status_transition",
        "job_claimed",
        "status_transition",
        "status_transition",
    ]


def test_foundation_job_store_rejects_invalid_and_terminal_transitions(
    tmp_path: Path,
) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.create("python-demo", "Inspect", _intent())

    with pytest.raises(InvalidJobTransitionError) as direct:
        store.transition(job.job_id, JobStatus.COMPLETED)
    assert direct.value.code == "INVALID_JOB_TRANSITION"

    store.transition(job.job_id, JobStatus.CANCELLED)
    with pytest.raises(InvalidJobTransitionError):
        store.transition(job.job_id, JobStatus.RUNNING)
    assert store.get(job.job_id).status is JobStatus.CANCELLED

    approval_job = store.create("python-demo", "Request deletion", _intent())
    _prepare_job(store, approval_job.job_id)
    waiting = store.transition(approval_job.job_id, JobStatus.WAITING_FOR_APPROVAL)
    assert waiting.status is JobStatus.WAITING_FOR_APPROVAL


def test_foundation_job_store_validates_metadata_updates(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = store.create("python-demo", "Inspect", _intent())

    with pytest.raises(InvalidJobUpdateError):
        store.update(job.job_id, status="completed")

    updated = store.update(job.job_id, error_code="EXAMPLE", error_message="evidence")
    assert updated.error_code == "EXAMPLE"
    assert store.list(project_id="python-demo", status="queued") == [updated]
