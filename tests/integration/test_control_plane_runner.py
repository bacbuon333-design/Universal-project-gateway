from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.control_plane import ControlPlane
from universal_project_gateway.evidence import EVIDENCE_FILES
from universal_project_gateway.models import Job, ProjectManifest
from universal_project_gateway.runner import (
    LocalRunner,
    Runner,
    ValidationExecution,
    WorkspacePreparation,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class RecordingLocalRunner(LocalRunner):
    """Local runner test double that records control-plane delegation."""

    def __init__(self, config: GatewayConfig) -> None:
        super().__init__(config)
        self.prepared_jobs: list[str] = []
        self.validated_jobs: list[str] = []

    def prepare_workspace(self, job_id: str, manifest: ProjectManifest) -> WorkspacePreparation:
        self.prepared_jobs.append(job_id)
        return super().prepare_workspace(job_id, manifest)

    def execute_validation(self, job: Job, manifest: ProjectManifest) -> ValidationExecution:
        self.validated_jobs.append(job.job_id)
        return super().execute_validation(job, manifest)


def _fixture_control_plane(
    tmp_path: Path,
    *,
    recording: bool = False,
) -> tuple[ControlPlane, LocalRunner, Path]:
    source = tmp_path / "source" / "python_demo"
    shutil.copytree(REPOSITORY_ROOT / "fixtures" / "python_demo", source)
    config = GatewayConfig.from_root(tmp_path / "gateway")
    runner = RecordingLocalRunner(config) if recording else LocalRunner(config)
    control_plane = ControlPlane(config, runner=runner)
    control_plane.register_project(source / "PROJECT_MANIFEST.yaml")
    return control_plane, runner, source


def test_control_plane_prepares_upg_self_management_job(tmp_path: Path) -> None:
    base = GatewayConfig.from_root(REPOSITORY_ROOT)
    config = replace(
        base,
        registry_path=tmp_path / "var" / "registry" / "projects.yaml",
        database_path=tmp_path / "var" / "gateway.db",
        workspaces_root=tmp_path / "workspaces" / "jobs",
        artifacts_root=tmp_path / "artifacts" / "jobs",
    )
    control_plane = ControlPlane(config)
    source_before = (REPOSITORY_ROOT / "PROJECT_MANIFEST.yaml").read_bytes()

    prepared = control_plane.prepare_task(
        "universal-project-gateway",
        "Inspect the control-plane and runner boundary.",
        target_paths=[
            "src/universal_project_gateway/control_plane.py",
            "src/universal_project_gateway/runner.py",
        ],
        requested_operation="inspect",
    )

    workspace = Path(prepared["workspace"])
    assert prepared["job"]["status"] == "prepared"
    assert prepared["intent"]["risk_level"] == "R0"
    assert workspace.parent.parent == config.workspaces_root
    assert (workspace / "src" / "universal_project_gateway" / "control_plane.py").is_file()
    assert (workspace / "src" / "universal_project_gateway" / "runner.py").is_file()
    assert not (workspace / ".git").exists()
    assert (REPOSITORY_ROOT / "PROJECT_MANIFEST.yaml").read_bytes() == source_before


def test_control_plane_delegates_preparation_and_validation_to_runner(
    tmp_path: Path,
) -> None:
    control_plane, runner, _ = _fixture_control_plane(tmp_path, recording=True)
    assert isinstance(runner, RecordingLocalRunner)

    prepared = control_plane.prepare_task(
        "python-demo",
        "Change the greeting and run the tests.",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
    )
    job_id = prepared["job"]["job_id"]
    control_plane.replace_workspace_text(
        job_id,
        "src/greeting.py",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )

    validation = control_plane.validate(job_id)

    assert runner.prepared_jobs == [job_id]
    assert runner.validated_jobs == [job_id]
    assert validation["passed"] is True
    assert validation["evidence_verified"] is True


def test_local_runner_preserves_workspace_validation_evidence_and_source(
    tmp_path: Path,
) -> None:
    control_plane, runner, source = _fixture_control_plane(tmp_path)
    source_target = source / "src" / "greeting.py"
    source_before = source_target.read_bytes()
    prepared = control_plane.prepare_task(
        "python-demo",
        "Change the greeting and run the tests.",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
    )
    job_id = prepared["job"]["job_id"]

    control_plane.replace_workspace_text(
        job_id,
        "src/greeting.py",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )
    validation = control_plane.validate(job_id)
    diff = control_plane.get_diff(job_id)
    evidence = control_plane.get_evidence(job_id)

    assert isinstance(runner, LocalRunner)
    assert isinstance(runner, Runner)
    assert validation["passed"] is True
    assert validation["evidence_verified"] is True
    assert 'return "Hello from UPG"' in diff["patch"]
    assert source_target.read_bytes() == source_before
    evidence_path = Path(evidence["path"])
    assert evidence["verified"] is True
    assert {path.name for path in evidence_path.iterdir()} == {
        *EVIDENCE_FILES,
        "manifest.sha256.json",
    }
