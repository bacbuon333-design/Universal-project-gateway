"""SQLite persistence for synchronous jobs and their append-style event log."""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from collections.abc import Mapping
from contextlib import closing
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
    utc_now,
)

VALID_TRANSITIONS: Mapping[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.PREPARED, JobStatus.FAILED, JobStatus.CANCELLED}),
    JobStatus.PREPARED: frozenset(
        {
            JobStatus.RUNNING,
            JobStatus.WAITING_FOR_APPROVAL,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }
    ),
    JobStatus.RUNNING: frozenset(
        {
            JobStatus.WAITING_FOR_APPROVAL,
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }
    ),
    JobStatus.WAITING_FOR_APPROVAL: frozenset(
        {JobStatus.RUNNING, JobStatus.FAILED, JobStatus.CANCELLED}
    ),
    JobStatus.COMPLETED: frozenset(),
    JobStatus.FAILED: frozenset(),
    JobStatus.CANCELLED: frozenset(),
}

_JOB_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


class JobStoreError(GatewayError):
    default_code = "JOB_STORE_ERROR"


class JobNotFoundError(JobStoreError):
    default_code = "JOB_NOT_FOUND"


class InvalidJobTransitionError(JobStoreError):
    default_code = "INVALID_JOB_TRANSITION"


class InvalidJobUpdateError(JobStoreError):
    default_code = "INVALID_JOB_UPDATE"


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


class JobStore:
    """Small durable job store with validated, atomic state transitions."""

    def __init__(self, database_path: str | Path, *, timeout_seconds: float = 5.0) -> None:
        self.database_path = Path(database_path).expanduser().resolve()
        self.timeout_seconds = timeout_seconds
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

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

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.executescript(
                """
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
                            'queued','prepared','running','waiting_for_approval',
                            'completed','failed','cancelled'
                        )
                    ),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    validation_summary_json TEXT,
                    evidence_path TEXT,
                    error_code TEXT,
                    error_message TEXT
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

                CREATE INDEX IF NOT EXISTS idx_jobs_project_status
                    ON jobs(project_id, status);
                CREATE INDEX IF NOT EXISTS idx_job_events_job_id
                    ON job_events(job_id, event_id);
                PRAGMA user_version = 1;
                """
            )

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

    def create(
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
    ) -> Job:
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
        selected_status = _coerce_status(status)
        selected_id = job_id or uuid.uuid4().hex
        if not isinstance(selected_id, str) or not _JOB_ID_PATTERN.fullmatch(selected_id):
            raise JobStoreError(
                "job_id must be filesystem-safe and at most 80 characters",
                code="INVALID_JOB_ID",
            )
        workspace = (
            str(Path(workspace_path).expanduser().resolve()) if workspace_path is not None else None
        )
        timestamp = utc_now()
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO jobs (
                        job_id, project_id, user_request, normalized_intent_json,
                        risk_level, source_revision, workspace_path, status,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        selected_id,
                        project_id.strip(),
                        user_request.strip(),
                        _json_dumps(intent_dict),
                        selected_risk.value,
                        source_revision,
                        workspace,
                        selected_status.value,
                        timestamp,
                        timestamp,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO job_events (
                        job_id, event_type, created_at, details_json,
                        from_status, to_status
                    ) VALUES (?, 'job_created', ?, ?, NULL, ?)
                    """,
                    (
                        selected_id,
                        timestamp,
                        _json_dumps({"project_id": project_id.strip()}),
                        selected_status.value,
                    ),
                )
                connection.commit()
        except sqlite3.IntegrityError as exc:
            raise JobStoreError(
                f"job ID {selected_id!r} already exists",
                code="DUPLICATE_JOB_ID",
                details={"job_id": selected_id},
            ) from exc
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot create job: {exc}") from exc
        return self.get(selected_id)

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

    def transition(
        self,
        job_id: str,
        new_status: JobStatus | str,
        *,
        validation_summary: Mapping[str, Any] | None = None,
        evidence_path: str | Path | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> Job:
        target = _coerce_status(new_status)
        timestamp = utc_now()
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
                connection.execute(
                    """
                    UPDATE jobs
                    SET status = ?, updated_at = ?, validation_summary_json = ?,
                        evidence_path = ?, error_code = ?, error_message = ?
                    WHERE job_id = ?
                    """,
                    (
                        target.value,
                        timestamp,
                        validation_json,
                        evidence,
                        selected_error_code,
                        selected_error_message,
                        job_id,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO job_events (
                        job_id, event_type, created_at, details_json,
                        from_status, to_status
                    ) VALUES (?, 'status_transition', ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        timestamp,
                        _json_dumps(details or {}),
                        current.value,
                        target.value,
                    ),
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot transition job: {exc}") from exc
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
        from_value = _coerce_status(from_status).value if from_status is not None else None
        to_value = _coerce_status(to_status).value if to_status is not None else None
        timestamp = utc_now()
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._require_job(connection, job_id)
                cursor = connection.execute(
                    """
                    INSERT INTO job_events (
                        job_id, event_type, created_at, details_json,
                        from_status, to_status
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        job_id,
                        event_type.strip(),
                        timestamp,
                        _json_dumps(details or {}),
                        from_value,
                        to_value,
                    ),
                )
                event_id = int(cursor.lastrowid)
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

    def update(self, job_id: str, **fields: Any) -> Job:
        """Update recoverable metadata; status changes must use ``transition``."""

        allowed = {
            "source_revision",
            "workspace_path",
            "validation_summary",
            "evidence_path",
            "error_code",
            "error_message",
            "normalized_intent",
            "risk_level",
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
        column_values["updated_at"] = utc_now()
        assignments = ", ".join(f"{column} = ?" for column in column_values)
        parameters = [*column_values.values(), job_id]
        try:
            with closing(self._connect()) as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._require_job(connection, job_id)
                connection.execute(f"UPDATE jobs SET {assignments} WHERE job_id = ?", parameters)
                connection.execute(
                    """
                    INSERT INTO job_events (
                        job_id, event_type, created_at, details_json,
                        from_status, to_status
                    ) VALUES (?, 'job_updated', ?, ?, NULL, NULL)
                    """,
                    (
                        job_id,
                        column_values["updated_at"],
                        _json_dumps({"fields": sorted(fields)}),
                    ),
                )
                connection.commit()
        except sqlite3.Error as exc:
            raise JobStoreError(f"cannot update job: {exc}") from exc
        return self.get(job_id)
