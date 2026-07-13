from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest
import yaml

from universal_project_gateway.service import GatewayService


def _git(repository: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repository,
        shell=False,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_validated_job_publishes_only_intended_change_to_generated_local_branch(
    gateway_factory: Callable[[str], tuple[GatewayService, Path]],
) -> None:
    gateway, source = gateway_factory("python_demo")
    manifest_path = source / "PROJECT_MANIFEST.yaml"
    # The factory registers immediately, so update both the disposable source
    # contract and its registry record by using a fresh isolated Gateway below.
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    manifest["permissions"]["git_publish"] = True
    manifest["publication_policy"]["allow_local_branch"] = True
    manifest_path.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )

    # Registration is intentionally non-idempotent. Recreate only the Gateway
    # runtime, while retaining the temp source copy supplied by the fixture.
    gateway = GatewayService(gateway.config.root_dir.parent / "publish-gateway")
    gateway.register_project(manifest_path)
    _git(source, "init")
    _git(source, "config", "user.name", "UPG Test")
    _git(source, "config", "user.email", "upg-test@example.invalid")
    _git(source, "add", "--all")
    _git(source, "commit", "-m", "Initial fixture")
    _git(source, "branch", "-M", "main")

    prepared = gateway.prepare_task(
        "python-demo",
        "Change the greeting and run the tests",
        target_paths=["src/greeting.py"],
        requested_operation="edit",
    )
    job_id = prepared["job"]["job_id"]
    gateway.replace_workspace_text(
        job_id,
        "src/greeting.py",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )
    assert gateway.validate(job_id)["passed"] is True
    assert _git(source, "branch", "--show-current") == "main"
    assert _git(source, "status", "--porcelain") == ""

    published = gateway.publish_local_branch(job_id, explicit=True)

    assert published["success"] is True
    assert published["branch"].startswith(f"agent/{job_id}-")
    assert published["branch"] != "main"
    assert published["committed_paths"] == ["src/greeting.py"]
    assert len(published["commit_sha"]) == 40
    assert _git(source, "branch", "--show-current") == published["branch"]
    assert _git(source, "status", "--porcelain") == ""
    assert _git(source, "diff", "--name-only", "main..HEAD") == "src/greeting.py"
    assert 'return "Hello from UPG"' in _git(source, "show", "HEAD:src/greeting.py")
