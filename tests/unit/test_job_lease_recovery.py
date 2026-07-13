from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from universal_project_gateway.jobs import (
    IdempotencyConflictError,
    InvalidJobTransitionError,
    JobAlreadyClaimedError,
    JobCancellationRequestedError,
    JobStore,
)
from universal_project_gateway.models import JobStatus, NormalizedIntent, PublicationMode, RiskLevel


@dataclass
class MutableClock:
    current: datetime

    def __call__(self) -> datetime:
        return self.current

    def advance(self, seconds: int) -> None:
        self.current += timedelta(seconds=seconds)


def _intent() -> NormalizedIntent:
    return NormalizedIntent(
        project_id="python-demo",
        task_type="inspection",
        target_scope=("src/greeting.py",),
        expected_operations=("read_files",),
        risk_level=RiskLevel.R0,
        required_validation=("test",),
        publication_mode=PublicationMode.NONE,
    )


def _store(tmp_path: Path) -> tuple[JobStore, MutableClock]:
    clock = MutableClock(datetime(2026, 7, 14, 0, 0, tzinfo=UTC))
    return JobStore(tmp_path / "gateway.db", clock=clock), clock


def test_job_claim_succeeds_once_and_duplicate_claim_is_rejected(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    job = store.create("python-demo", "Inspect", _intent())

    with pytest.raises(InvalidJobTransitionError) as bypass:
        store.transition(job.job_id, JobStatus.CLAIMED)
    assert bypass.value.code == "CLAIM_OPERATION_REQUIRED"

    claimed = store.claim(job.job_id, "worker-a", lease_seconds=30)

    assert claimed.status is JobStatus.CLAIMED
    assert claimed.worker_id == "worker-a"
    assert claimed.lease_token is not None and len(claimed.lease_token) >= 32
    assert claimed.attempt == 1
    assert "lease_token" not in claimed.to_dict()
    with pytest.raises(JobAlreadyClaimedError) as duplicate:
        store.claim(job.job_id, "worker-b", lease_seconds=30)
    assert duplicate.value.code == "JOB_ALREADY_CLAIMED"


def test_expired_claim_is_safely_requeued_with_a_new_future_token(tmp_path: Path) -> None:
    store, clock = _store(tmp_path)
    job = store.create("python-demo", "Inspect", _intent())
    first = store.claim(job.job_id, "worker-a", lease_seconds=10)
    first_token = first.lease_token
    clock.advance(11)

    recovered = store.recover_expired(job.job_id)
    second = store.claim(job.job_id, "worker-b", lease_seconds=10)

    assert recovered.status is JobStatus.QUEUED
    assert recovered.recovery_reason and "lease expired" in recovered.recovery_reason
    assert recovered.worker_id is None
    assert second.lease_token != first_token
    assert second.attempt == 2
    assert [event.event_type for event in store.list_events(job.job_id)].count(
        "lease_recovered"
    ) == 1


def test_expired_lease_during_effectful_phase_requires_recovery(tmp_path: Path) -> None:
    store, clock = _store(tmp_path)
    job = store.create("python-demo", "Inspect", _intent())
    claimed = store.claim(job.job_id, "worker-a", lease_seconds=10)
    validating = store.transition(
        job.job_id,
        JobStatus.VALIDATING,
        worker_id="worker-a",
        lease_token=claimed.lease_token,
    )
    clock.advance(11)

    recovered = store.recover_expired(job.job_id)

    assert validating.status is JobStatus.VALIDATING
    assert recovered.status is JobStatus.RECOVERY_REQUIRED
    assert recovered.last_error == recovered.recovery_reason
    with pytest.raises(InvalidJobTransitionError):
        store.transition(job.job_id, JobStatus.COMPLETED)


def test_heartbeat_extends_lease_and_staleness_is_detectable(tmp_path: Path) -> None:
    store, clock = _store(tmp_path)
    job = store.create("python-demo", "Inspect", _intent())
    claimed = store.claim(job.job_id, "worker-a", lease_seconds=10)
    original_expiry = claimed.lease_expires_at
    clock.advance(5)

    refreshed = store.heartbeat(
        job.job_id,
        "worker-a",
        claimed.lease_token or "",
        lease_seconds=20,
    )

    assert refreshed.heartbeat_at != claimed.heartbeat_at
    assert refreshed.lease_expires_at != original_expiry
    clock.advance(19)
    assert store.is_lease_stale(job.job_id) is False
    clock.advance(2)
    assert store.is_lease_stale(job.job_id) is True
    assert store.list_stale_leases() == [store.get(job.job_id)]
    assert store.list_events(job.job_id)[-1].event_type == "job_heartbeat"


def test_cancellation_request_is_persisted_and_blocks_forward_progress(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)
    job = store.create("python-demo", "Inspect", _intent())
    claimed = store.claim(job.job_id, "worker-a", lease_seconds=30)

    requested = store.request_cancellation(job.job_id, reason="operator request")

    assert requested.status is JobStatus.CLAIMED
    assert requested.cancel_requested is True
    with pytest.raises(JobCancellationRequestedError):
        store.transition(
            job.job_id,
            JobStatus.PREPARING,
            worker_id="worker-a",
            lease_token=claimed.lease_token,
        )
    cancelled = store.transition(
        job.job_id,
        JobStatus.CANCELLED,
        worker_id="worker-a",
        lease_token=claimed.lease_token,
    )
    assert cancelled.status is JobStatus.CANCELLED
    with pytest.raises(InvalidJobTransitionError):
        store.transition(job.job_id, JobStatus.QUEUED)
    assert "cancellation_requested" in {event.event_type for event in store.list_events(job.job_id)}


def test_prepare_and_operation_idempotency_prevent_duplicate_effects(tmp_path: Path) -> None:
    store, _ = _store(tmp_path)

    first, created = store.create_or_get(
        "python-demo",
        "Inspect",
        _intent(),
        idempotency_key="prepare-001",
    )
    replay, replay_created = store.create_or_get(
        "python-demo",
        "Inspect",
        _intent(),
        idempotency_key="prepare-001",
    )

    assert created is True
    assert replay_created is False
    assert replay.job_id == first.job_id
    assert len(store.list(project_id="python-demo")) == 1
    with pytest.raises(IdempotencyConflictError):
        store.create_or_get(
            "python-demo",
            "Different request",
            _intent(),
            idempotency_key="prepare-001",
        )

    started = store.begin_idempotent_operation(first.job_id, "validate", "validate-001")
    duplicate = store.begin_idempotent_operation(first.job_id, "validate", "validate-001")
    completed = store.complete_idempotent_operation(
        first.job_id,
        "validate",
        "validate-001",
        {"passed": True},
    )
    completed_replay = store.begin_idempotent_operation(
        first.job_id,
        "validate",
        "validate-001",
    )

    assert started["replay"] is False
    assert duplicate["replay"] is True and duplicate["state"] == "started"
    assert completed["result"] == {"passed": True}
    assert completed_replay["replay"] is True
    assert completed_replay["result"] == {"passed": True}


def test_v1_job_database_is_migrated_without_losing_existing_jobs(tmp_path: Path) -> None:
    database = tmp_path / "legacy.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                user_request TEXT NOT NULL,
                normalized_intent_json TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                source_revision TEXT,
                workspace_path TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                validation_summary_json TEXT,
                evidence_path TEXT,
                error_code TEXT,
                error_message TEXT
            );
            CREATE TABLE job_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                details_json TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT
            );
            INSERT INTO jobs (
                job_id, project_id, user_request, normalized_intent_json, risk_level,
                status, created_at, updated_at
            ) VALUES (
                'legacy-job', 'python-demo', 'Inspect', '{"risk_level":"R0"}', 'R0',
                'prepared', '2026-07-14T00:00:00.000Z', '2026-07-14T00:00:00.000Z'
            );
            INSERT INTO job_events (
                job_id, event_type, created_at, details_json, to_status
            ) VALUES (
                'legacy-job', 'job_created', '2026-07-14T00:00:00.000Z', '{}', 'prepared'
            );
            PRAGMA user_version = 1;
            """
        )

    store = JobStore(database)
    migrated = store.get("legacy-job")

    assert migrated.status is JobStatus.PREPARED
    assert migrated.attempt == 0
    assert migrated.worker_id is None
    assert store.list_events("legacy-job")[0].event_type == "job_created"
