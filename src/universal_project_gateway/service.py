"""Application service coordinating registry, jobs, workspaces, validation, and evidence."""

from __future__ import annotations

import shutil
from collections.abc import Iterable, Mapping
from contextlib import suppress
from pathlib import Path
from typing import Any

from . import __version__
from .config import GatewayConfig
from .context import ContextCompiler
from .evidence import EvidenceLedger
from .git_controller import GitController
from .intent import IntentCompiler
from .jobs import JobStore
from .models import GatewayError, Job, JobStatus, ProjectManifest, json_ready
from .policy import PolicyEngine
from .registry import ProjectRegistry
from .runtime import create_runtime_adapter
from .scoped_fs import ScopedWorkspace
from .workspaces import WorkspaceManager


class ServiceError(GatewayError):
    """Stable structured error at the Gateway application boundary."""

    default_code = "SERVICE_ERROR"


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(json_ready(value))
    if hasattr(value, "to_dict"):
        return dict(json_ready(value.to_dict()))
    raise TypeError(f"Expected a mapping-like result, got {type(value).__name__}")


class GatewayService:
    """Synchronous local runner with persistent jobs and recoverable evidence."""

    def __init__(self, config: GatewayConfig | str | Path | None = None) -> None:
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
        self.workspaces = WorkspaceManager(config.workspaces_root)
        self.evidence = EvidenceLedger(config.artifacts_root)

    def get_status(self) -> dict[str, Any]:
        return {
            "system_id": "universal-project-gateway",
            "version": __version__,
            "status": "ready",
            "root": str(self.config.root_dir),
            "risk_boundary": {"permittable": ["R0", "R1", "R2", "R3"], "prohibited": ["R4"]},
            "transports": ["stdio", "streamable-http-localhost"],
        }

    def register_project(self, manifest_path: str | Path) -> dict[str, Any]:
        record = self.registry.register(manifest_path)
        return record.to_dict()

    def list_projects(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.registry.list()]

    def get_project(self, project_id: str) -> dict[str, Any]:
        record = self.registry.get(project_id)
        manifest = self.registry.get_manifest(project_id)
        return {"record": record.to_dict(), "manifest": manifest.to_dict(include_metadata=True)}

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

    def prepare_task(
        self,
        project_id: str,
        request: str,
        *,
        target_paths: Iterable[str] = (),
        requested_operation: str | None = None,
        publication_preference: str = "none",
    ) -> dict[str, Any]:
        manifest = self.registry.get_manifest(project_id)
        normalized = self.intent.compile(
            project_id,
            request,
            target_paths=tuple(target_paths),
            requested_operation=requested_operation,
            publication_preference=publication_preference,
            required_validation=manifest.validation_requirements,
        )
        action = "read" if normalized.risk_level.value == "R0" else "write"
        self._require(self.policy.decide(action, manifest))
        job = self.jobs.create(
            project_id,
            request,
            normalized,
            risk_level=normalized.risk_level,
        )
        try:
            snapshot = self.workspaces.create(
                job.job_id,
                manifest.local_path,
                protected_paths=manifest.protected_paths,
            )
            snapshot_data = _dict(snapshot)
            workspace_path = self.workspaces.workspace_path(job.job_id)
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
                target_paths=tuple(target_paths),
                gateway_rules=(
                    "Operate only within the active isolated job workspace.",
                    "Never access protected paths or credentials.",
                    "Run only manifest-declared validation actions.",
                    "R4 actions, merges, force pushes, and deployments are prohibited.",
                ),
            )
            evidence_path = self.evidence.initialize(job.job_id)
            self.evidence.write(job.job_id, "intent.json", normalized.to_dict())
            self.evidence.write(job.job_id, "context_pack.json", context_pack)
            self.evidence.write(job.job_id, "source_snapshot.json", snapshot_data)
            job = self.jobs.transition(
                job.job_id,
                JobStatus.PREPARED,
                evidence_path=evidence_path,
                details={"workspace_path": str(workspace_path)},
            )
            self.evidence.write(job.job_id, "task.json", job.to_dict())
            self._sync_operations(job.job_id)
            return {
                "job": job.to_dict(),
                "intent": normalized.to_dict(),
                "workspace": str(workspace_path),
                "evidence": str(evidence_path),
            }
        except Exception as exc:
            with suppress(Exception):
                evidence_path = self.evidence.job_path(job.job_id)
                if not evidence_path.exists() or not any(evidence_path.iterdir()):
                    self.evidence.initialize(job.job_id)
                failed_job = self.jobs.transition(
                    job.job_id,
                    JobStatus.FAILED,
                    evidence_path=evidence_path,
                    error_code=getattr(exc, "code", "PREPARATION_FAILED"),
                    error_message=str(exc),
                )
                self.evidence.write(job.job_id, "task.json", failed_job.to_dict())
                self.evidence.write(job.job_id, "intent.json", normalized.to_dict())
                self.evidence.write(
                    job.job_id,
                    "validation.json",
                    {
                        "passed": False,
                        "overall_status": "not_run",
                        "checks": [],
                        "counts": {"passed": 0, "failed": 0, "skipped": 0, "not_run": 1},
                    },
                )
                self._sync_operations(job.job_id)
                self.evidence.finalize(
                    job.job_id,
                    final_report={
                        "job_id": job.job_id,
                        "project_id": project_id,
                        "success": False,
                        "status": "failed",
                        "error_code": getattr(exc, "code", "PREPARATION_FAILED"),
                        "message": str(exc),
                    },
                )
            raise

    def inspect_job(self, job_id: str) -> dict[str, Any]:
        job = self._job(job_id)
        return {
            "job": job.to_dict(),
            "events": [event.to_dict() for event in self.jobs.list_events(job_id)],
        }

    def _scoped(self, job_id: str) -> tuple[Job, ProjectManifest, ScopedWorkspace]:
        job = self._job(job_id)
        if job.workspace_path is None:
            raise ServiceError("Job has no workspace", code="WORKSPACE_NOT_READY")
        manifest = self._manifest(job)
        return (
            job,
            manifest,
            ScopedWorkspace(
                job.workspace_path,
                manifest.protected_paths,
                max_file_size=self.config.max_text_file_bytes,
            ),
        )

    def _event(self, job_id: str, event_type: str, details: Mapping[str, Any]) -> None:
        self.jobs.record_event(job_id, event_type, details)
        if self.jobs.get(job_id).status not in {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        }:
            self._sync_operations(job_id)

    def _sync_operations(self, job_id: str) -> None:
        events = [event.to_dict() for event in self.jobs.list_events(job_id)]
        self.evidence.write(job_id, "operations.json", events)

    def list_workspace_files(self, job_id: str, path: str = ".") -> dict[str, Any]:
        _, manifest, scoped = self._scoped(job_id)
        self._require(self.policy.decide("read", manifest, path="README.md" if path == "." else path))
        entries = scoped.list_dir(path)
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
        _, manifest, scoped = self._scoped(job_id)
        self._require(self.policy.decide("read", manifest, path="README.md" if path == "." else path))
        results = scoped.search(query, path, max_results=max_results)
        self._event(
            job_id,
            "workspace_searched",
            {"path": path, "query": query, "result_count": len(results)},
        )
        return {"job_id": job_id, "query": query, "results": results}

    def read_workspace_file(self, job_id: str, path: str) -> dict[str, Any]:
        _, manifest, scoped = self._scoped(job_id)
        self._require(self.policy.decide("read", manifest, path=path))
        content = scoped.read_text(path)
        metadata = scoped.metadata(path)
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
        job, manifest, scoped = self._scoped(job_id)
        if job.status not in {JobStatus.PREPARED, JobStatus.RUNNING}:
            raise ServiceError("Job is not writable in its current state", code="JOB_NOT_WRITABLE")
        self._require(self.policy.decide("write", manifest, path=path))
        result = scoped.create_text(path, content) if create else scoped.replace_text(path, content)
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
        job, manifest, scoped = self._scoped(job_id)
        if job.status not in {JobStatus.PREPARED, JobStatus.RUNNING}:
            raise ServiceError("Job is not writable in its current state", code="JOB_NOT_WRITABLE")
        self._require(self.policy.decide("write", manifest, path=path))
        result = scoped.replace_in_text(path, old, new, max_replacements=max_replacements)
        self._event(job_id, "workspace_text_replaced", result)
        return {"job_id": job_id, **result}

    def move_workspace_file(self, job_id: str, source: str, destination: str) -> dict[str, Any]:
        job, manifest, scoped = self._scoped(job_id)
        if job.status not in {JobStatus.PREPARED, JobStatus.RUNNING}:
            raise ServiceError("Job is not writable in its current state", code="JOB_NOT_WRITABLE")
        self._require(self.policy.decide("write", manifest, path=source))
        self._require(self.policy.decide("write", manifest, path=destination))
        result = scoped.move(source, destination)
        self._event(job_id, "workspace_file_moved", result)
        return {"job_id": job_id, **result}

    def request_delete(self, job_id: str, path: str) -> dict[str, Any]:
        job, _, scoped = self._scoped(job_id)
        request = scoped.request_delete(path)
        self._event(job_id, "deletion_requested", request)
        if job.status == JobStatus.PREPARED:
            self.jobs.transition(
                job_id,
                JobStatus.RUNNING,
                details={"operation": "request_delete", "executed": False},
            )
        if job.status in {JobStatus.PREPARED, JobStatus.RUNNING}:
            self.jobs.transition(
                job_id,
                JobStatus.WAITING_FOR_APPROVAL,
                details={"request_id": request["request_id"], "executed": False},
            )
            self._sync_operations(job_id)
        return request

    def get_diff(self, job_id: str) -> dict[str, Any]:
        job, _, _ = self._scoped(job_id)
        diff = self.workspaces.diff(job_id)
        payload = _dict(diff)
        if job.status not in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
            self.evidence.write(job_id, "patch.diff", payload.get("patch", ""))
            self.evidence.write(job_id, "files_changed.json", payload.get("files_changed", []))
            self._event(
                job_id,
                "workspace_diff_computed",
                {"changed_count": len(payload.get("files_changed", [])), "stale_source": payload.get("stale_source_warning")},
            )
        return {"job_id": job_id, **payload}

    @staticmethod
    def _result_passed(result: Mapping[str, Any]) -> bool:
        status = str(result.get("status", "")).casefold()
        if status in {"passed", "pass", "success"}:
            return True
        if status in {"skipped", "not-run", "not_run", "failed", "error", "timeout"}:
            return False
        return result.get("returncode", result.get("return_code")) == 0

    def validate(self, job_id: str) -> dict[str, Any]:
        job, manifest, _ = self._scoped(job_id)
        if job.status == JobStatus.COMPLETED and job.validation_summary is not None:
            return {"job_id": job_id, **dict(job.validation_summary)}
        if job.status != JobStatus.PREPARED:
            raise ServiceError("Only a prepared job can be validated", code="INVALID_JOB_STATE")
        self._require(self.policy.decide("validate", manifest))
        job = self.jobs.transition(job_id, JobStatus.RUNNING, details={"actions": list(manifest.validation_requirements)})
        adapter = create_runtime_adapter(
            manifest.project_type,
            job.workspace_path,
            manifest.commands,
            timeout_seconds=self.config.command_timeout_seconds,
        )
        environment = _dict(adapter.inspect_environment())
        results: list[dict[str, Any]] = []
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        method_names = {
            "install": "install_dependencies",
            "lint": "run_lint",
            "test": "run_tests",
            "build": "run_build",
            "smoke_test": "run_smoke_test",
        }
        for action in manifest.validation_requirements:
            if action not in method_names:
                result = {
                    "action": action,
                    "status": "not-run",
                    "passed": False,
                    "message": "No runtime adapter operation exists for this mandatory action.",
                }
            elif action == "install":
                result = _dict(adapter.install_dependencies(enabled=False))
            else:
                self._require(self.policy.decide(action, manifest))
                result = _dict(getattr(adapter, method_names[action])())
            result.setdefault("action", action)
            result["passed"] = self._result_passed(result)
            results.append(result)
            if result.get("stdout"):
                stdout_parts.append(f"[{action}]\n{result['stdout']}")
            if result.get("stderr"):
                stderr_parts.append(f"[{action}]\n{result['stderr']}")

        mandatory_passed = bool(results) and all(result["passed"] for result in results)
        summary = {
            "passed": mandatory_passed,
            "mandatory": list(manifest.validation_requirements),
            "checks": results,
            "counts": {
                "passed": sum(1 for result in results if result["passed"]),
                "failed": sum(1 for result in results if str(result.get("status", "")).casefold() == "failed"),
                "skipped": sum(1 for result in results if str(result.get("status", "")).casefold() == "skipped"),
                "not_run": sum(1 for result in results if str(result.get("status", "")).casefold() in {"not-run", "not_run"}),
            },
        }
        diff = _dict(self.workspaces.diff(job_id))
        self.evidence.write(job_id, "patch.diff", diff.get("patch", ""))
        self.evidence.write(job_id, "files_changed.json", diff.get("files_changed", []))
        self.evidence.write(job_id, "validation.json", summary)
        self.evidence.write(job_id, "stdout.log", "\n\n".join(stdout_parts))
        self.evidence.write(job_id, "stderr.log", "\n\n".join(stderr_parts))
        self.evidence.write(job_id, "environment.json", environment)
        status = JobStatus.COMPLETED if mandatory_passed else JobStatus.FAILED
        job = self.jobs.transition(
            job_id,
            status,
            validation_summary=summary,
            evidence_path=self.evidence.job_path(job_id),
            error_code=None if mandatory_passed else "VALIDATION_FAILED",
            error_message=None if mandatory_passed else "One or more mandatory validations did not pass.",
            details={"passed": mandatory_passed},
        )
        final_report = {
            "job_id": job_id,
            "project_id": manifest.project_id,
            "success": mandatory_passed,
            "status": job.status.value,
            "validation": summary,
            "files_changed": diff.get("files_changed", []),
            "stale_source_warning": diff.get("stale_source_warning"),
            "evidence_path": str(self.evidence.job_path(job_id)),
        }
        self.evidence.write(job_id, "task.json", job.to_dict())
        self._sync_operations(job_id)
        self.evidence.finalize(job_id, final_report=final_report)
        verification = _dict(self.evidence.verify(job_id))
        self.jobs.record_event(job_id, "evidence_finalized", verification)
        return {
            "job_id": job_id,
            **summary,
            "evidence_path": str(self.evidence.job_path(job_id)),
            "evidence_verified": bool(verification.get("valid", verification.get("ok", False))),
        }

    def get_evidence(self, job_id: str) -> dict[str, Any]:
        job = self._job(job_id)
        path = job.evidence_path or self.evidence.job_path(job_id)
        result = _dict(self.evidence.verify(path))
        verified = bool(result.get("valid", result.get("ok", False)))
        return {"job_id": job_id, "path": str(path), "verified": verified, "verification": result}

    def publish_local_branch(self, job_id: str, *, explicit: bool = False) -> dict[str, Any]:
        job, manifest, _ = self._scoped(job_id)
        controller = GitController(manifest.local_path)
        repository = _dict(controller.inspect())
        decision = self.policy.decide(
            "local_commit",
            manifest,
            explicit=explicit,
            default_branch=repository.get("default_branch"),
        )
        self._require(decision)
        if job.status != JobStatus.COMPLETED:
            raise ServiceError("Only successfully validated jobs may be published", code="JOB_NOT_VALIDATED")
        diff = _dict(self.workspaces.diff(job_id))
        if not repository.get("is_repository"):
            raise ServiceError("Registered source is not a Git repository", code="GIT_REPOSITORY_INVALID")
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
        changed: list[str] = []
        for item in diff.get("files_changed", []):
            relative = item["path"] if isinstance(item, Mapping) else str(item)
            change_type = item.get("change_type", item.get("status")) if isinstance(item, Mapping) else None
            if change_type in {"deleted", "delete", "D"}:
                raise ServiceError("Deletion publication is prohibited in this MVP", code="ACTION_PROHIBITED")
            source = Path(job.workspace_path, *relative.split("/"))
            destination = Path(manifest.local_path, *relative.split("/"))
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            changed.append(relative)
        result = controller.publish_local_branch(
            job_id,
            changed,
            commit_message=f"Apply UPG job {job_id}",
            explicit_permission=explicit,
            slug="workspace-change",
        )
        payload = _dict(result)
        self._event(job_id, "local_branch_published", payload)
        self._sync_operations(job_id)
        self.evidence.finalize(job_id)
        return payload


__all__ = ["GatewayService", "ServiceError"]
