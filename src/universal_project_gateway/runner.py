"""Runner boundary and the current in-process local implementation.

The runner receives validated manifests, persisted jobs, and named actions. It
never accepts a caller-supplied command line or an arbitrary source path.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from .config import GatewayConfig
from .contracts import ADAPTER_CONTRACT_VERSION, EXECUTION_CONTRACT_VERSION
from .evidence import EvidenceLedger
from .models import GatewayError, Job, JobStatus, ProjectManifest, json_ready
from .runtime import AdapterRegistry, AdapterResolution, built_in_adapter_registry
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


def _sandbox_execution_event(value: Any) -> dict[str, Any]:
    """Select stable sandbox facts without hashing host-specific argv or cwd."""

    if not isinstance(value, Mapping):
        return {"status": "invalid"}
    sandbox = value.get("sandbox")
    metadata = sandbox if isinstance(sandbox, Mapping) else {}
    return {
        "contract_version": value.get("contract_version", EXECUTION_CONTRACT_VERSION),
        "runtime_action": value.get("action"),
        "status": value.get("status"),
        "return_code": value.get("returncode"),
        "timeout_seconds": value.get("timeout_seconds"),
        "timed_out": bool(value.get("timed_out", False)),
        "cancelled": bool(value.get("cancelled", False)),
        "shell_disabled": bool(metadata.get("shell_disabled", False)),
        "environment_filtered": bool(metadata.get("environment_filtered", False)),
        "network_policy": metadata.get("network_policy", "unrestricted"),
        "network_policy_enforced": bool(metadata.get("network_policy_enforced", False)),
    }


def _project_intelligence_reference(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    schema_version = value.get("schema_version")
    cache_hash = value.get("cache_hash")
    source_fingerprint = value.get("source_fingerprint")
    if not all(isinstance(item, str) and item for item in (schema_version, cache_hash)):
        return {}
    result = {"schema_version": schema_version, "cache_hash": cache_hash}
    if isinstance(source_fingerprint, str) and source_fingerprint:
        result["source_fingerprint"] = source_fingerprint
    return result


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

    def record_evidence_event(
        self,
        job_id: str,
        project_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        actor: str,
    ) -> Mapping[str, Any]: ...

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

    def list_adapters(self) -> list[dict[str, Any]]: ...


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
        adapter_registry: AdapterRegistry | None = None,
    ) -> None:
        self.config = config
        self.workspaces = WorkspaceManager(config.workspaces_root)
        self.evidence = EvidenceLedger(config.artifacts_root)
        self.sandbox_backend = sandbox_backend or UnsafeLocalSandboxBackend()
        self.adapter_registry = adapter_registry or built_in_adapter_registry()

    def list_adapters(self) -> list[dict[str, Any]]:
        return [capability.to_dict() for capability in self.adapter_registry.list_capabilities()]

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
        project_id = str(intent.get("project_id", "unknown-project"))
        intelligence = _project_intelligence_reference(
            context_pack.get("project_intelligence")
        )
        self.record_evidence_event(
            job_id,
            project_id,
            "workspace_prepared",
            {
                "source_commit": snapshot.get("source_revision"),
                "file_count": len(snapshot.get("files", [])),
                "omitted_path_count": len(snapshot.get("omitted_paths", [])),
                "project_intelligence": intelligence,
            },
            actor="local_runner",
        )
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
        self.record_evidence_event(
            job.job_id,
            job.project_id,
            "job_failed",
            {
                "phase": "preparing",
                "status": job.status.value,
                "error_code": error_code,
            },
            actor="control_plane",
        )
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
        self.record_evidence_event(
            job.job_id,
            job.project_id,
            "job_cancelled",
            {"phase": phase, "status": job.status.value},
            actor="control_plane",
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

    def record_evidence_event(
        self,
        job_id: str,
        project_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        actor: str,
    ) -> Mapping[str, Any]:
        return self.evidence.append_event(
            job_id,
            project_id,
            event_type,
            payload,
            actor=actor,
        )

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
        intelligence = self._read_project_intelligence_reference(job.job_id)
        resolutions = [
            self.adapter_registry.resolve(manifest, action)
            for action in manifest.validation_requirements
        ]
        resolution_payload = [resolution.to_dict() for resolution in resolutions]
        self.record_evidence_event(
            job.job_id,
            job.project_id,
            "validation_started",
            {
                "actions": list(manifest.validation_requirements),
                "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
                "adapter_resolutions": resolution_payload,
                "sandbox_backend_id": self.sandbox_backend.backend_id,
                "sandbox_safety_level": self.sandbox_backend.safety_level,
                "project_intelligence": intelligence,
            },
            actor="local_runner",
        )
        sandbox_handle = self.sandbox_backend.prepare(
            job.workspace_path,
            snapshot={
                "job_id": job.job_id,
                "project_id": job.project_id,
                "source_revision": job.source_revision,
            },
        )
        try:
            adapters: dict[str, Any] = {}
            resolution_by_action: dict[str, AdapterResolution] = {}
            inspections: dict[str, dict[str, Any]] = {}
            for resolution in resolutions:
                adapter = adapters.get(resolution.adapter.adapter_id)
                if adapter is None:
                    adapter = self.adapter_registry.create(
                        resolution,
                        job.workspace_path,
                        manifest.commands,
                        timeout_seconds=self.config.command_timeout_seconds,
                        sandbox_backend=self.sandbox_backend,
                        sandbox_handle=sandbox_handle,
                        should_cancel=should_cancel,
                    )
                    adapters[resolution.adapter.adapter_id] = adapter
                    inspections[resolution.adapter.adapter_id] = _dict(
                        adapter.inspect_environment()
                    )
                resolution_by_action[resolution.runtime_action] = resolution
            environment = (
                dict(inspections[resolutions[0].adapter.adapter_id]) if resolutions else {}
            )
            environment["adapter_registry"] = {
                "contract_version": ADAPTER_CONTRACT_VERSION,
                "resolved": resolution_payload,
                "inspections": inspections,
            }
            environment["project_intelligence"] = intelligence
            results, stdout_parts, stderr_parts, cancelled, cancellation_reason = (
                self._execute_validation_actions(
                    adapters,
                    resolution_by_action,
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
            "contract_version": EXECUTION_CONTRACT_VERSION,
            "adapter_contract_version": ADAPTER_CONTRACT_VERSION,
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
            "project_intelligence": intelligence,
        }
        if cancelled:
            summary["cancelled"] = True
            summary["cancellation_reason"] = cancellation_reason
        sandbox = environment["sandbox"]
        executions = sandbox.get("executions", []) if isinstance(sandbox, Mapping) else []
        self.record_evidence_event(
            job.job_id,
            job.project_id,
            "sandbox_execution_collected",
            {
                "backend_id": sandbox.get("backend_id", self.sandbox_backend.backend_id),
                "safety_level": sandbox.get(
                    "safety_level", self.sandbox_backend.safety_level
                ),
                "executions": [_sandbox_execution_event(item) for item in executions],
            },
            actor="sandbox_backend",
        )
        self.record_evidence_event(
            job.job_id,
            job.project_id,
            "validation_completed",
            {
                "passed": mandatory_passed,
                "cancelled": cancelled,
                "counts": dict(summary["counts"]),
                "adapter_resolutions": resolution_payload,
                "project_intelligence": intelligence,
            },
            actor="local_runner",
        )
        return ValidationExecution(
            summary=summary,
            environment=environment,
            stdout="\n\n".join(stdout_parts),
            stderr="\n\n".join(stderr_parts),
            cancelled=cancelled,
            cancellation_reason=cancellation_reason,
        )

    def _read_project_intelligence_reference(self, job_id: str) -> dict[str, Any]:
        path = self.evidence.job_path(job_id) / "context_pack.json"
        try:
            if path.stat().st_size > self.config.context_max_bytes * 2:
                return {}
            context_pack = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return {}
        if not isinstance(context_pack, Mapping):
            return {}
        return _project_intelligence_reference(context_pack.get("project_intelligence"))

    def _execute_validation_actions(
        self,
        adapters: Mapping[str, Any],
        resolutions: Mapping[str, AdapterResolution],
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
            resolution = resolutions[action]
            adapter_metadata = {
                **resolution.adapter.to_dict(),
                "resolved_capability": resolution.capability,
                "runtime_action": action,
            }
            if should_cancel is not None and should_cancel():
                cancelled = True
                cancellation_reason = "Cancellation was observed before the next validation action."
                for remaining in requirements[index:]:
                    results.append(
                        {
                            "contract_version": EXECUTION_CONTRACT_VERSION,
                            "action": remaining,
                            "status": "not-run",
                            "passed": False,
                            "message": cancellation_reason,
                            "adapter": {
                                **resolutions[remaining].adapter.to_dict(),
                                "resolved_capability": resolutions[remaining].capability,
                                "runtime_action": remaining,
                            },
                        }
                    )
                break
            if heartbeat is not None:
                heartbeat()
            method_name = self._VALIDATION_METHODS.get(action)
            adapter = adapters[resolution.adapter.adapter_id]
            if method_name is None:
                result = {
                    "contract_version": EXECUTION_CONTRACT_VERSION,
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
            result.setdefault("contract_version", EXECUTION_CONTRACT_VERSION)
            result["adapter"] = adapter_metadata
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
                            "contract_version": EXECUTION_CONTRACT_VERSION,
                            "action": remaining,
                            "status": "not-run",
                            "passed": False,
                            "message": cancellation_reason,
                            "adapter": {
                                **resolutions[remaining].adapter.to_dict(),
                                "resolved_capability": resolutions[remaining].capability,
                                "runtime_action": remaining,
                            },
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
        self.record_evidence_event(
            job.job_id,
            job.project_id,
            "patch_generated",
            {
                "changed_count": len(diff.get("files_changed", [])),
                "changed_paths": [
                    item.get("path")
                    for item in diff.get("files_changed", [])
                    if isinstance(item, Mapping) and isinstance(item.get("path"), str)
                ],
                "stale_source": bool(diff.get("stale_source_warning")),
            },
            actor="local_runner",
        )
        self.evidence.write(job.job_id, "validation.json", summary)
        self.evidence.write(job.job_id, "stdout.log", execution.stdout)
        self.evidence.write(job.job_id, "stderr.log", execution.stderr)
        self.evidence.write(job.job_id, "environment.json", execution.environment)
        self.record_task(job)
        self.record_operations(job.job_id, operations)
        self.record_evidence_event(
            job.job_id,
            job.project_id,
            f"job_{job.status.value}",
            {
                "status": job.status.value,
                "success": bool(summary.get("passed")),
                "error_code": job.error_code,
            },
            actor="control_plane",
        )
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
