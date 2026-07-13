from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from universal_project_gateway.git_controller import GitController, GitControllerError
from universal_project_gateway.policy import PolicyEngine

PUBLISH_PERMISSIONS = {
    "read": True,
    "workspace_write": True,
    "validation": True,
    "git_publish": True,
}


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


@pytest.fixture
def local_git_repository(tmp_path: Path) -> Path:
    if shutil.which("git") is None:
        pytest.skip("Git is not installed")
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init")
    _git(repository, "config", "user.name", "UPG Test")
    _git(repository, "config", "user.email", "upg-test@example.invalid")
    (repository / "tracked.txt").write_text("before\n", encoding="utf-8")
    _git(repository, "add", "--", "tracked.txt")
    _git(repository, "commit", "-m", "Initial fixture")
    _git(repository, "branch", "-M", "main")
    return repository


def test_direct_default_branch_commit_is_rejected_even_with_publish_permission() -> None:
    decision = PolicyEngine().decide(
        "local_commit",
        permissions=PUBLISH_PERMISSIONS,
        explicit=True,
        branch="main",
        default_branch="main",
    )

    assert decision.allowed is False
    assert decision.risk_level.value == "R3"
    assert decision.reason_code == "DEFAULT_BRANCH_PROHIBITED"


def test_detected_nonstandard_default_branch_is_also_rejected() -> None:
    decision = PolicyEngine().decide(
        "local_commit",
        permissions=PUBLISH_PERMISSIONS,
        explicit=True,
        branch="trunk",
        default_branch="refs/heads/trunk",
    )

    assert decision.allowed is False
    assert decision.reason_code == "DEFAULT_BRANCH_PROHIBITED"


def test_force_push_is_always_r4_and_cannot_be_authorized() -> None:
    decision = PolicyEngine().decide(
        "force_push",
        permissions=PUBLISH_PERMISSIONS,
        explicit=True,
        branch="agent/safe-job",
        default_branch="main",
    )

    assert decision.to_dict()["allowed"] is False
    assert decision.to_dict()["risk_level"] == "R4"
    assert decision.to_dict()["reason_code"] == "ACTION_PROHIBITED"


def test_git_controller_refuses_commit_on_actual_default_branch(
    local_git_repository: Path,
) -> None:
    (local_git_repository / "tracked.txt").write_text("after\n", encoding="utf-8")
    controller = GitController(local_git_repository)

    with pytest.raises(GitControllerError) as caught:
        controller.commit(
            ["tracked.txt"],
            commit_message="Must not land on main",
            explicit_permission=True,
        )

    assert caught.value.code == "DEFAULT_BRANCH_COMMIT_PROHIBITED"
    status = controller.inspect()
    assert status.current_branch == "main"
    assert status.staged_paths == ()
    assert status.changed_paths == ("tracked.txt",)
    assert _git(local_git_repository, "show", "HEAD:tracked.txt") == "before"


def test_git_controller_rejects_force_before_contacting_a_remote(
    local_git_repository: Path,
) -> None:
    controller = GitController(local_git_repository)

    with pytest.raises(GitControllerError) as caught:
        controller.push_current_branch(
            explicit_permission=True,
            remote="origin",
            force=True,
        )

    assert caught.value.code == "FORCE_PUSH_PROHIBITED"
    assert controller.inspect().current_branch == "main"
