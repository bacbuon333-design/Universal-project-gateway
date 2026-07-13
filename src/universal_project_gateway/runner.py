"""Runner boundary and the current in-process local implementation.

The runner receives validated manifests, persisted jobs, and named actions. It
never accepts a caller-supplied command line or an arbitrary source path.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .config import GatewayConfig
from .evidence import EvidenceLedger
from .models import GatewayError, Job, JobStatus, ProjectManifest, json_ready
from .runtime import create_runtime_adapter
from .sandbox import SandboxBackend, UnsafeLocalSandboxBackend
from .scoped_fs import ScopedWorkspace
from .workspaces import WorkspaceManager


class RunnerError(GatewayError):
    """Stable error raised at the execution-plane boundary."""

    default_code = "RUNNER_ERROR"


def _dict(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(json_ready(value))
    if hasattr(value, "to_dict"):
        return dict(json_ready(value.to_dict()))
    raise TypeError(f"Expected a mapping-like result, got {type(value).__name__}")


@dataclass(frozen=True, slots=True)
class WorkspacePreparation:
    """Workspace and snapshot metadata returned to the control plane."""

    workspace_path: Path
    snapshot: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class ValidationExecution:
    """Unpersisted result of running manifest-declared validation actions."""

    summary: Mapping[str, Any]
    environment: Mapping[str, Any]
    stdout: str
    stderr: str
    cancelled: bool = False
    cancellation_reason: str | None = None


@dataclass(frozen=True, slots=True)
class FinalizedEvidence:
    """Patch and checksum result produced for one terminal validation job."""

    diff: Mapping[str, Any]
    verification: Mapping[str, Any]
    evidence_path: Path


@runtime_checkable
class Runner(Protocol):
    """Execution-plane contract used by :class:`ControlPlane`.

    A runner may prepare only the source described by a validated manifest and
    may execute only the manifest's fixed validation action names.
    """

    def prepare_workspace(self, job_id: str, manifest: ProjectManifest) -> WorkspacePreparation: ...

    def record_preparation(
        self,
        job_id: str,
        *,
        intent: Mapping[str, Any],
        context_pack: Mapping[str, Any],
        snapshot: Mapping[str, Any],
    ) -> Path: ...

    def evidence_path(self, job_id: str) -> Path: ...

    def record_preparation_failure(
        self,
        job: Job,
        *,
        intent: Mapping[str, Any],
        operations: Sequence[Mapping[str, Any]],
        error_code: str,
        message: str,
    ) -> Path: ...

    def record_cancellation(
        self,
        job: Job,
        *,
        operations: Sequence[Mapping[str, Any]],
        phase: str,
        message: str,
    ) -> Path: ...

    def record_task(self, job: Job) -> None: ...

    def record_operations(self, job_id: str, operations: Sequence[Mapping[str, Any]]) -> None: ...

    def list_workspace_files(
        self, job: Job, manifest: ProjectManifest, path: str = "."
    ) -> list[dict[str, Any]]: ...

    def search_workspace(
        self,
        job: Job,
        manifest: ProjectManifest,
        query: str,
        *,
        path: str = ".",
        max_results: int = 100,
    ) -> list[dict[str, Any]]: ...

    def read_workspace_file(
        self, job: Job, manifest: ProjectManifest, path: str
    ) -> tuple[str, dict[str, Any]]: ...

    def write_workspace_file(
        self,
        job: Job,
        manifest: ProjectManifest,
        path: str,
        content: str,
        *,
        create: bool = False,
    ) -> dict[str, Any]: ...

    def replace_workspace_text(
        self,
        job: Job,
        manifest: ProjectManifest,
        path: str,
        old: str,
        new: str,
        *,
        max_replacements: int = 100,
    ) -> dict[str, Any]: ...

    def move_workspace_file(
        self,
        job: Job,
        manifest: ProjectManifest,
        source: str,
        destination: str,
    ) -> dict[str, Any]: ...

    def request_delete(self, job: Job, manifest: ProjectManifest, path: str) -> dict[str, Any]: ...

    def generate_patch(self, job_id: str) -> dict[str, Any]: ...

    def record_patch(self, job_id: str, diff: Mapping[str, Any]) -> None: ...

    def execute_validation(
        self,
        job: Job,
        manifest: ProjectManifest,
        *,
        heartbeat: Callable[[], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> ValidationExecution: ...

    def finalize_validation(
        self,
        job: Job,
        manifest: ProjectManifest,
        execution: ValidationExecution,
        operations: Sequence[Mapping[str, Any]],
    ) -> FinalizedEvidence: ...

    def get_evidence(self, job: Job) -> dict[str, Any]: ...

    def finalize_evidence(self, job_id: str) -> None: ...


class LocalRunner:
    """Current synchronous execution plane using local application isolation.

    This implementation deliberately preserves the MVP behavior. It is not an
    operating-system sandbox and it does not implement remote work. Durable
    lease ownership remains enforced by the Control Plane's job store; the
    callbacks below provide cooperative heartbeat and cancellation boundaries.
    """

    _VALIDATION_METHODS = {
        "install": "install_dependencies",
        "lint": "run_lint",
        "test": "run_tests",
        "build": "run_build",
        "smoke_test": "run_smoke_test",
    }

    def __init__(
        self,
        config: GatewayConfig,
        *,
        sandbox_backend: SandboxBackend | None = None,
    ) -> None:
        self.config = config
        self.workspaces = WorkspaceManager(config.workspaces_root)
        self.evidence = EvidenceLedger(config.artifacts_root)
        self.sandbox_backend = sandbox_backend or UnsafeLocalSandboxBackend()

    @staticmethod
    def _scoped(job: Job, manifest: ProjectManifest, *, max_file_size: int) -> ScopedWorkspace:
        if job.workspace_path is None:
            raise RunnerError("Job has no workspace", code="WORKSPACE_NOT_READY")
        return ScopedWorkspace(
            job.workspace_path,
            manifest.protected_paths,
            max_file_size=max_file_size,
        )

    def prepare_workspace(self, job_id: str, manifest: ProjectManifest) -> WorkspacePreparation:
        snapshot = self.workspaces.create(
            job_id,
            manifest.local_path,
            protected_paths=manifest.protected_paths,
        )
        return WorkspacePreparation(
            workspace_path=self.workspaces.workspace_path(job_id),
            snapshot=_dict(snapshot),
        )

    def record_preparation(
        self,
        job_id: str,
        *,
        intent: Mapping[str, Any],
        context_pack: Mapping[str, Any],
        snapshot: Mapping[str, Any],
    ) -> Path:
        evidence_path = self.evidence.initialize(job_id)
        self.evidence.write(job_id, "intent.json", intent)
        self.evidence.write(job_id, "context_pack.json", context_pack)
        self.evidence.write(job_id, "source_snapshot.json", snapshot)
        return evidence_path

    def evidence_path(self, job_id: str) -> Path:
        return self.evidence.job_path(job_id)

    def record_preparation_failure(
        self,
        job: Job,
        *,
        intent: Mapping[str, Any],
        operations: Sequence[Mapping[str, Any]],
        error_code: str,
        message: str,
    ) -> Path:
        evidence_path = self.evidence.job_path(job.job_id)
        if not evidence_path.exists() or not any(evidence_path.iterdir()):
            self.evidence.initialize(job.job_id)
        self.record_task(job)
        self.evidence.write(job.job_id, "intent.json", intent)
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
        self.record_operations(job.job_id, operations)
        self.evidence.finalize(
            job.job_id,
            final_report={
                "job_id": job.job_id,
                "project_id": job.project_id,
                "success": False,
                "status": "failed",
                "error_code": error_code,
                "message": message,
            },
        )
        return evidence_path

    def record_task(self, job: Job) -> None:
        self.evidence.write(job.job_id, "task.json", job.to_dict())

    def record_cancellation(
        self,
        job: Job,
        *,
        operations: Sequence[Mapping[str, Any]],
        phase: str,
        message: str,
    ) -> Path:
        evidence_path = self.evidence.job_path(job.job_id)
        if not evidence_path.exists():
            self.evidence.initialize(job.job_id)
        self.record_task(job)
        self.record_operations(job.job_id, operations)
        self.evidence.write(
            job.job_id,
            "validation.json",
            {
                "passed": False,
                "cancelled": True,
                "overall_status": "not_run",
                "checks": [],
                "counts": {"passed": 0, "failed": 0, "skipped": 0, "not_run": 1},
            },
        )
        self.evidence.finalize(
            job.job_id,
            final_report={
                "job_id": job.job_id,
                "project_id": job.project_id,
                "success": False,
                "status": JobStatus.CANCELLED.value,
                "phase": phase,
                "message": message,
                "evidence_path": str(evidence_path),
            },
        )
        return evidence_path

    def record_operations(self, job_id: str, operations: Sequence[Mapping[str, Any]]) -> None:
        self.evidence.write(job_id, "operations.json", list(operations))

    def list_workspace_files(
        self, job: Job, manifest: ProjectManifest, path: str = "."
    ) -> list[dict[str, Any]]:
        scoped = self._scoped(job, manifest, max_file_size=self.config.max_text_file_bytes)
        return scoped.list_dir(path)

    def search_workspace(
        self,
        job: Job,
        manifest: ProjectManifest,
        query: str,
        *,
        path: str = ".",
        max_results: int = 100,
    ) -> list[dict[str, Any]]:
        scoped = self._scoped(job, manifest, max_file_size=self.config.max_text_file_bytes)
        return scoped.search(query, path, max_results=max_results)

    def read_workspace_file(
        self, job: Job, manifest: ProjectManifest, path: str
    ) -> tuple[str, dict[str, Any]]:
        scoped = self._scoped(job, manifest, max_file_size=self.config.max_text_file_bytes)
        return scoped.read_text(path), scoped.metadata(path)

    def write_workspace_file(
        self,
        job: Job,
        manifest: ProjectManifest,
        path: str,
        content: str,
        *,
        create: bool = False,
    ) -> dict[str, Any]:
        scoped = self._scoped(job, manifest, max_file_size=self.config.max_text_file_bytes)
        return scoped.create_text(path, content) if create else scoped.replace_text(path, content)

    def replace_workspace_text(
        self,
        job: Job,
        manifest: ProjectManifest,
        path: str,
        old: str,
        new: str,
        *,
        max_replacements: int = 100,
    ) -> dict[str, Any]:
        scoped = self._scoped(job, manifest, max_file_size=self.config.max_text_file_bytes)
        return scoped.replace_in_text(
            path,
            old,
            new,
            max_replacements=max_replacements,
        )

    def move_workspace_file(
        self,
        job: Job,
        manifest: ProjectManifest,
        source: str,
        destination: str,
    ) -> dict[str, Any]:
        scoped = self._scoped(job, manifest, max_file_size=self.config.max_text_file_bytes)
        return scoped.move(source, destination)

    def request_delete(self, job: Job, manifest: ProjectManifest, path: str) -> dict[str, Any]:
        scoped = self._scoped(job, manifest, max_file_size=self.config.max_text_file_bytes)
        return scoped.request_delete(path)

    def generate_patch(self, job_id: str) -> dict[str, Any]:
        return _dict(self.workspaces.diff(job_id))

    def record_patch(self, job_id: str, diff: Mapping[str, Any]) -> None:
        self.evidence.write(job_id, "patch.diff", diff.get("patch", ""))
        self.evidence.write(job_id, "files_changed.json", diff.get("files_changed", []))

    @staticmethod
    def _result_passed(result: Mapping[str, Any]) -> bool:
        status = str(result.get("status", "")).casefold()
        if status in {"passed", "pass", "success"}:
            return True
        if status in {"skipped", "not-run", "not_run", "failed", "error", "timeout"}:
            return False
        return result.get("returncode", result.get("return_code")) == 0

    def execute_validation(
        self,
        job: Job,
        manifest: ProjectManifest,
        *,
        heartbeat: Callable[[], None] | None = None,
        should_cancel: Callable[[], bool] | None = None,
    ) -> ValidationExecution:
        if job.workspace_path is None:
            raise RunnerError("Job has no workspace", code="WORKSPACE_NOT_READY")
        sandbox_handle = self.sandbox_backend.prepare(
            job.workspace_path,
            snapshot={
                "job_id": job.job_id,
                "project_id": job.project_id,
                "source_revision": job.source_revision,
            },
        )
        try:
            adapter = create_runtime_adapter(
                manifest.project_type,
                job.workspace_path,
                manifest.commands,
                timeout_seconds=self.config.command_timeout_seconds,
                sandbox_backend=self.sandbox_backend,
                sandbox_handle=sandbox_handle,
                should_cancel=should_cancel,
            )
            environment = _dict(adapter.inspect_environment())
            results, stdout_parts, stderr_parts, cancelled, cancellation_reason = (
                self._execute_validation_actions(
                    adapter,
                    manifest,
                    heartbeat=heartbeat,
                    should_cancel=should_cancel,
                )
            )
        finally:
            self.sandbox_backend.destroy(sandbox_handle)
        environment["sandbox"] = _dict(self.sandbox_backend.collect(sandbox_handle))

        mandatory_passed = (
            bool(results) and not cancelled and all(result["passed"] for result in results)
        )
        summary = {
            "passed": mandatory_passed,
            "mandatory": list(manifest.validation_requirements),
            "checks": results,
            "counts": {
                "passed": sum(1 for result in results if result["passed"]),
                "failed": sum(
                    1 for result in results if str(result.get("status", "")).casefold() == "failed"
                ),
                "skipped": sum(
                    1
                    for result in results
                    if str(result.get("status", "")).casefold() == "skipped"
                ),
                "not_run": sum(
                    1
                    for result in results
                    if str(result.get("status", "")).casefold() in {"not-run", "not_run"}
                ),
            },
        }
        if cancelled:
            summary["cancelled"] = True
            summary["cancellation_reason"] = cancellation_reason
        return ValidationExecution(
            summary=summary,
            environment=environment,
            stdout="\n\n".join(stdout_parts),
            stderr="\n\n".join(stderr_parts),
            cancelled=cancelled,
            cancellation_reason=cancellation_reason,
        )

    def _execute_validation_actions(
        self,
        adapter: Any,
        manifest: ProjectManifest,
        *,
        heartbeat: Callable[[], None] | None,
        should_cancel: Callable[[], bool] | None,
    ) -> tuple[list[dict[str, Any]], list[str], list[str], bool, str | None]:
        results: list[dict[str, Any]] = []
        stdout_parts: list[str] = []
        stderr_parts: list[str] = []
        requirements = list(manifest.validation_requirements)
        cancelled = False
        cancellation_reason: str | None = None
        for index, action in enumerate(requirements):
            if should_cancel is not None and should_cancel():
                cancelled = True
                cancellation_reason = "Cancellation was observed before the next validation action."
                for remaining in requirements[index:]:
                    results.append(
                        {
                            "action": remaining,
                            "status": "not-run",
                            "passed": False,
                            "message": cancellation_reason,
                        }
                    )
                break
            if heartbeat is not None:
                heartbeat()
            method_name = self._VALIDATION_METHODS.get(action)
            if method_name is None:
                result = {
                    "action": action,
                    "status": "not-run",
                    "passed": False,
                    "message": "No runtime adapter operation exists for this mandatory action.",
                }
            elif action == "install":
                result = _dict(adapter.install_dependencies(enabled=False))
            else:
                result = _dict(getattr(adapter, method_name)())
            result.setdefault("action", action)
            result["passed"] = self._result_passed(result)
            results.append(result)
            if result.get("stdout"):
                stdout_parts.append(f"[{action}]\n{result['stdout']}")
            if result.get("stderr"):
                stderr_parts.append(f"[{action}]\n{result['stderr']}")
            if heartbeat is not None:
                heartbeat()
            if should_cancel is not None and should_cancel():
                cancelled = True
                cancellation_reason = (
                    "Cancellation was observed after a validation action completed. "
                    "The current implementation does not kill an action already in progress."
                )
                for remaining in requirements[index + 1 :]:
                    results.append(
                        {
                            "action": remaining,
                            "status": "not-run",
                            "passed": False,
                            "message": cancellation_reason,
                        }
                    )
                break
        return (
            results,
            stdout_parts,
            stderr_parts,
            cancelled,
            cancellation_reason,
        )

    def finalize_validation(
        self,
        job: Job,
        manifest: ProjectManifest,
        execution: ValidationExecution,
        operations: Sequence[Mapping[str, Any]],
    ) -> FinalizedEvidence:
        summary = dict(execution.summary)
        diff = self.generate_patch(job.job_id)
        self.record_patch(job.job_id, diff)
        self.evidence.write(job.job_id, "validation.json", summary)
        self.evidence.write(job.job_id, "stdout.log", execution.stdout)
        self.evidence.write(job.job_id, "stderr.log", execution.stderr)
        self.evidence.write(job.job_id, "environment.json", execution.environment)
        self.record_task(job)
        self.record_operations(job.job_id, operations)
        evidence_path = self.evidence.job_path(job.job_id)
        self.evidence.finalize(
            job.job_id,
            final_report={
                "job_id": job.job_id,
                "project_id": manifest.project_id,
                "success": bool(summary.get("passed")),
                "status": job.status.value,
                "validation": summary,
                "files_changed": diff.get("files_changed", []),
                "stale_source_warning": diff.get("stale_source_warning"),
                "evidence_path": str(evidence_path),
            },
        )
        verification = _dict(self.evidence.verify(job.job_id))
        return FinalizedEvidence(
            diff=diff,
            verification=verification,
            evidence_path=evidence_path,
        )

    def get_evidence(self, job: Job) -> dict[str, Any]:
        path = job.evidence_path or self.evidence.job_path(job.job_id)
        result = _dict(self.evidence.verify(path))
        verified = bool(result.get("valid", result.get("ok", False)))
        return {
            "job_id": job.job_id,
            "path": str(path),
            "verified": verified,
            "verification": result,
        }

    def finalize_evidence(self, job_id: str) -> None:
        self.evidence.finalize(job_id)


__all__ = [
    "FinalizedEvidence",
    "LocalRunner",
    "Runner",
    "RunnerError",
    "ValidationExecution",
    "WorkspacePreparation",
]
