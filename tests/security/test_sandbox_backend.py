from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.models import CommandSpec
from universal_project_gateway.runner import LocalRunner
from universal_project_gateway.runtime.python_adapter import PythonAdapter
from universal_project_gateway.sandbox import (
    LocalProcessSandboxBackend,
    SandboxError,
    SandboxExecutionRequest,
    UnsafeLocalSandboxBackend,
)
from universal_project_gateway.service import GatewayService

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


def _request(
    workspace: Path,
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 5,
    environment: dict[str, str] | None = None,
) -> SandboxExecutionRequest:
    return SandboxExecutionRequest(
        action="test",
        argv=("python", "-m", "unittest"),
        cwd=cwd or workspace,
        timeout_seconds=timeout_seconds,
        environment=environment or {},
    )


def test_default_backend_preserves_runtime_behavior_and_metadata(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    (workspace / "test_ok.py").write_text(
        "import unittest\n\n"
        "class TestOk(unittest.TestCase):\n"
        "    def test_ok(self):\n"
        "        self.assertEqual(2 + 2, 4)\n",
        encoding="utf-8",
    )

    adapter = PythonAdapter(
        workspace,
        {"test": CommandSpec(("python", "-m", "unittest"))},
    )
    result = adapter.run_tests()

    assert isinstance(adapter.sandbox_backend, UnsafeLocalSandboxBackend)
    assert result.status == "passed"
    assert result.to_dict()["sandbox"] == {
        "backend_id": "unsafe-local-subprocess",
        "safety_level": "unsafe-local",
        "runtime_action": "test",
        "shell_disabled": True,
        "environment_filtered": True,
        "network_policy": "unrestricted",
        "network_policy_enforced": False,
        "limitation_notes": list(adapter.sandbox_backend.limitation_notes),
        "artifacts": [],
    }


def test_unsafe_backend_always_disables_shell(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    backend = UnsafeLocalSandboxBackend()
    handle = backend.prepare(workspace)
    captured: dict[str, Any] = {}

    def fake_run(argv: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["argv"] = argv
        captured.update(kwargs)
        return subprocess.CompletedProcess(argv, 0, stdout="ok", stderr="")

    monkeypatch.setattr(
        "universal_project_gateway.sandbox.local.subprocess.run",
        fake_run,
    )

    result = backend.execute(handle, _request(workspace))

    assert result.passed is True
    assert captured["shell"] is False
    assert captured["cwd"] == workspace.resolve()


def test_sandbox_rejects_cwd_outside_prepared_workspace(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    backend = LocalProcessSandboxBackend()
    handle = backend.prepare(workspace)

    with pytest.raises(SandboxError) as caught:
        backend.execute(handle, _request(workspace, cwd=outside))

    assert caught.value.code == "SANDBOX_CWD_OUTSIDE_WORKSPACE"


def test_local_process_backend_filters_environment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    backend = LocalProcessSandboxBackend()
    handle = backend.prepare(workspace)
    captured: dict[str, Any] = {}

    class FakeProcess:
        returncode = 0

        def communicate(self, timeout: int | None = None) -> tuple[str, str]:
            captured["timeout"] = timeout
            return "ok", ""

        def poll(self) -> int:
            return self.returncode

    def fake_popen(argv: list[str], **kwargs: Any) -> FakeProcess:
        captured["argv"] = argv
        captured.update(kwargs)
        return FakeProcess()

    monkeypatch.setattr(
        "universal_project_gateway.sandbox.local.subprocess.Popen",
        fake_popen,
    )

    result = backend.execute(
        handle,
        _request(
            workspace,
            environment={"PATH": "safe-path", "UPG_TEST_SECRET": "must-not-pass"},
        ),
    )

    assert result.passed is True
    assert captured["shell"] is False
    assert captured["env"] == {"PATH": "safe-path"}
    assert result.environment_filtered is True


def test_local_process_backend_enforces_timeout(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    tests = workspace / "tests"
    tests.mkdir()
    (tests / "test_sleep.py").write_text(
        "import time\n\ndef test_slow():\n    time.sleep(5)\n",
        encoding="utf-8",
    )
    backend = LocalProcessSandboxBackend()
    adapter = PythonAdapter(
        workspace,
        {
            "test": CommandSpec(
                ("python", "-m", "pytest", "tests", "-q"),
                timeout_seconds=1,
            )
        },
        sandbox_backend=backend,
    )

    result = adapter.run_tests()

    assert result.status == "timed_out"
    assert result.timed_out is True
    assert result.reason_code == "COMMAND_TIMEOUT"
    assert result.duration_seconds < 4


def test_cancellation_before_execution_does_not_start_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = _workspace(tmp_path)
    backend = LocalProcessSandboxBackend()
    handle = backend.prepare(workspace)

    def forbidden_popen(*args: Any, **kwargs: Any) -> None:
        pytest.fail("process execution must not start after cancellation")

    monkeypatch.setattr(
        "universal_project_gateway.sandbox.local.subprocess.Popen",
        forbidden_popen,
    )

    result = backend.execute(handle, _request(workspace), should_cancel=lambda: True)

    assert result.status == "cancelled"
    assert result.cancelled is True
    assert result.returncode is None
    assert result.reason_code == "SANDBOX_CANCELLED"


def test_local_runner_records_sandbox_metadata_in_verified_evidence(tmp_path: Path) -> None:
    source = tmp_path / "source" / "python_demo"
    shutil.copytree(REPOSITORY_ROOT / "fixtures" / "python_demo", source)
    config = GatewayConfig.from_root(tmp_path / "gateway")
    runner = LocalRunner(config, sandbox_backend=LocalProcessSandboxBackend())
    gateway = GatewayService(config, runner=runner)
    gateway.register_project(source / "PROJECT_MANIFEST.yaml")
    prepared = gateway.prepare_task(
        "python-demo",
        "Validate the isolated fixture",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
    )
    gateway.replace_workspace_text(
        prepared["job"]["job_id"],
        "src/greeting.py",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )

    validation = gateway.validate(prepared["job"]["job_id"])

    assert validation["passed"] is True
    check = validation["checks"][0]
    assert check["sandbox"]["backend_id"] == "local-process-restricted"
    assert check["sandbox"]["safety_level"] == "process-restricted"
    assert check["sandbox"]["runtime_action"] == "test"
    assert check["sandbox"]["shell_disabled"] is True
    assert check["sandbox"]["environment_filtered"] is True
    evidence = gateway.get_evidence(prepared["job"]["job_id"])
    assert evidence["verified"] is True
    environment = json.loads(
        (Path(evidence["path"]) / "environment.json").read_text(encoding="utf-8")
    )
    sandbox = environment["sandbox"]
    assert sandbox["backend_id"] == "local-process-restricted"
    assert sandbox["destroyed"] is True
    assert sandbox["executions"][0]["timeout_seconds"] > 0
    assert sandbox["executions"][0]["returncode"] == 0
    assert sandbox["limitation_notes"]
