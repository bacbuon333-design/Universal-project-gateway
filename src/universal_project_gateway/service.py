"""Backward-compatible service facade over the control plane and runner."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .config import GatewayConfig
from .control_plane import ControlPlane, ServiceError
from .runner import Runner


class GatewayService:
    """Preserve the v0.1 public API while delegating all behavior.

    CLI, MCP, demo, and existing Python callers continue to construct this
    class. New integrations may depend directly on :class:`ControlPlane` and
    inject a runner that implements the bounded :class:`Runner` contract.
    """

    def __init__(
        self,
        config: GatewayConfig | str | Path | None = None,
        *,
        control_plane: ControlPlane | None = None,
        runner: Runner | None = None,
        worker_id: str | None = None,
        lease_seconds: int = 300,
    ) -> None:
        if control_plane is not None and (
            config is not None
            or runner is not None
            or worker_id is not None
            or lease_seconds != 300
        ):
            raise ValueError(
                "control_plane cannot be combined with config, runner, or lease options"
            )
        self.control_plane = control_plane or ControlPlane(
            config,
            runner=runner,
            worker_id=worker_id,
            lease_seconds=lease_seconds,
        )

    @property
    def config(self) -> GatewayConfig:
        return self.control_plane.config

    @property
    def registry(self) -> Any:
        return self.control_plane.registry

    @property
    def jobs(self) -> Any:
        return self.control_plane.jobs

    @property
    def policy(self) -> Any:
        return self.control_plane.policy

    @property
    def intent(self) -> Any:
        return self.control_plane.intent

    @property
    def runner(self) -> Runner:
        return self.control_plane.runner

    @property
    def workspaces(self) -> Any:
        """Compatibility access to the local runner's workspace manager."""

        return self.runner.workspaces  # type: ignore[attr-defined]

    @property
    def evidence(self) -> Any:
        """Compatibility access to the local runner's evidence ledger."""

        return self.runner.evidence  # type: ignore[attr-defined]

    def get_status(self) -> dict[str, Any]:
        return self.control_plane.get_status()

    def list_adapters(self) -> list[dict[str, Any]]:
        return self.control_plane.list_adapters()

    def register_project(self, manifest_path: str | Path) -> dict[str, Any]:
        return self.control_plane.register_project(manifest_path)

    def list_projects(self) -> list[dict[str, Any]]:
        return self.control_plane.list_projects()

    def get_project(self, project_id: str) -> dict[str, Any]:
        return self.control_plane.get_project(project_id)

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
        return self.control_plane.prepare_task(
            project_id,
            request,
            target_paths=target_paths,
            requested_operation=requested_operation,
            publication_preference=publication_preference,
            idempotency_key=idempotency_key,
        )

    def inspect_job(self, job_id: str) -> dict[str, Any]:
        return self.control_plane.inspect_job(job_id)

    def request_cancellation(self, job_id: str, *, reason: str | None = None) -> dict[str, Any]:
        return self.control_plane.request_cancellation(job_id, reason=reason)

    def recover_expired_job(self, job_id: str) -> dict[str, Any]:
        return self.control_plane.recover_expired_job(job_id)

    def list_workspace_files(self, job_id: str, path: str = ".") -> dict[str, Any]:
        return self.control_plane.list_workspace_files(job_id, path)

    def search_workspace(
        self,
        job_id: str,
        query: str,
        *,
        path: str = ".",
        max_results: int = 100,
    ) -> dict[str, Any]:
        return self.control_plane.search_workspace(
            job_id,
            query,
            path=path,
            max_results=max_results,
        )

    def read_workspace_file(self, job_id: str, path: str) -> dict[str, Any]:
        return self.control_plane.read_workspace_file(job_id, path)

    def write_workspace_file(
        self,
        job_id: str,
        path: str,
        content: str,
        *,
        create: bool = False,
    ) -> dict[str, Any]:
        return self.control_plane.write_workspace_file(
            job_id,
            path,
            content,
            create=create,
        )

    def replace_workspace_text(
        self,
        job_id: str,
        path: str,
        old: str,
        new: str,
        *,
        max_replacements: int = 100,
    ) -> dict[str, Any]:
        return self.control_plane.replace_workspace_text(
            job_id,
            path,
            old,
            new,
            max_replacements=max_replacements,
        )

    def move_workspace_file(
        self,
        job_id: str,
        source: str,
        destination: str,
    ) -> dict[str, Any]:
        return self.control_plane.move_workspace_file(job_id, source, destination)

    def request_delete(self, job_id: str, path: str) -> dict[str, Any]:
        return self.control_plane.request_delete(job_id, path)

    def get_diff(self, job_id: str) -> dict[str, Any]:
        return self.control_plane.get_diff(job_id)

    def validate(
        self,
        job_id: str,
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self.control_plane.validate(job_id, idempotency_key=idempotency_key)

    def get_evidence(self, job_id: str) -> dict[str, Any]:
        return self.control_plane.get_evidence(job_id)

    def publish_local_branch(
        self,
        job_id: str,
        *,
        explicit: bool = False,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return self.control_plane.publish_local_branch(
            job_id,
            explicit=explicit,
            idempotency_key=idempotency_key,
        )


__all__ = ["GatewayService", "ServiceError"]
