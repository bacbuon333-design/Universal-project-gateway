from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.models import CommandSpec
from universal_project_gateway.policy import PolicyEngine
from universal_project_gateway.registry import ProjectRegistry, UnregisteredPathError
from universal_project_gateway.runtime.base import RuntimeAdapterError
from universal_project_gateway.runtime.node_adapter import NodeAdapter
from universal_project_gateway.runtime.python_adapter import PythonAdapter
from universal_project_gateway.service import GatewayService

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "tests").mkdir()
    return workspace


def test_shell_operator_injection_is_rejected_before_process_start(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    marker = tmp_path / "injection-ran.txt"
    adapter = PythonAdapter(
        workspace,
        {
            "test": CommandSpec(
                (
                    "python",
                    "-m",
                    "pytest",
                    "tests",
                    "&&",
                    "python",
                    "-c",
                    f"open({str(marker)!r}, 'w').write('bad')",
                )
            )
        },
    )

    with pytest.raises(RuntimeAdapterError) as caught:
        adapter.run_tests()

    assert caught.value.code == "UNSAFE_COMMAND_ARGUMENT"
    assert not marker.exists()


@pytest.mark.parametrize("executable", ["powershell", "cmd.exe", "bash", "curl"])
def test_python_adapter_rejects_arbitrary_executables(tmp_path: Path, executable: str) -> None:
    adapter = PythonAdapter(
        _workspace(tmp_path),
        {"test": CommandSpec((executable, "--version"))},
    )

    with pytest.raises(RuntimeAdapterError) as caught:
        adapter.run_tests()

    assert caught.value.code == "EXECUTABLE_NOT_ALLOWLISTED"


def test_python_adapter_rejects_arbitrary_python_modules(tmp_path: Path) -> None:
    adapter = PythonAdapter(
        _workspace(tmp_path),
        {"test": CommandSpec(("python", "-m", "http.server"))},
    )

    with pytest.raises(RuntimeAdapterError) as caught:
        adapter.run_tests()

    assert caught.value.code == "PYTHON_MODULE_NOT_ALLOWLISTED"


def test_node_adapter_rejects_arbitrary_executable_without_running_it(tmp_path: Path) -> None:
    adapter = NodeAdapter(
        _workspace(tmp_path),
        {"test": CommandSpec(("cmd.exe", "/c", "whoami"))},
    )

    with pytest.raises(RuntimeAdapterError) as caught:
        adapter.run_tests()

    assert caught.value.code == "EXECUTABLE_NOT_ALLOWLISTED"


def test_non_allowlisted_environment_variable_is_rejected(tmp_path: Path) -> None:
    adapter = PythonAdapter(
        _workspace(tmp_path),
        {
            "test": CommandSpec(
                ("python", "-m", "pytest", "tests"),
                environment=("AWS_SECRET_ACCESS_KEY",),
            )
        },
    )

    with pytest.raises(RuntimeAdapterError) as caught:
        adapter.run_tests()

    assert caught.value.code == "ENVIRONMENT_VARIABLE_FORBIDDEN"


def test_registry_refuses_unregistered_and_nested_paths(tmp_path: Path) -> None:
    source = tmp_path / "python_demo"
    shutil.copytree(REPOSITORY_ROOT / "fixtures" / "python_demo", source)
    registry = ProjectRegistry(tmp_path / "registry" / "projects.yaml")
    registered = registry.register(source / "PROJECT_MANIFEST.yaml")
    assert registry.resolve_path(source).project_id == registered.project_id

    for unregistered in (source / "src", tmp_path / "different-project"):
        with pytest.raises(UnregisteredPathError) as caught:
            registry.resolve_path(unregistered)
        assert caught.value.code == "UNREGISTERED_PATH"


@pytest.mark.parametrize(
    "action",
    [
        "delete",
        "deploy",
        "merge",
        "force_push",
        "read_credentials",
        "source_modify",
    ],
)
def test_destructive_and_credential_actions_return_structured_r4_refusal(
    action: str,
) -> None:
    decision = PolicyEngine().decide(
        action,
        permissions={
            "read": True,
            "workspace_write": True,
            "validation": True,
            "git_publish": True,
        },
        explicit=True,
    )

    assert decision.to_dict() == {
        "allowed": False,
        "risk_level": "R4",
        "reason_code": "ACTION_PROHIBITED",
        "message": decision.message,
    }


def test_deletion_request_never_deletes_and_moves_job_to_approval(tmp_path: Path) -> None:
    source = tmp_path / "python_demo"
    shutil.copytree(REPOSITORY_ROOT / "fixtures" / "python_demo", source)
    gateway = GatewayService(GatewayConfig.from_root(tmp_path / "gateway"))
    gateway.register_project(source / "PROJECT_MANIFEST.yaml")
    prepared = gateway.prepare_task(
        "python-demo",
        "Change the greeting",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
    )
    job_id = prepared["job"]["job_id"]
    workspace_target = Path(prepared["workspace"]) / "src" / "greeting.py"
    before = workspace_target.read_bytes()

    request = gateway.request_delete(job_id, "src/greeting.py")

    assert request["risk_level"] == "R4"
    assert request["status"] == "waiting_for_approval"
    assert request["executed"] is False
    assert workspace_target.read_bytes() == before
    assert gateway.inspect_job(job_id)["job"]["status"] == "waiting_for_approval"


def test_service_has_no_generic_execution_or_source_mutation_api() -> None:
    forbidden = {
        "run_any_command",
        "execute_python",
        "execute_shell",
        "delete_source_path",
        "deploy",
        "merge",
        "force_push",
        "read_credentials",
    }

    assert all(not hasattr(GatewayService, name) for name in forbidden)
