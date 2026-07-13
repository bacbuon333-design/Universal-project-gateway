"""Durable SQLite jobs, leases, recovery, cancellation, and effect replay."""

from __future__ import annotations

import json
import re
import secrets
import sqlite3
import uuid
from collections.abc import Callable, Iterable, Mapping
from contextlib import closing
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .models import (
    GatewayError,
    Job,
    JobEvent,
    JobStatus,
    NormalizedIntent,
    RiskLevel,
    json_ready,
)

# ``prepared`` remains for backward compatibility with existing persisted jobs
# and the synchronous public API. Worker-owned phases use the other states.
VALID_TRANSITIONS: Mapping[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.CLAIMED, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.CLAIMED: frozenset(
        {
            JobStatus.PREPARING,
            JobStatus.RUNNING,
            JobStatus.VALIDATING,
            JobStatus.PUBLISHING,
            JobStatus.QUEUED,
            JobStatus.PREPARED,
            JobStatus.WAITING_FOR_APPROVAL,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.RECOVERY_REQUIRED,
        }
    ),
    JobStatus.PREPARING: frozenset(
        {
            JobStatus.PREPARED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.RECOVERY_REQUIRED,
        }
    ),
    JobStatus.PREPARED: frozenset(
        {
            JobStatus.CLAIMED,
            JobStatus.WAITING_FOR_APPROVAL,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }
    ),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.VALIDATING,
            JobStatus.WAITING_FOR_APPROVAL,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.RECOVERY_REQUIRED,
        }
    ),
    JobStatus.VALIDATING: frozenset(
        {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.RECOVERY_REQUIRED,
        }
    ),
    JobStatus.WAITING_FOR_APPROVAL: frozenset(
        {JobStatus.CLAIMED, JobStatus.FAILED, JobStatus.CANCELLED}
    ),
    JobStatus.PUBLISHING: frozenset(
        {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.RECOVERY_REQUIRED,
        }
    ),
    JobStatus.COMPLETED: frozenset({JobStatus.CLAIMED}),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
    JobStatus.RECOVERY_REQUIRED: frozenset(
        {JobStatus.QUEUED, JobStatus.FAILED, JobStatus.CANCELLED}
    ),
}

LEASE_GUARDED_STATUSES = frozenset(
    {
        JobStatus.CLAIMED,
        JobStatus.PREPARING,
        JobStatus.RUNNING,
        JobStatus.VALIDATING,
        JobStatus.PUBLISHING,
    }
)

_SAFE_CLAIM_ORIGINS = frozenset(
    {
        JobStatus.QUEUED,
        JobStatus.PREPARED,
        JobStatus.WAITING_FOR_APPROVAL,
        JobStatus.COMPLETED,
    }
)
_IMMEDIATE_CANCEL_STATUSES = frozenset(
    {
        JobStatus.QUEUED,
        JobStatus.PREPARED,
        JobStatus.WAITING_FOR_APPROVAL,
        JobStatus.RECOVERY_REQUIRED,
    }
)
_TERMINAL_STATUSES = frozenset({JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED})
_JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")
_WORKER_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,199}$")
_IDEMPOTENCY_KEY_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
_OPERATION_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class JobStoreError(GatewayError):
    default_code = "JOB_STORE_ERROR"


class JobNotFoundError(JobStoreError):
    default_code = "JOB_NOT_FOUND"


class InvalidJobTransitionError(JobStoreError):
    default_code = "INVALID_JOB_TRANSITION"


class InvalidJobUpdateError(JobStoreError):
    default_code = "INVALID_JOB_UPDATE"


class JobLeaseError(JobStoreError):
    default_code = "JOB_LEASE_ERROR"


class JobAlreadyClaimedError(JobLeaseError):
    default_code = "JOB_ALREADY_CLAIMED"


class JobLeaseExpiredError(JobLeaseError):
    default_code = "JOB_LEASE_EXPIRED"


class JobCancellationRequestedError(JobStoreError):
    default_code = "JOB_CANCELLATION_REQUESTED"


class IdempotencyConflictError(JobStoreError):
    default_code = "IDEMPOTENCY_CONFLICT"


class IdempotentOperationError(JobStoreError):
    default_code = "IDEMPOTENT_OPERATION_ERROR"


