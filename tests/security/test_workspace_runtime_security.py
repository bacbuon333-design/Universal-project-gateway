from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from universal_project_gateway.git_controller import GitController, GitControllerError
from universal_project_gateway.models import CommandSpec
from universal_project_gateway.runtime.base import RuntimeAdapterError
from universal_project_gateway.runtime.python_adapter import PythonAdapter
from universal_project_gateway.scoped_fs import ScopedFileError, ScopedWorkspace
from universal_project_gateway.workspaces import WorkspaceError, WorkspaceManager


def test_binary_files_remain_metadata_only(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    binary = workspace / "image.bin"
    binary.write_bytes(b"\x89PNG\r\n\x1a\n\x00payload")
    scoped = ScopedWorkspace(workspace)

    assert scoped.metadata("image.bin")["binary"] is True
    with pytest.raises(ScopedFileError) as read_error:
        scoped.read_text("image.bin")
    with pytest.raises(ScopedFileError) as replace_error:
        scoped.replace_text("image.bin", "destroyed")
    with pytest.raises(ScopedFileError) as move_error:
        scoped.move("image.bin", "moved.bin")

    assert read_error.value.code == "BINARY_FILE_READ_FORBIDDEN"
    assert replace_error.value.code == "BINARY_FILE_READ_FORBIDDEN"
    assert move_error.value.code == "BINARY_FILE_READ_FORBIDDEN"
    assert binary.exists()


@pytest.mark.parametrize("job_id", ["../escape", "C:\\escape", ".", "job/name"])
def test_workspace_job_identifier_cannot_escape_root(tmp_path: Path, job_id: str) -> None:
    source = tmp_path / "source"
    source.mkdir()
    manager = WorkspaceManager(tmp_path / "jobs")

    with pytest.raises(WorkspaceError) as caught:
        manager.create(job_id, source)

    assert caught.value.code == "INVALID_JOB_ID"


@pytest.mark.parametrize(
    "argv",
    [
        ("python", "-c", "print('unsafe')"),
        ("python", "-m", "pytest", "--basetemp=C:/outside"),
        ("python", "-m", "pytest", "../outside"),
    ],
)
def test_python_runtime_rejects_inline_code_external_paths_and_unapproved_flags(
    tmp_path: Path, argv: tuple[str, ...]
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    adapter = PythonAdapter(workspace, {"test": CommandSpec(argv)})

    with pytest.raises(RuntimeAdapterError):
        adapter.run_tests()


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_git_controller_branches_then_stages_only_the_intended_path(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "UPG Tests")
    _git(repository, "config", "user.email", "upg-tests@example.invalid")
    target = repository / "greeting.txt"
    target.write_text("Hello\n", encoding="utf-8")
    _git(repository, "add", "--", "greeting.txt")
    _git(repository, "commit", "-m", "Initial")
    target.write_text("Hello from UPG\n", encoding="utf-8")

    controller = GitController(repository)
    status = controller.inspect()
    assert status.current_branch == "main"
    assert status.default_branch == "main"
    with pytest.raises(GitControllerError) as direct_commit:
        controller.commit(
            ["greeting.txt"],
            commit_message="Unsafe default branch commit",
            explicit_permission=True,
        )
    assert direct_commit.value.code == "DEFAULT_BRANCH_COMMIT_PROHIBITED"

    published = controller.publish_local_branch(
        "job-git-1",
        ["greeting.txt"],
        commit_message="Apply isolated change",
        explicit_permission=True,
        slug="greeting",
    )
    assert published.success is True
    assert published.branch == "agent/job-git-1-greeting"
    assert len(published.commit_sha) == 40
    assert controller.inspect().dirty is False

    with pytest.raises(GitControllerError) as force_push:
        controller.push_current_branch(explicit_permission=True, force=True)
    assert force_push.value.code == "FORCE_PUSH_PROHIBITED"


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_git_controller_refuses_unrelated_dirty_source(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "UPG Tests")
    _git(repository, "config", "user.email", "upg-tests@example.invalid")
    for name in ("intended.txt", "unrelated.txt"):
        (repository / name).write_text("initial\n", encoding="utf-8")
    _git(repository, "add", "--", "intended.txt", "unrelated.txt")
    _git(repository, "commit", "-m", "Initial")
    (repository / "intended.txt").write_text("intended change\n", encoding="utf-8")
    (repository / "unrelated.txt").write_text("unrelated change\n", encoding="utf-8")

    with pytest.raises(GitControllerError) as caught:
        GitController(repository).publish_local_branch(
            "job-dirty",
            ["intended.txt"],
            commit_message="Must not publish",
            explicit_permission=True,
        )

    assert caught.value.code == "DIRTY_SOURCE_REPOSITORY"
    assert _git(repository, "branch", "--show-current").stdout.strip() == "main"


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is not installed")
def test_git_controller_refuses_clean_filter_execution_during_staging(tmp_path: Path) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    _git(repository, "init", "-b", "main")
    _git(repository, "config", "user.name", "UPG Tests")
    _git(repository, "config", "user.email", "upg-tests@example.invalid")
    target = repository / "greeting.txt"
    target.write_text("initial\n", encoding="utf-8")
    _git(repository, "add", "--", "greeting.txt")
    _git(repository, "commit", "-m", "Initial")
    (repository / ".gitattributes").write_text("*.txt filter=unsafe\n", encoding="utf-8")
    _git(repository, "add", "--", ".gitattributes")
    _git(repository, "commit", "-m", "Declare filter attribute")
    target.write_text("changed\n", encoding="utf-8")

    with pytest.raises(GitControllerError) as caught:
        GitController(repository).publish_local_branch(
            "job-filter",
            ["greeting.txt"],
            commit_message="Must not invoke a clean filter",
            explicit_permission=True,
        )

    assert caught.value.code == "GIT_FILTER_FORBIDDEN"


def _git(repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [shutil.which("git") or "git", *arguments],
        cwd=repository,
        shell=False,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
