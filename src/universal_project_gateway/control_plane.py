"""Control-plane orchestration for registered, job-scoped Gateway operations."""

from __future__ import annotations

import shutil
import uuid
from collections.abc import Iterable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from . import __version__
from .config import GatewayConfig
from .context import ContextCompiler
from .contracts import CONTRACT_VERSIONS
from .git_controller import GitController
from .intelligence import ProjectIntelligenceCache
from .intent import IntentCompiler
from .jobs import LEASE_GUARDED_STATUSES, JobStore
from .models import GatewayError, Job, JobStatus, ProjectManifest, json_ready
from .policy import PolicyEngine
from .registry import ProjectRegistry
from .runner import LocalRunner, Runner


class ServiceError(GatewayError):
    """Stable structured error at the Gateway application boundary."""

    default_code = "SERVICE_ERROR"


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(json_ready(value))
    if hasattr(value, "to_dict"):
        return dict(json_ready(value.to_dict()))
    raise TypeError(f"Expected a mapping-like result, got {type(value).__name__}")


class ControlPlane:
    """Authorize and orchestrate high-level project and job operations."""

    def __init__(
        self,
        config: GatewayConfig | str | Path | None = None,
        *,
        runner: Runner | None = None,
        worker_id: str | None = None,
        lease_seconds: int = 300,
    ) -> None:
        if config is None:
            config = GatewayConfig.discover()
        elif not isinstance(config, GatewayConfig):
            config = GatewayConfig.from_root(config)
        self.config = config
        self.config.ensure_runtime_dirs()
        registry_seed = config.root_dir / "registry" / "projects.yaml"
        if not config.registry_path.exists() and registry_seed.is_file():
            shutil.copy2(registry_seed, config.registry_path)
        # The versioned seed registry may use repository-relative paths so a
        # self-registration remains portable when the checkout moves. Runtime
        # records written by the registry continue to use canonical paths.
        self.registry = ProjectRegistry(config.registry_path, path_base=config.root_dir)
        self.jobs = JobStore(config.database_path)
        self.policy = PolicyEngine()
        self.intent = IntentCompiler()
        self.runner = runner or LocalRunner(config)
        self.intelligence = ProjectIntelligenceCache(config)
        self.worker_id = worker_id or f"local-{uuid.uuid4().hex}"
        if isinstance(lease_seconds, bool) or not isinstance(lease_seconds, int):
            raise ValueError("lease_seconds must be an integer")
        if not 1 <= lease_seconds <= 86_400:
            raise ValueError("lease_seconds must be between 1 and 86400")
        self.lease_seconds = lease_seconds

    def get_status(self) -> dict[str, Any]:
        return {
            "system_id": "universal-project-gateway",
            "version": __version__,
            "status": "ready",
            "root": str(self.config.root_dir),
            "risk_boundary": {"permittable": ["R0", "R1", "R2", "R3"], "prohibited": ["R4"]},
            "transports": ["stdio", "streamable-http-localhost"],
            "contracts": dict(CONTRACT_VERSIONS),
        }

    def list_adapters(self) -> list[dict[str, Any]]:
        """Return immutable adapter capability declarations as JSON values."""

        return self.runner.list_adapters()

    def register_project(self, manifest_path: str | Path) -> dict[str, Any]:
        record = self.registry.register(manifest_path)
        return record.to_dict()

    def list_projects(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.registry.list()]

    def get_project(self, project_id: str) -> dict[str, Any]:
        record = self.registry.get(project_id)
        manifest = self.registry.get_manifest(project_id)
        return {"record": record.to_dict(), "manifest": manifest.to_dict(include_metadata=True)}

    def generate_project_intelligence(self, project_id: str) -> dict[str, Any]:
        """Refresh one cache from a registered manifest and bounded source scan."""

        manifest = self.registry.get_manifest(project_id)
        return self.intelligence.generate(manifest)

    def list_project_intelligence(self) -> list[dict[str, Any]]:
        """List verified cache metadata without scanning registered sources."""

        return self.intelligence.list()

    def get_project_intelligence(self, project_id: str) -> dict[str, Any]:
        """Read one verified cache without scanning or executing project code."""

        self.registry.get(project_id)
        return self.intelligence.get(project_id)

    def _job(self, job_id: str) -> Job:
        return self.jobs.get(job_id)

    def _manifest(self, job: Job) -> ProjectManifest:
        return self.registry.get_manifest(job.project_id)

    @staticmethod
    def _require(decision: Any) -> None:
        if not decision.allowed:
            raise ServiceError(
                decision.message,
                code=decision.reason_code,
                details=decision.to_dict(),
            )

    @staticmethod
    def _lease_credentials(job: Job) -> tuple[str, str]:
        if job.worker_id is None or job.lease_token is None:
            raise ServiceError("Job does not have an active lease", code="LEASE_REQUIRED")
        return job.worker_id, job.lease_token

    def _claim(self, job_id: str, *expected_statuses: JobStatus) -> Job:
        return self.jobs.claim(
            job_id,
            self.worker_id,
            lease_seconds=self.lease_seconds,
            expected_statuses=expected_statuses,
        )

    def _heartbeat(self, job: Job) -> Job:
        worker_id, lease_token = self._lease_credentials(job)
        return self.jobs.heartbeat(
            job.job_id,
            worker_id,
            lease_token,
            lease_seconds=self.lease_seconds,
        )

    def _transition_owned(
        self,
        job: Job,
        status: JobStatus,
        **kwargs: Any,
    ) -> Job:
        worker_id, lease_token = self._lease_credentials(job)
        return self.jobs.transition(
            job.job_id,
            status,
            worker_id=worker_id,
            lease_token=lease_token,
            **kwargs,
        )

    def _cancel_owned_job(self, job: Job, *, phase: str, message: str) -> Job:
        cancelled = self._transition_owned(
            job,
            JobStatus.CANCELLED,
            details={"phase": phase, "reason": message},
        )
        operations = [event.to_dict() for event in self.jobs.list_events(job.job_id)]
        self.runner.record_cancellation(
            cancelled,
            operations=operations,
            phase=phase,
            message=message,
        )
        return cancelled

    @staticmethod
    def _idempotent_replay(record: Mapping[str, Any]) -> dict[str, Any] | None:
        if not record.get("replay"):
            return None
        if record.get("state") == "completed" and isinstance(record.get("result"), Mapping):
            return dict(record["result"])
        if record.get("state") == "started":
            raise ServiceError(
                "An operation with this idempotency key is already in progress",
                code="IDEMPOTENT_OPERATION_IN_PROGRESS",
                details={
                    "job_id": record.get("job_id"),
                    "operation": record.get("operation"),
                },
            )
        raise ServiceError(
            record.get("error_message") or "A previous idempotent operation failed",
            code=record.get("error_code") or "IDEMPOTENT_OPERATION_FAILED",
            details={
                "job_id": record.get("job_id"),
                "operation": record.get("operation"),
            },
        )

    def prepare_task(
        self,
        project_id: str,
        request: str,
        *,
        target_paths: Iterable[str] = (),
        requested_operation: str | None = None,
        publication_preference: str = "none",
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        manifest = self.registry.get_manifest(project_id)
        target_scope = tuple(target_paths)
        normalized = self.intent.compile(
            project_id,
            request,
            target_paths=target_scope,
            requested_operation=requested_operation,
            publication_preference=publication_preference,
            required_validation=manifest.validation_requirements,
        )
        action = "read" if normalized.risk_level.value == "R0" else "write"
        self._require(self.policy.decide(action, manifest))
        job, created = self.jobs.create_or_get(
            project_id,
            request,
            normalized,
            risk_level=normalized.risk_level,
            idempotency_key=idempotency_key,
        )
        if not created:
            return {
                "job": job.to_dict(),
                "intent": dict(job.normalized_intent),
                "workspace": str(job.workspace_path) if job.workspace_path else None,
                "evidence": (
                    str(job.evidence_path)
                    if job.evidence_path
                    else str(self.runner.evidence_path(job.job_id))
                ),
                "idempotent_replay": True,
            }
        try:
            job = self._claim(job.job_id, JobStatus.QUEUED)
            job = self._transition_owned(
                job,
                JobStatus.PREPARING,
                details={"phase": "workspace_preparation"},
            )
            if self.jobs.get(job.job_id).cancel_requested:
                self._cancel_owned_job(
                    job,
                    phase="preparing",
                    message="Cancellation was observed before workspace preparation.",
                )
                raise ServiceError("Job was cancelled", code="JOB_CANCELLED")
            preparation = self.runner.prepare_workspace(job.job_id, manifest)
            snapshot_data = dict(preparation.snapshot)
            workspace_path = preparation.workspace_path
            job = self.jobs.update(
                job.job_id,
                workspace_path=workspace_path,
                source_revision=snapshot_data.get("source_revision"),
            )
            context_pack = ContextCompiler(
                max_files=self.config.context_max_files,
                max_total_bytes=self.config.context_max_bytes,
            ).compile(
                manifest.local_path,
                manifest,
                normalized,
                target_paths=target_scope,
                gateway_rules=(
                    "Operate only within the active isolated job workspace.",
                    "Never access protected paths or credentials.",
                    "Run only manifest-declared validation actions.",
                    "R4 actions, merges, force pushes, and deployments are prohibited.",
                ),
                project_intelligence=ProjectIntelligenceCache.compact(
                    self.intelligence.get_or_generate(manifest)
                ),
            )
            evidence_path = self.runner.record_preparation(
                job.job_id,
                intent=normalized.to_dict(),
                context_pack=context_pack,
                snapshot=snapshot_data,
            )
            if self.jobs.get(job.job_id).cancel_requested:
                self._cancel_owned_job(
                    job,
                    phase="preparing",
                    message="Cancellation was observed after workspace preparation.",
                )
                raise ServiceError("Job was cancelled", code="JOB_CANCELLED")
            job = self._transition_owned(
                job,
                JobStatus.PREPARED,
                evidence_path=evidence_path,
                details={"workspace_path": str(workspace_path)},
            )
            self.runner.record_task(job)
            self.runner.record_evidence_event(
                job.job_id,
                job.project_id,
                "job_prepared",
                {"status": job.status.value, "risk_level": job.risk_level.value},
                actor="control_plane",
            )
            self._sync_operations(job.job_id)
            return {
                "job": job.to_dict(),
                "intent": normalized.to_dict(),
                "workspace": str(workspace_path),
                "evidence": str(evidence_path),
            }
        except Exception as exc:
            with suppress(Exception):
                current = self.jobs.get(job.job_id)
                if current.status is not JobStatus.CANCELLED:
                    evidence_path = self.runner.evidence_path(job.job_id)
                    if current.status in LEASE_GUARDED_STATUSES:
                        failed_job = self._transition_owned(
                            current,
                            JobStatus.FAILED,
                            evidence_path=evidence_path,
                            error_code=getattr(exc, "code", "PREPARATION_FAILED"),
                            error_message=str(exc),
                            last_error=str(exc),
                        )
                    else:
                        failed_job = self.jobs.transition(
                            current.job_id,
                            JobStatus.FAILED,
                            evidence_path=evidence_path,
                            error_code=getattr(exc, "code", "PREPARATION_FAILED"),
                            error_message=str(exc),
                            last_error=str(exc),
                        )
                    operations = [event.to_dict() for event in self.jobs.list_events(job.job_id)]
                    self.runner.record_preparation_failure(
                        failed_job,
                        intent=normalized.to_dict(),
                        operations=operations,
                        error_code=getattr(exc, "code", "PREPARATION_FAILED"),
                        message=str(exc),
                    )
            raise

    def inspect_job(self, job_id: str) -> dict[str, Any]:
        job = self._job(job_id)
        return {
            "job": job.to_dict(),
            "events": [event.to_dict() for event in self.jobs.list_events(job_id)],
        }

    def request_cancellation(self, job_id: str, *, reason: str | None = None) -> dict[str, Any]:
        job = self.jobs.request_cancellation(job_id, reason=reason)
        events = [event.to_dict() for event in self.jobs.list_events(job_id)]
        if job.status is JobStatus.CANCELLED:
            self.runner.record_cancellation(
                job,
                operations=events,
                phase="queued_or_waiting",
                message=reason or "Cancellation requested.",
            )
        elif job.evidence_path is not None:
            self.runner.record_operations(job_id, events)
        return {"job": job.to_dict(), "events": events}

    def recover_expired_job(self, job_id: str) -> dict[str, Any]:
        job = self.jobs.recover_expired(job_id)
        events = [event.to_dict() for event in self.jobs.list_events(job_id)]
        if job.evidence_path is not None:
            self.runner.record_operations(job_id, events)
        return {"job": job.to_dict(), "events": events}

    def _job_context(self, job_id: str) -> tuple[Job, ProjectManifest]:
        job = self._job(job_id)
        if job.workspace_path is None:
            raise ServiceError("Job has no workspace", code="WORKSPACE_NOT_READY")
        manifest = self._manifest(job)
        return job, manifest

    def _event(self, job_id: str, event_type: str, details: Mapping[str, Any]) -> None:
        self.jobs.record_event(job_id, event_type, details)
        if event_type in {
            "workspace_file_written",
            "workspace_text_replaced",
            "workspace_file_moved",
        }:
            job = self.jobs.get(job_id)
            self.runner.record_evidence_event(
                job_id,
                job.project_id,
                "file_operation_applied",
                {"operation": event_type, **dict(details)},
                actor="control_plane",
            )
        if self.jobs.get(job_id).status not in {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }:
            self._sync_operations(job_id)

    def _sync_operations(self, job_id: str) -> None:
        events = [event.to_dict() for event in self.jobs.list_events(job_id)]
        self.runner.record_operations(job_id, events)

    def list_workspace_files(self, job_id: str, path: str = ".") -> dict[str, Any]:
        job, manifest = self._job_context(job_id)
        self._require(
            self.policy.decide("read", manifest, path="README.md" if path == "." else path)
        )
        entries = self.runner.list_workspace_files(job, manifest, path)
        self._event(job_id, "workspace_listed", {"path": path, "count": len(entries)})
        return {"job_id": job_id, "path": path, "entries": entries}

    def search_workspace(
        self,
        job_id: str,
        query: str,
        *,
        path: str = ".",
        max_results: int = 100,
    ) -> dict[str, Any]:
        job, manifest = self._job_context(job_id)
        self._require(
            self.policy.decide("read", manifest, path="README.md" if path == "." else path)
        )
        results = self.runner.search_workspace(
            job,
            manifest,
            query,
            path=path,
            max_results=max_results,
        )
        self._event(
            job_id,
            "workspace_searched",
            {"path": path, "query": query, "result_count": len(results)},
        )
        return {"job_id": job_id, "query": query, "results": results}

    def read_workspace_file(self, job_id: str, path: str) -> dict[str, Any]:
        job, manifest = self._job_context(job_id)
        self._require(self.policy.decide("read", manifest, path=path))
        content, metadata = self.runner.read_workspace_file(job, manifest, path)
        self._event(job_id, "workspace_file_read", {"path": path, "size": metadata.get("size")})
        return {"job_id": job_id, "path": path, "content": content, "metadata": metadata}

    def write_workspace_file(
        self,
        job_id: str,
        path: str,
        content: str,
        *,
        create: bool = False,
    ) -> dict[str, Any]:
        job, manifest = self._job_context(job_id)
        if job.status not in {JobStatus.PREPARED, JobStatus.RUNNING}:
            raise ServiceError("Job is not writable in its current state", code="JOB_NOT_WRITABLE")
        self._require(self.policy.decide("write", manifest, path=path))
        result = self.runner.write_workspace_file(
            job,
            manifest,
            path,
            content,
            create=create,
        )
        self._event(job_id, "workspace_file_written", {"create": create, **result})
        return {"job_id": job_id, **result}

    def replace_workspace_text(
        self,
        job_id: str,
        path: str,
        old: str,
        new: str,
        *,
        max_replacements: int = 100,
    ) -> dict[str, Any]:
        job, manifest = self._job_context(job_id)
        if job.status not in {JobStatus.PREPARED, JobStatus.RUNNING}:
            raise ServiceError("Job is not writable in its current state", code="JOB_NOT_WRITABLE")
        self._require(self.policy.decide("write", manifest, path=path))
        result = self.runner.replace_workspace_text(
            job,
            manifest,
            path,
            old,
            new,
            max_replacements=max_replacements,
        )
        self._event(job_id, "workspace_text_replaced", result)
        return {"job_id": job_id, **result}

    def move_workspace_file(self, job_id: str, source: str, destination: str) -> dict[str, Any]:
        job, manifest = self._job_context(job_id)
        if job.status not in {JobStatus.PREPARED, JobStatus.RUNNING}:
            raise ServiceError("Job is not writable in its current state", code="JOB_NOT_WRITABLE")
        self._require(self.policy.decide("write", manifest, path=source))
        self._require(self.policy.decide("write", manifest, path=destination))
        result = self.runner.move_workspace_file(
            job,
            manifest,
            source,
            destination,
        )
        self._event(job_id, "workspace_file_moved", result)
        return {"job_id": job_id, **result}

    def request_delete(self, job_id: str, path: str) -> dict[str, Any]:
        job, manifest = self._job_context(job_id)
        request = self.runner.request_delete(job, manifest, path)
        self._event(job_id, "deletion_requested", request)
        if job.status == JobStatus.PREPARED:
            self.jobs.transition(
                job_id,
                JobStatus.WAITING_FOR_APPROVAL,
                details={"request_id": request["request_id"], "executed": False},
            )
            self._sync_operations(job_id)
        return request

    def get_diff(self, job_id: str) -> dict[str, Any]:
        job, _ = self._job_context(job_id)
        payload = self.runner.generate_patch(job_id)
        if job.status not in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            self.runner.record_patch(job_id, payload)
            self._event(
                job_id,
                "workspace_diff_computed",
                {
                    "changed_count": len(payload.get("files_changed", [])),
                    "stale_source": payload.get("stale_source_warning"),
                },
            )
        return {"job_id": job_id, **payload}

    def validate(
        self,
        job_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        operation_record: dict[str, Any] | None = None
        if idempotency_key is not None:
            operation_record = self.jobs.begin_idempotent_operation(
                job_id,
                "validate",
                idempotency_key,
            )
            replay = self._idempotent_replay(operation_record)
            if replay is not None:
                return replay
        job, manifest = self._job_context(job_id)
        if job.status == JobStatus.COMPLETED and job.validation_summary is not None:
            evidence = self.runner.get_evidence(job)
            result = {
                "job_id": job_id,
                **dict(job.validation_summary),
                "evidence_path": evidence["path"],
                "evidence_verified": evidence["verified"],
            }
            if idempotency_key is not None:
                self.jobs.complete_idempotent_operation(
                    job_id,
                    "validate",
                    idempotency_key,
                    result,
                )
            return result
        try:
            if job.status is JobStatus.CANCELLED:
                raise ServiceError("Cancelled jobs cannot be validated", code="JOB_CANCELLED")
            if job.status is JobStatus.RECOVERY_REQUIRED:
                raise ServiceError(
                    "Job requires recovery review before validation can continue",
                    code="JOB_RECOVERY_REQUIRED",
                )
            if job.status != JobStatus.PREPARED:
                raise ServiceError("Only a prepared job can be validated", code="INVALID_JOB_STATE")
            self._require(self.policy.decide("validate", manifest))
            for action in manifest.validation_requirements:
                if action != "install":
                    self._require(self.policy.decide(action, manifest))
        except Exception as exc:
            if idempotency_key is not None:
                with suppress(Exception):
                    self.jobs.fail_idempotent_operation(
                        job_id,
                        "validate",
                        idempotency_key,
                        error_code=getattr(exc, "code", "VALIDATION_REFUSED"),
                        error_message=str(exc),
                    )
            raise
        leased_job: Job | None = None
        try:
            leased_job = self._claim(job_id, JobStatus.PREPARED)
            leased_job = self._transition_owned(
                leased_job,
                JobStatus.VALIDATING,
                details={"actions": list(manifest.validation_requirements)},
            )

            def heartbeat() -> None:
                assert leased_job is not None
                self._heartbeat(leased_job)

            def should_cancel() -> bool:
                return self.jobs.get(job_id).cancel_requested

            execution = self.runner.execute_validation(
                leased_job,
                manifest,
                heartbeat=heartbeat,
                should_cancel=should_cancel,
            )
            summary = dict(execution.summary)
            current = self.jobs.get(job_id)
            cancelled = execution.cancelled or current.cancel_requested
            mandatory_passed = bool(summary.get("passed")) and not cancelled
            if cancelled:
                summary["passed"] = False
                summary["cancelled"] = True
                summary.setdefault(
                    "cancellation_reason",
                    execution.cancellation_reason or "Cancellation was observed after validation.",
                )
                status = JobStatus.CANCELLED
                error_code = "JOB_CANCELLED"
                error_message = str(summary["cancellation_reason"])
            else:
                status = JobStatus.COMPLETED if mandatory_passed else JobStatus.FAILED
                error_code = None if mandatory_passed else "VALIDATION_FAILED"
                error_message = (
                    None if mandatory_passed else "One or more mandatory validations did not pass."
                )
            job = self._transition_owned(
                current,
                status,
                validation_summary=summary,
                evidence_path=self.runner.evidence_path(job_id),
                error_code=error_code,
                error_message=error_message,
                last_error=error_message,
                details={"passed": mandatory_passed, "cancelled": cancelled},
            )
            operations = [event.to_dict() for event in self.jobs.list_events(job_id)]
            finalized = self.runner.finalize_validation(
                job,
                manifest,
                execution,
                operations,
            )
            verification = dict(finalized.verification)
            self.jobs.record_event(job_id, "evidence_finalized", verification)
            result = {
                "job_id": job_id,
                **summary,
                "evidence_path": str(finalized.evidence_path),
                "evidence_verified": bool(verification.get("valid", verification.get("ok", False))),
            }
            if idempotency_key is not None:
                self.jobs.complete_idempotent_operation(
                    job_id,
                    "validate",
                    idempotency_key,
                    result,
                )
            return result
        except Exception as exc:
            with suppress(Exception):
                current = self.jobs.get(job_id)
                if current.status in LEASE_GUARDED_STATUSES:
                    if current.cancel_requested:
                        self._cancel_owned_job(
                            current,
                            phase="validating",
                            message="Cancellation was observed at a validation boundary.",
                        )
                    else:
                        self._transition_owned(
                            current,
                            JobStatus.RECOVERY_REQUIRED,
                            recovery_reason="Validation stopped before a terminal result was recorded.",
                            last_error=str(exc),
                            details={
                                "phase": "validating",
                                "error_code": getattr(exc, "code", None),
                            },
                        )
            if idempotency_key is not None:
                with suppress(Exception):
                    self.jobs.fail_idempotent_operation(
                        job_id,
                        "validate",
                        idempotency_key,
                        error_code=getattr(exc, "code", "VALIDATION_INTERRUPTED"),
                        error_message=str(exc),
                    )
            raise

    def get_evidence(self, job_id: str) -> dict[str, Any]:
        job = self._job(job_id)
        return self.runner.get_evidence(job)

    def publish_local_branch(
        self,
        job_id: str,
        *,
        explicit: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        job, manifest = self._job_context(job_id)
        controller = GitController(manifest.local_path)
        repository = _dict(controller.inspect())
        decision = self.policy.decide(
            "local_commit",
            manifest,
            explicit=explicit,
            default_branch=repository.get("default_branch"),
        )
        self._require(decision)
        if idempotency_key is not None:
            operation_record = self.jobs.begin_idempotent_operation(
                job_id,
                "publish",
                idempotency_key,
            )
            replay = self._idempotent_replay(operation_record)
            if replay is not None:
                return replay
        try:
            if job.status != JobStatus.COMPLETED:
                raise ServiceError(
                    "Only successfully validated jobs may be published", code="JOB_NOT_VALIDATED"
                )
            diff = self.runner.generate_patch(job_id)
            if not repository.get("is_repository"):
                raise ServiceError(
                    "Registered source is not a Git repository", code="GIT_REPOSITORY_INVALID"
                )
            if repository.get("dirty") or repository.get("staged_paths"):
                raise ServiceError(
                    "Source repository must be clean before applying a validated workspace patch",
                    code="DIRTY_SOURCE_REPOSITORY",
                    details={
                        "changed_paths": repository.get("changed_paths", []),
                        "staged_paths": repository.get("staged_paths", []),
                    },
                )
            if diff.get("stale_source_warning"):
                raise ServiceError(
                    "Source changed after workspace creation; publication would be stale",
                    code="STALE_SOURCE",
                    details=diff.get("stale_source_details", {}),
                )
        except Exception as exc:
            if idempotency_key is not None:
                with suppress(Exception):
                    self.jobs.fail_idempotent_operation(
                        job_id,
                        "publish",
                        idempotency_key,
                        error_code=getattr(exc, "code", "PUBLICATION_REFUSED"),
                        error_message=str(exc),
                    )
            raise
        changed: list[str] = []
        leased_job: Job | None = None
        try:
            leased_job = self._claim(job_id, JobStatus.COMPLETED)
            leased_job = self._transition_owned(
                leased_job,
                JobStatus.PUBLISHING,
                details={"changed_count": len(diff.get("files_changed", []))},
            )
            for item in diff.get("files_changed", []):
                self._heartbeat(leased_job)
                if self.jobs.get(job_id).cancel_requested:
                    raise ServiceError(
                        "Cancellation was observed during publication",
                        code="JOB_CANCELLED",
                    )
                relative = item["path"] if isinstance(item, Mapping) else str(item)
                change_type = (
                    item.get("change_type", item.get("status"))
                    if isinstance(item, Mapping)
                    else None
                )
                if change_type in {"deleted", "delete", "D"}:
                    raise ServiceError(
                        "Deletion publication is prohibited in this MVP",
                        code="ACTION_PROHIBITED",
                    )
                source = Path(job.workspace_path, *relative.split("/"))
                destination = Path(manifest.local_path, *relative.split("/"))
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
                changed.append(relative)
            self._heartbeat(leased_job)
            if self.jobs.get(job_id).cancel_requested:
                raise ServiceError(
                    "Cancellation was observed before the Git commit",
                    code="JOB_CANCELLED",
                )
            result = controller.publish_local_branch(
                job_id,
                changed,
                commit_message=f"Apply UPG job {job_id}",
                explicit_permission=explicit,
                slug="workspace-change",
            )
            payload = _dict(result)
            completed = self._transition_owned(
                self.jobs.get(job_id),
                JobStatus.COMPLETED,
                details={"publication_succeeded": True},
            )
            self._event(completed.job_id, "local_branch_published", payload)
            self._sync_operations(job_id)
            self.runner.finalize_evidence(job_id)
            if idempotency_key is not None:
                self.jobs.complete_idempotent_operation(
                    job_id,
                    "publish",
                    idempotency_key,
                    payload,
                )
            return payload
        except Exception as exc:
            with suppress(Exception):
                current = self.jobs.get(job_id)
                if current.status in LEASE_GUARDED_STATUSES:
                    if current.cancel_requested and not changed:
                        self._cancel_owned_job(
                            current,
                            phase="publishing",
                            message="Cancellation was observed before source files were copied.",
                        )
                    else:
                        reason = (
                            "Publication stopped after source mutation may have begun; "
                            "manual recovery is required."
                        )
                        self._transition_owned(
                            current,
                            JobStatus.RECOVERY_REQUIRED,
                            recovery_reason=reason,
                            last_error=str(exc),
                            details={"phase": "publishing", "copied_paths": list(changed)},
                        )
            if idempotency_key is not None:
                with suppress(Exception):
                    self.jobs.fail_idempotent_operation(
                        job_id,
                        "publish",
                        idempotency_key,
                        error_code=getattr(exc, "code", "PUBLICATION_INTERRUPTED"),
                        error_message=str(exc),
                    )
            raise


__all__ = ["ControlPlane", "ServiceError"]