def _json_dumps(value: Any) -> str:
    return json.dumps(
        json_ready(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _coerce_status(value: JobStatus | str) -> JobStatus:
    try:
        return value if isinstance(value, JobStatus) else JobStatus(value)
    except ValueError as exc:
        raise JobStoreError(
            f"unknown job status {value!r}",
            code="INVALID_JOB_STATUS",
        ) from exc


def _coerce_risk(value: RiskLevel | str) -> RiskLevel:
    try:
        return value if isinstance(value, RiskLevel) else RiskLevel(value)
    except ValueError as exc:
        raise JobStoreError(
            f"unknown risk level {value!r}",
            code="INVALID_RISK_LEVEL",
        ) from exc


def _coerce_datetime(value: datetime | str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise JobStoreError("timestamp is invalid", code="INVALID_TIMESTAMP") from exc
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _validate_worker_id(worker_id: str) -> str:
    if not isinstance(worker_id, str) or not _WORKER_ID_PATTERN.fullmatch(worker_id):
        raise JobLeaseError(
            "worker_id must be a bounded stable identifier",
            code="INVALID_WORKER_ID",
        )
    return worker_id


def _validate_idempotency_key(value: str | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not _IDEMPOTENCY_KEY_PATTERN.fullmatch(value):
        raise IdempotencyConflictError(
            "idempotency_key must use 1-200 letters, digits, dots, colons, underscores, or hyphens",
            code="INVALID_IDEMPOTENCY_KEY",
        )
    return value


class JobStore:
    """Durable local job store with atomic lease and effect ownership."""

    def __init__(
        self,
        database_path: str | Path,
        *,
        timeout_seconds: float = 5.0,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.database_path = Path(database_path).expanduser().resolve()
        self.timeout_seconds = timeout_seconds
        self._clock = clock or (lambda: datetime.now(UTC))
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _now(self, value: datetime | str | None = None) -> datetime:
        return _coerce_datetime(value) if value is not None else _coerce_datetime(self._clock())

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=self.timeout_seconds,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(f"PRAGMA busy_timeout = {int(self.timeout_seconds * 1000)}")
        return connection

    @staticmethod
    def _schema_sql() -> str:
        return """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                user_request TEXT NOT NULL,
                normalized_intent_json TEXT NOT NULL,
                risk_level TEXT NOT NULL CHECK (risk_level IN ('R0','R1','R2','R3','R4')),
                source_revision TEXT,
                workspace_path TEXT,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'queued','claimed','preparing','prepared','running','validating',
                        'waiting_for_approval','publishing','completed','failed','cancelled',
                        'recovery_required'
                    )
                ),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                validation_summary_json TEXT,
                evidence_path TEXT,
                error_code TEXT,
                error_message TEXT,
                worker_id TEXT,
                lease_token TEXT,
                lease_expires_at TEXT,
                heartbeat_at TEXT,
                attempt INTEGER NOT NULL DEFAULT 0 CHECK (attempt >= 0),
                idempotency_key TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0,1)),
                recovery_reason TEXT,
                last_error TEXT,
                lease_origin_status TEXT
            );

            CREATE TABLE IF NOT EXISTS job_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                details_json TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS job_operations (
                job_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                state TEXT NOT NULL CHECK (state IN ('started','completed','failed')),
                result_json TEXT,
                error_code TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (job_id, operation, idempotency_key),
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_project_status
                ON jobs(project_id, status);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_project_idempotency
                ON jobs(project_id, idempotency_key)
                WHERE idempotency_key IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_jobs_lease_expiry
                ON jobs(lease_expires_at)
                WHERE lease_token IS NOT NULL;
            CREATE INDEX IF NOT EXISTS idx_job_events_job_id
                ON job_events(job_id, event_id);
            CREATE INDEX IF NOT EXISTS idx_job_operations_state
                ON job_operations(job_id, operation, state);
            PRAGMA user_version = 2;
        """

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            columns = {
                str(row["name"]) for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
            }
            if not columns:
                connection.executescript(self._schema_sql())
                return
            if "worker_id" not in columns:
                self._migrate_v1_to_v2(connection)
                return
            connection.executescript(self._schema_sql())

    def _migrate_v1_to_v2(self, connection: sqlite3.Connection) -> None:
        """Rebuild the v1 table so its status CHECK accepts worker phases."""

        connection.execute("PRAGMA foreign_keys = OFF")
        connection.executescript(
            """
            BEGIN IMMEDIATE;
            ALTER TABLE job_events RENAME TO job_events_v1;
            ALTER TABLE jobs RENAME TO jobs_v1;

            CREATE TABLE jobs (
                job_id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                user_request TEXT NOT NULL,
                normalized_intent_json TEXT NOT NULL,
                risk_level TEXT NOT NULL CHECK (risk_level IN ('R0','R1','R2','R3','R4')),
                source_revision TEXT,
                workspace_path TEXT,
                status TEXT NOT NULL CHECK (
                    status IN (
                        'queued','claimed','preparing','prepared','running','validating',
                        'waiting_for_approval','publishing','completed','failed','cancelled',
                        'recovery_required'
                    )
                ),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                validation_summary_json TEXT,
                evidence_path TEXT,
                error_code TEXT,
                error_message TEXT,
                worker_id TEXT,
                lease_token TEXT,
                lease_expires_at TEXT,
                heartbeat_at TEXT,
                attempt INTEGER NOT NULL DEFAULT 0 CHECK (attempt >= 0),
                idempotency_key TEXT,
                cancel_requested INTEGER NOT NULL DEFAULT 0 CHECK (cancel_requested IN (0,1)),
                recovery_reason TEXT,
                last_error TEXT,
                lease_origin_status TEXT
            );

            INSERT INTO jobs (
                job_id, project_id, user_request, normalized_intent_json, risk_level,
                source_revision, workspace_path, status, created_at, updated_at,
                validation_summary_json, evidence_path, error_code, error_message
            )
            SELECT
                job_id, project_id, user_request, normalized_intent_json, risk_level,
                source_revision, workspace_path, status, created_at, updated_at,
                validation_summary_json, evidence_path, error_code, error_message
            FROM jobs_v1;

            CREATE TABLE job_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                details_json TEXT NOT NULL,
                from_status TEXT,
                to_status TEXT,
                FOREIGN KEY (job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
            );

            INSERT INTO job_events (
                event_id, job_id, event_type, created_at, details_json, from_status, to_status
            )
            SELECT
                event_id, job_id, event_type, created_at, details_json, from_status, to_status
            FROM job_events_v1;

            DROP TABLE job_events_v1;
            DROP TABLE jobs_v1;
            COMMIT;
            """
        )
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(self._schema_sql())

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> Job:
        try:
            intent = json.loads(row["normalized_intent_json"])
            validation = (
                json.loads(row["validation_summary_json"])
                if row["validation_summary_json"] is not None
                else None
            )
            if not isinstance(intent, dict) or (
                validation is not None and not isinstance(validation, dict)
            ):
                raise TypeError("job JSON columns must contain objects")
            origin = row["lease_origin_status"]
            return Job(
                job_id=row["job_id"],
                project_id=row["project_id"],
                user_request=row["user_request"],
                normalized_intent=intent,
                risk_level=RiskLevel(row["risk_level"]),
                source_revision=row["source_revision"],
                workspace_path=Path(row["workspace_path"]) if row["workspace_path"] else None,
                status=JobStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                validation_summary=validation,
                evidence_path=Path(row["evidence_path"]) if row["evidence_path"] else None,
                error_code=row["error_code"],
                error_message=row["error_message"],
                worker_id=row["worker_id"],
                lease_token=row["lease_token"],
                lease_expires_at=row["lease_expires_at"],
                heartbeat_at=row["heartbeat_at"],
                attempt=int(row["attempt"]),
                idempotency_key=row["idempotency_key"],
                cancel_requested=bool(row["cancel_requested"]),
                recovery_reason=row["recovery_reason"],
                last_error=row["last_error"],
                lease_origin_status=JobStatus(origin) if origin else None,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise JobStoreError(
                "stored job record is invalid",
                code="JOB_RECORD_CORRUPT",
            ) from exc

    @staticmethod
    def _event_from_row(row: sqlite3.Row) -> JobEvent:
        try:
            return JobEvent(
                event_id=row["event_id"],
                job_id=row["job_id"],
                event_type=row["event_type"],
                created_at=row["created_at"],
                details=json.loads(row["details_json"]),
                from_status=JobStatus(row["from_status"]) if row["from_status"] else None,
                to_status=JobStatus(row["to_status"]) if row["to_status"] else None,
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise JobStoreError(
                "stored job event is invalid",
                code="JOB_EVENT_CORRUPT",
            ) from exc

    @staticmethod
    def _require_job(connection: sqlite3.Connection, job_id: str) -> sqlite3.Row:
        row = connection.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            raise JobNotFoundError(
                f"job {job_id!r} does not exist",
                details={"job_id": job_id},
            )
        return row

    @staticmethod
    def _insert_event(
        connection: sqlite3.Connection,
        job_id: str,
        event_type: str,
        timestamp: str,
        details: Mapping[str, Any] | None = None,
        *,
        from_status: JobStatus | str | None = None,
        to_status: JobStatus | str | None = None,
    ) -> int:
        from_value = _coerce_status(from_status).value if from_status is not None else None
        to_value = _coerce_status(to_status).value if to_status is not None else None
        cursor = connection.execute(
            """
            INSERT INTO job_events (
                job_id, event_type, created_at, details_json, from_status, to_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                event_type,
                timestamp,
                _json_dumps(details or {}),
                from_value,
                to_value,
            ),
        )
        return int(cursor.lastrowid)

    @staticmethod
    def _validate_create_input(
        project_id: str,
        user_request: str,
        normalized_intent: NormalizedIntent | Mapping[str, Any],
        risk_level: RiskLevel | str | None,
    ) -> tuple[str, str, dict[str, Any], RiskLevel]:
        if not isinstance(project_id, str) or not project_id.strip():
            raise JobStoreError("project_id must be a non-empty string", code="INVALID_PROJECT_ID")
        if not isinstance(user_request, str) or not user_request.strip():
            raise JobStoreError(
                "user_request must be a non-empty string", code="INVALID_USER_REQUEST"
            )
        if isinstance(normalized_intent, NormalizedIntent):
            intent_dict = normalized_intent.to_dict()
            inferred_risk = normalized_intent.risk_level
        elif isinstance(normalized_intent, Mapping):
            intent_dict = dict(normalized_intent)
            inferred_risk = _coerce_risk(intent_dict.get("risk_level", "R0"))
        else:
            raise JobStoreError(
                "normalized_intent must be a mapping or NormalizedIntent", code="INVALID_INTENT"
            )
        selected_risk = _coerce_risk(risk_level) if risk_level is not None else inferred_risk
        return project_id.strip(), user_request.strip(), intent_dict, selected_risk

    def create_or_get(
        self,
        project_id: str,
        user_request: str,
        normalized_intent: NormalizedIntent | Mapping[str, Any],
        risk_level: RiskLevel | str | None = None,
        *,
        job_id: str | None = None,
        source_revision: str | None = None,
        workspace_path: str | Path | None = None,
        status: JobStatus | str = JobStatus.QUEUED,
        idempotency_key: str | None = None,
    ) -> tuple[Job, bool]:
        project, request, intent_dict, selected_risk = self._validate_create_input(
            project_id, user_request, normalized_intent, risk_level
        )
        selected_status = _coerce_status(status)
        selected_key = _validate_idempotency_key(idempotency_key)
        selected_id = job_id or uuid.uuid4().hex
        if not isinstance(selected_id, str) or not _JOB_ID_PATTERN.fullmatch(selected_id):
            raise JobStoreError(
                "job_id must be filesystem-safe and at most 80 characters",
                code="INVALID_JOB_ID",
            )
        workspace = (
            str(Path(workspace_path).expanduser().resolve()) if workspace_path is not None else None
        )
        timestamp = _timestamp(self._now())
        intent_json = _json_dumps(intent_dict)
        created = False
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                if selected_key is not None:
                    existing = connection.execute(
                        "SELECT * FROM jobs WHERE project_id = ? AND idempotency_key = ?",
                        (project, selected_key),
                    ).fetchone()
                    if existing is not None:
                        if (
                            existing["user_request"] != request
                            or existing["normalized_intent_json"] != intent_json
                        ):
                            raise IdempotencyConflictError(
                                "idempotency key was already used for a different prepare request",
                                details={"project_id": project, "job_id": existing["job_id"]},
                            )
                        self._insert_event(
                            connection,
                            existing["job_id"],
                            "idempotency_replayed",
                            timestamp,
                            {"operation": "prepare"},
                        )
                        connection.commit()
                        return self._job_from_row(existing), False
                connection.execute(
                    """
                    INSERT INTO jobs (
                        job_id, project_id, user_request, normalized_intent_json,
                        risk_level, source_revision, workspace_path, status,
                        created_at, updated_at, idempotency_key
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        selected_id,
                        project,
                        request,
                        intent_json,
                        selected_risk.value,
                        source_revision,
                        workspace,
                        selected_status.value,
                        timestamp,
                        timestamp,
                        selected_key,
                    ),
                )
                self._insert_event(
                    connection,
                    selected_id,
                    "job_created",
                    timestamp,
                    {"project_id": project},
                    to_status=selected_status,
                )
                connection.commit()
                created = True
        except sqlite3.IntegrityError as exc:
            raise JobStoreError(
                f"job ID {selected_id!r} or idempotency key already exists",
                code="DUPLICATE_JOB_ID",
                details={"job_id": selected_id},
            ) from exc
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot create job: {exc}") from exc
        return self.get(selected_id), created

    def create(self, *args: Any, **kwargs: Any) -> Job:
        return self.create_or_get(*args, **kwargs)[0]

    def create_job(self, *args: Any, **kwargs: Any) -> Job:
        return self.create(*args, **kwargs)

    def get(self, job_id: str) -> Job:
        with closing(self._connect()) as connection:
            row = self._require_job(connection, job_id)
        return self._job_from_row(row)

    def get_job(self, job_id: str) -> Job:
        return self.get(job_id)

    def list(
        self,
        *,
        project_id: str | None = None,
        status: JobStatus | str | None = None,
        limit: int = 100,
    ) -> list[Job]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise JobStoreError("limit must be an integer from 1 to 1000", code="INVALID_LIMIT")
        conditions: list[str] = []
        parameters: list[Any] = []
        if project_id is not None:
            conditions.append("project_id = ?")
            parameters.append(project_id)
        if status is not None:
            conditions.append("status = ?")
            parameters.append(_coerce_status(status).value)
        where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"SELECT * FROM jobs{where} ORDER BY created_at DESC, job_id DESC LIMIT ?"
        parameters.append(limit)
        with closing(self._connect()) as connection:
            rows = connection.execute(query, parameters).fetchall()
        return [self._job_from_row(row) for row in rows]

    def list_jobs(self, **kwargs: Any) -> list[Job]:
        return self.list(**kwargs)

    @staticmethod
    def _require_active_lease(
        row: sqlite3.Row,
        worker_id: str | None,
        lease_token: str | None,
        now: datetime,
    ) -> None:
        current = JobStatus(row["status"])
        if current not in LEASE_GUARDED_STATUSES:
            raise JobLeaseError(
                "job is not in a lease-owned phase",
                code="JOB_NOT_LEASED",
                details={"job_id": row["job_id"], "status": current.value},
            )
        if not worker_id or not lease_token:
            raise JobLeaseError(
                "worker_id and lease_token are required",
                code="LEASE_REQUIRED",
                details={"job_id": row["job_id"]},
            )
        if row["worker_id"] != worker_id or not secrets.compare_digest(
            str(row["lease_token"] or ""), lease_token
        ):
            raise JobLeaseError(
                "worker does not own this job lease",
                code="LEASE_OWNERSHIP_MISMATCH",
                details={"job_id": row["job_id"], "worker_id": worker_id},
            )
        expires = row["lease_expires_at"]
        if not expires or _coerce_datetime(expires) <= now:
            raise JobLeaseExpiredError(
                "job lease has expired",
                details={"job_id": row["job_id"], "lease_expires_at": expires},
            )

    def claim(
        self,
        job_id: str,
        worker_id: str,
        *,
        lease_seconds: int = 300,
        expected_statuses: Iterable[JobStatus | str] = (JobStatus.QUEUED,),
        now: datetime | str | None = None,
    ) -> Job:
        selected_worker = _validate_worker_id(worker_id)
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int):
            raise JobLeaseError("lease_seconds must be an integer", code="INVALID_LEASE_DURATION")
        if not 1 <= lease_seconds <= 86_400:
            raise JobLeaseError(
                "lease_seconds must be between 1 and 86400",
                code="INVALID_LEASE_DURATION",
            )
        expected = frozenset(_coerce_status(status) for status in expected_statuses)
        if not expected:
            raise JobLeaseError("expected_statuses cannot be empty", code="INVALID_CLAIM_STATE")
        selected_now = self._now(now)
        timestamp = _timestamp(selected_now)
        expires_at = _timestamp(selected_now + timedelta(seconds=lease_seconds))
        token = secrets.token_urlsafe(32)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = self._require_job(connection, job_id)
                current = JobStatus(row["status"])
                if current in LEASE_GUARDED_STATUSES:
                    stale = bool(
                        row["lease_expires_at"]
                        and _coerce_datetime(row["lease_expires_at"]) <= selected_now
                    )
                    raise JobAlreadyClaimedError(
                        "job already has a lease; recover an expired lease explicitly",
                        details={
                            "job_id": job_id,
                            "worker_id": row["worker_id"],
                            "lease_expires_at": row["lease_expires_at"],
                            "stale": stale,
                        },
                    )
                if current not in expected or current not in _SAFE_CLAIM_ORIGINS:
                    raise JobLeaseError(
                        "job is not claimable from its current state",
                        code="JOB_NOT_CLAIMABLE",
                        details={
                            "job_id": job_id,
                            "status": current.value,
                            "expected_statuses": sorted(status.value for status in expected),
                        },
                    )
                if bool(row["cancel_requested"]):
                    raise JobCancellationRequestedError(
                        "job has a pending cancellation request",
                        details={"job_id": job_id},
                    )
                attempt = int(row["attempt"]) + 1
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = ?, worker_id = ?, lease_token = ?, lease_expires_at = ?,
                        heartbeat_at = ?, attempt = ?, lease_origin_status = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (
                        JobStatus.CLAIMED.value,
                        selected_worker,
                        token,
                        expires_at,
                        timestamp,
                        attempt,
                        current.value,
                        timestamp,
                        job_id,
                    ),
                )
                self._insert_event(
                    connection,
                    job_id,
                    "job_claimed",
                    timestamp,
                    {
                        "worker_id": selected_worker,
                        "lease_expires_at": expires_at,
                        "attempt": attempt,
                        "origin_status": current.value,
                    },
                    from_status=current,
                    to_status=JobStatus.CLAIMED,
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot claim job: {exc}") from exc
        return self.get(job_id)

    def heartbeat(
        self,
        job_id: str,
        worker_id: str,
        lease_token: str,
        *,
        lease_seconds: int = 300,
        now: datetime | str | None = None,
    ) -> Job:
        selected_worker = _validate_worker_id(worker_id)
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int):
            raise JobLeaseError("lease_seconds must be an integer", code="INVALID_LEASE_DURATION")
        if not 1 <= lease_seconds <= 86_400:
            raise JobLeaseError(
                "lease_seconds must be between 1 and 86400",
                code="INVALID_LEASE_DURATION",
            )
        selected_now = self._now(now)
        timestamp = _timestamp(selected_now)
        expires_at = _timestamp(selected_now + timedelta(seconds=lease_seconds))
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = self._require_job(connection, job_id)
                self._require_active_lease(row, selected_worker, lease_token, selected_now)
                connection.execute(
                    """
                    UPDATE jobs
                    SET heartbeat_at = ?, lease_expires_at = ?, updated_at = ?
                    WHERE job_id = ?
                    """,
                    (timestamp, expires_at, timestamp, job_id),
                )
                self._insert_event(
                    connection,
                    job_id,
                    "job_heartbeat",
                    timestamp,
                    {"worker_id": selected_worker, "lease_expires_at": expires_at},
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot heartbeat job: {exc}") from exc
        return self.get(job_id)

    def is_lease_stale(
        self,
        job_id: str,
        *,
        at: datetime | str | None = None,
    ) -> bool:
        job = self.get(job_id)
        if job.status not in LEASE_GUARDED_STATUSES or job.lease_expires_at is None:
            return False
        return _coerce_datetime(job.lease_expires_at) <= self._now(at)

    def list_stale_leases(self, *, at: datetime | str | None = None) -> list[Job]:
        selected = _timestamp(self._now(at))
        placeholders = ",".join("?" for _ in LEASE_GUARDED_STATUSES)
        parameters = [status.value for status in LEASE_GUARDED_STATUSES]
        parameters.append(selected)
        with closing(self._connect()) as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM jobs
                WHERE status IN ({placeholders})
                    AND lease_expires_at IS NOT NULL
                    AND lease_expires_at <= ?
                ORDER BY lease_expires_at, job_id
                """,
                parameters,
            ).fetchall()
        return [self._job_from_row(row) for row in rows]

    def recover_expired(
        self,
        job_id: str,
        *,
        now: datetime | str | None = None,
    ) -> Job:
        selected_now = self._now(now)
        timestamp = _timestamp(selected_now)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = self._require_job(connection, job_id)
                current = JobStatus(row["status"])
                if current not in LEASE_GUARDED_STATUSES:
                    raise JobLeaseError(
                        "job is not in a recoverable leased phase",
                        code="JOB_NOT_RECOVERABLE",
                        details={"job_id": job_id, "status": current.value},
                    )
                expires = row["lease_expires_at"]
                if not expires or _coerce_datetime(expires) > selected_now:
                    raise JobLeaseError(
                        "active leases cannot be recovered",
                        code="LEASE_NOT_EXPIRED",
                        details={"job_id": job_id, "lease_expires_at": expires},
                    )
                origin = (
                    JobStatus(row["lease_origin_status"])
                    if row["lease_origin_status"]
                    else JobStatus.QUEUED
                )
                if current is JobStatus.CLAIMED and origin in _SAFE_CLAIM_ORIGINS:
                    target = JobStatus.CANCELLED if bool(row["cancel_requested"]) else origin
                else:
                    target = JobStatus.RECOVERY_REQUIRED
                reason = (
                    f"lease expired while worker {row['worker_id']!r} owned phase {current.value!r}"
                )
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = ?, worker_id = NULL, lease_token = NULL,
                        lease_expires_at = NULL, heartbeat_at = NULL,
                        lease_origin_status = NULL, recovery_reason = ?, last_error = ?,
                        updated_at = ?
                    WHERE job_id = ?
                    """,
                    (target.value, reason, reason, timestamp, job_id),
                )
                self._insert_event(
                    connection,
                    job_id,
                    "lease_recovered",
                    timestamp,
                    {
                        "reason": reason,
                        "safe_requeue": current is JobStatus.CLAIMED,
                    },
                    from_status=current,
                    to_status=target,
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot recover job: {exc}") from exc
        return self.get(job_id)

    def transition(
        self,
        job_id: str,
        new_status: JobStatus | str,
        *,
        worker_id: str | None = None,
        lease_token: str | None = None,
        validation_summary: Mapping[str, Any] | None = None,
        evidence_path: str | Path | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        recovery_reason: str | None = None,
        last_error: str | None = None,
        details: Mapping[str, Any] | None = None,
        now: datetime | str | None = None,
    ) -> Job:
        target = _coerce_status(new_status)
        if target is JobStatus.CLAIMED:
            raise InvalidJobTransitionError(
                "claimed state can only be entered through the atomic claim operation",
                code="CLAIM_OPERATION_REQUIRED",
                details={"job_id": job_id},
            )
        selected_now = self._now(now)
        timestamp = _timestamp(selected_now)
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = self._require_job(connection, job_id)
                current = JobStatus(row["status"])
                if target not in VALID_TRANSITIONS[current]:
                    raise InvalidJobTransitionError(
                        f"cannot transition job from {current.value!r} to {target.value!r}",
                        details={
                            "job_id": job_id,
                            "from_status": current.value,
                            "to_status": target.value,
                            "allowed_statuses": sorted(
                                status.value for status in VALID_TRANSITIONS[current]
                            ),
                        },
                    )
                if current in LEASE_GUARDED_STATUSES:
                    self._require_active_lease(row, worker_id, lease_token, selected_now)
                    if bool(row["cancel_requested"]) and target not in {
                        JobStatus.CANCELLED,
                        JobStatus.RECOVERY_REQUIRED,
                    }:
                        raise JobCancellationRequestedError(
                            "job cannot advance while cancellation is requested",
                            details={"job_id": job_id, "status": current.value},
                        )
                validation_json = (
                    _json_dumps(validation_summary)
                    if validation_summary is not None
                    else row["validation_summary_json"]
                )
                evidence = (
                    str(Path(evidence_path).expanduser().resolve())
                    if evidence_path is not None
                    else row["evidence_path"]
                )
                selected_error_code = error_code if error_code is not None else row["error_code"]
                selected_error_message = (
                    error_message if error_message is not None else row["error_message"]
                )
                selected_last_error = last_error if last_error is not None else row["last_error"]
                clear_lease = target not in LEASE_GUARDED_STATUSES
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = ?, updated_at = ?, validation_summary_json = ?,
                        evidence_path = ?, error_code = ?, error_message = ?,
                        recovery_reason = ?, last_error = ?,
                        worker_id = ?, lease_token = ?, lease_expires_at = ?,
                        heartbeat_at = ?, lease_origin_status = ?
                    WHERE job_id = ?
                    """,
                    (
                        target.value,
                        timestamp,
                        validation_json,
                        evidence,
                        selected_error_code,
                        selected_error_message,
                        recovery_reason if recovery_reason is not None else row["recovery_reason"],
                        selected_last_error,
                        None if clear_lease else row["worker_id"],
                        None if clear_lease else row["lease_token"],
                        None if clear_lease else row["lease_expires_at"],
                        None if clear_lease else row["heartbeat_at"],
                        None if clear_lease else row["lease_origin_status"],
                        job_id,
                    ),
                )
                self._insert_event(
                    connection,
                    job_id,
                    "status_transition",
                    timestamp,
                    details,
                    from_status=current,
                    to_status=target,
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot transition job: {exc}") from exc
        return self.get(job_id)

    def request_cancellation(self, job_id: str, *, reason: str | None = None) -> Job:
        timestamp = _timestamp(self._now())
        selected_reason = (reason or "Cancellation requested.").strip()
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = self._require_job(connection, job_id)
                current = JobStatus(row["status"])
                if current is JobStatus.CANCELLED:
                    connection.commit()
                    return self._job_from_row(row)
                if current in {JobStatus.COMPLETED, JobStatus.FAILED}:
                    raise JobStoreError(
                        "terminal completed or failed jobs cannot be cancelled",
                        code="JOB_ALREADY_TERMINAL",
                        details={"job_id": job_id, "status": current.value},
                    )
                if not bool(row["cancel_requested"]):
                    connection.execute(
                        "UPDATE jobs SET cancel_requested = 1, updated_at = ? WHERE job_id = ?",
                        (timestamp, job_id),
                    )
                    self._insert_event(
                        connection,
                        job_id,
                        "cancellation_requested",
                        timestamp,
                        {"reason": selected_reason},
                    )
                if current in _IMMEDIATE_CANCEL_STATUSES:
                    connection.execute(
                        """
                        UPDATE jobs
                        SET status = ?, worker_id = NULL, lease_token = NULL,
                            lease_expires_at = NULL, heartbeat_at = NULL,
                            lease_origin_status = NULL, updated_at = ?
                        WHERE job_id = ?
                        """,
                        (JobStatus.CANCELLED.value, timestamp, job_id),
                    )
                    self._insert_event(
                        connection,
                        job_id,
                        "status_transition",
                        timestamp,
                        {"reason": selected_reason},
                        from_status=current,
                        to_status=JobStatus.CANCELLED,
                    )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot request cancellation: {exc}") from exc
        return self.get(job_id)

    def record_event(
        self,
        job_id: str,
        event_type: str,
        details: Mapping[str, Any] | None = None,
        *,
        from_status: JobStatus | str | None = None,
        to_status: JobStatus | str | None = None,
    ) -> JobEvent:
        if not isinstance(event_type, str) or not event_type.strip():
            raise JobStoreError("event_type must be a non-empty string", code="INVALID_EVENT_TYPE")
        timestamp = _timestamp(self._now())
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._require_job(connection, job_id)
                event_id = self._insert_event(
                    connection,
                    job_id,
                    event_type.strip(),
                    timestamp,
                    details,
                    from_status=from_status,
                    to_status=to_status,
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot record job event: {exc}") from exc
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT * FROM job_events WHERE event_id = ?", (event_id,)
            ).fetchone()
        if row is None:
            raise JobStoreError("newly recorded event could not be read")
        return self._event_from_row(row)

    def add_event(self, *args: Any, **kwargs: Any) -> JobEvent:
        return self.record_event(*args, **kwargs)

    def list_events(self, job_id: str) -> list[JobEvent]:
        with closing(self._connect()) as connection:
            self._require_job(connection, job_id)
            rows = connection.execute(
                "SELECT * FROM job_events WHERE job_id = ? ORDER BY event_id",
                (job_id,),
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def begin_idempotent_operation(
        self,
        job_id: str,
        operation: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if not isinstance(operation, str) or not _OPERATION_PATTERN.fullmatch(operation):
            raise IdempotentOperationError("operation name is invalid", code="INVALID_OPERATION")
        selected_key = _validate_idempotency_key(idempotency_key)
        assert selected_key is not None
        timestamp = _timestamp(self._now())
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._require_job(connection, job_id)
                row = connection.execute(
                    """
                    SELECT * FROM job_operations
                    WHERE job_id = ? AND operation = ? AND idempotency_key = ?
                    """,
                    (job_id, operation, selected_key),
                ).fetchone()
                if row is not None:
                    connection.commit()
                    return self._operation_from_row(row, replay=True)
                connection.execute(
                    """
                    INSERT INTO job_operations (
                        job_id, operation, idempotency_key, state, created_at, updated_at
                    ) VALUES (?, ?, ?, 'started', ?, ?)
                    """,
                    (job_id, operation, selected_key, timestamp, timestamp),
                )
                self._insert_event(
                    connection,
                    job_id,
                    "idempotent_operation_started",
                    timestamp,
                    {"operation": operation},
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot begin idempotent operation: {exc}") from exc
        return {
            "job_id": job_id,
            "operation": operation,
            "idempotency_key": selected_key,
            "state": "started",
            "result": None,
            "error_code": None,
            "error_message": None,
            "replay": False,
        }

    @staticmethod
    def _operation_from_row(row: sqlite3.Row, *, replay: bool) -> dict[str, Any]:
        result = json.loads(row["result_json"]) if row["result_json"] is not None else None
        if result is not None and not isinstance(result, dict):
            raise JobStoreError("stored idempotency result is invalid", code="JOB_RECORD_CORRUPT")
        return {
            "job_id": row["job_id"],
            "operation": row["operation"],
            "idempotency_key": row["idempotency_key"],
            "state": row["state"],
            "result": result,
            "error_code": row["error_code"],
            "error_message": row["error_message"],
            "replay": replay,
        }

    def complete_idempotent_operation(
        self,
        job_id: str,
        operation: str,
        idempotency_key: str,
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self._finish_idempotent_operation(
            job_id,
            operation,
            idempotency_key,
            state="completed",
            result=result,
        )

    def fail_idempotent_operation(
        self,
        job_id: str,
        operation: str,
        idempotency_key: str,
        *,
        error_code: str,
        error_message: str,
    ) -> dict[str, Any]:
        return self._finish_idempotent_operation(
            job_id,
            operation,
            idempotency_key,
            state="failed",
            error_code=error_code,
            error_message=error_message,
        )

    def _finish_idempotent_operation(
        self,
        job_id: str,
        operation: str,
        idempotency_key: str,
        *,
        state: str,
        result: Mapping[str, Any] | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        selected_key = _validate_idempotency_key(idempotency_key)
        assert selected_key is not None
        timestamp = _timestamp(self._now())
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT * FROM job_operations
                    WHERE job_id = ? AND operation = ? AND idempotency_key = ?
                    """,
                    (job_id, operation, selected_key),
                ).fetchone()
                if row is None:
                    raise IdempotentOperationError(
                        "idempotent operation has not been started",
                        code="IDEMPOTENT_OPERATION_NOT_FOUND",
                    )
                if row["state"] == "completed":
                    connection.commit()
                    return self._operation_from_row(row, replay=True)
                if row["state"] == "failed":
                    if state == "failed":
                        connection.commit()
                        return self._operation_from_row(row, replay=True)
                    raise IdempotentOperationError(
                        "a failed idempotent operation cannot later be marked completed",
                        code="IDEMPOTENT_OPERATION_ALREADY_FAILED",
                        details={"job_id": job_id, "operation": operation},
                    )
                connection.execute(
                    """
                    UPDATE job_operations
                    SET state = ?, result_json = ?, error_code = ?, error_message = ?,
                        updated_at = ?
                    WHERE job_id = ? AND operation = ? AND idempotency_key = ?
                    """,
                    (
                        state,
                        _json_dumps(result) if result is not None else None,
                        error_code,
                        error_message,
                        timestamp,
                        job_id,
                        operation,
                        selected_key,
                    ),
                )
                self._insert_event(
                    connection,
                    job_id,
                    f"idempotent_operation_{state}",
                    timestamp,
                    {"operation": operation, "error_code": error_code},
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot finish idempotent operation: {exc}") from exc
        with closing(self._connect()) as connection:
            finished = connection.execute(
                """
                SELECT * FROM job_operations
                WHERE job_id = ? AND operation = ? AND idempotency_key = ?
                """,
                (job_id, operation, selected_key),
            ).fetchone()
        if finished is None:
            raise JobStoreError("finished idempotent operation could not be read")
        return self._operation_from_row(finished, replay=False)

    def update(self, job_id: str, **fields: Any) -> Job:
        """Update recoverable metadata; status and ownership use dedicated methods."""

        allowed = {
            "source_revision",
            "workspace_path",
            "validation_summary",
            "evidence_path",
            "error_code",
            "error_message",
            "normalized_intent",
            "risk_level",
            "recovery_reason",
            "last_error",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise InvalidJobUpdateError(
                "job update contains unsupported fields",
                details={"fields": sorted(unknown)},
            )
        if not fields:
            return self.get(job_id)
        column_values: dict[str, Any] = {}
        for field, value in fields.items():
            if field in {"workspace_path", "evidence_path"}:
                column_values[field] = (
                    str(Path(value).expanduser().resolve()) if value is not None else None
                )
            elif field == "validation_summary":
                column_values["validation_summary_json"] = (
                    _json_dumps(value) if value is not None else None
                )
            elif field == "normalized_intent":
                if isinstance(value, NormalizedIntent):
                    value = value.to_dict()
                if not isinstance(value, Mapping):
                    raise InvalidJobUpdateError("normalized_intent must be a mapping")
                column_values["normalized_intent_json"] = _json_dumps(value)
            elif field == "risk_level":
                column_values[field] = _coerce_risk(value).value
            else:
                column_values[field] = value
        column_values["updated_at"] = _timestamp(self._now())
        assignments = ", ".join(f"{column} = ?" for column in column_values)
        parameters = [*column_values.values(), job_id]
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._require_job(connection, job_id)
                connection.execute(f"UPDATE jobs SET {assignments} WHERE job_id = ?", parameters)
                self._insert_event(
                    connection,
                    job_id,
                    "job_updated",
                    column_values["updated_at"],
                    {"fields": sorted(fields)},
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot update job: {exc}") from exc
        return self.get(job_id)


__all__ = [
    "IdempotencyConflictError",
    "IdempotentOperationError",
    "InvalidJobTransitionError",
    "InvalidJobUpdateError",
    "JobAlreadyClaimedError",
    "JobCancellationRequestedError",
    "JobLeaseError",
    "JobLeaseExpiredError",
    "JobNotFoundError",
    "JobStore",
    "JobStoreError",
    "LEASE_GUARDED_STATUSES",
    "VALID_TRANSITIONS",
]
