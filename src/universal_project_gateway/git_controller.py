"""Constrained local Git publication for explicitly authorized R3 actions."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import GatewayError
from .scoped_fs import ScopedFileError, normalize_relative_path, path_matches

_SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_SAFE_REMOTE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_DEFAULT_BRANCH_NAMES = {"main", "master"}


class GitControllerError(GatewayError):
    default_code = "GIT_CONTROLLER_ERROR"


@dataclass(frozen=True, slots=True)
class GitRepositoryStatus:
    is_repository: bool
    repository_root: str | None
    current_branch: str | None
    default_branch: str | None
    head_sha: str | None
    dirty: bool
    changed_paths: tuple[str, ...]
    staged_paths: tuple[str, ...]
    remotes: tuple[str, ...]
    git_available: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_repository": self.is_repository,
            "repository_root": self.repository_root,
            "current_branch": self.current_branch,
            "default_branch": self.default_branch,
            "head_sha": self.head_sha,
            "dirty": self.dirty,
            "changed_paths": list(self.changed_paths),
            "staged_paths": list(self.staged_paths),
            "remotes": list(self.remotes),
            "git_available": self.git_available,
        }


@dataclass(frozen=True, slots=True)
class GitPublishResult:
    success: bool
    branch: str
    commit_sha: str
    committed_paths: tuple[str, ...]
    pushed: bool = False
    remote: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "committed_paths": list(self.committed_paths),
            "pushed": self.pushed,
            "remote": self.remote,
        }


class GitController:
    """Run only fixed Git argv sequences in one repository."""

    def __init__(self, repository_root: str | os.PathLike[str], *, timeout_seconds: int = 30) -> None:
        root = Path(repository_root).expanduser().resolve(strict=True)
        if not root.is_dir():
            raise GitControllerError("repository path is not a directory", code="GIT_REPOSITORY_INVALID")
        if not 1 <= timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be from 1 to 300")
        self.repository_root = root
        self.timeout_seconds = timeout_seconds
        self.git = shutil.which("git")

    def inspect(self) -> GitRepositoryStatus:
        if not self.git:
            return GitRepositoryStatus(
                False, None, None, None, None, False, (), (), (), git_available=False
            )
        top = self._run(("rev-parse", "--show-toplevel"), check=False)
        if top.returncode != 0:
            return GitRepositoryStatus(False, None, None, None, None, False, (), (), ())
        actual_root = Path(top.stdout.strip()).resolve(strict=True)
        branch_result = self._run(("branch", "--show-current"), check=False)
        current_branch = branch_result.stdout.strip() or None
        head_result = self._run(("rev-parse", "--verify", "HEAD"), check=False)
        head_sha = head_result.stdout.strip() if head_result.returncode == 0 else None
        status_result = self._run(("status", "--porcelain=v1", "-z"), check=True)
        changed, staged = _parse_porcelain(status_result.stdout)
        remote_result = self._run(("remote",), check=False)
        remotes = tuple(
            sorted(line.strip() for line in remote_result.stdout.splitlines() if line.strip())
        )
        default_branch = self._detect_default_branch(current_branch)
        return GitRepositoryStatus(
            is_repository=True,
            repository_root=str(actual_root),
            current_branch=current_branch,
            default_branch=default_branch,
            head_sha=head_sha,
            dirty=bool(changed),
            changed_paths=tuple(sorted(changed)),
            staged_paths=tuple(sorted(staged)),
            remotes=remotes,
        )

    inspect_repository = inspect

    def publish_local_branch(
        self,
        job_id: str,
        changed_paths: Iterable[str],
        *,
        commit_message: str,
        explicit_permission: bool,
        slug: str = "change",
        allow_unrelated_dirty: bool = False,
    ) -> GitPublishResult:
        if not explicit_permission:
            raise GitControllerError(
                "local Git publication requires explicit permission",
                code="GIT_PERMISSION_REQUIRED",
            )
        if not _branch_safe_job_id(job_id):
            raise GitControllerError("job_id is not branch-safe", code="INVALID_JOB_ID")
        intended = self._normalize_paths(changed_paths)
        if not intended:
            raise GitControllerError(
                "at least one intended changed path is required",
                code="NO_INTENDED_CHANGES",
            )
        status = self._publication_status()
        self._check_clean_index(status)
        dirty = set(status.changed_paths)
        missing = set(intended) - dirty
        if missing:
            raise GitControllerError(
                "an intended path has no working-tree change",
                code="INTENDED_PATH_NOT_CHANGED",
                details={"paths": sorted(missing)},
            )
        unrelated = dirty - set(intended)
        if unrelated and not allow_unrelated_dirty:
            raise GitControllerError(
                "repository has unrelated dirty paths",
                code="DIRTY_SOURCE_REPOSITORY",
                details={"unrelated_paths": sorted(unrelated)},
            )
        self._assert_no_clean_filters(intended)

        branch = self.branch_name(job_id, slug)
        if branch == status.default_branch or branch.casefold() in _DEFAULT_BRANCH_NAMES:
            raise GitControllerError(
                "commits to the default branch are prohibited",
                code="DEFAULT_BRANCH_COMMIT_PROHIBITED",
            )
        exists = self._run(("show-ref", "--verify", f"refs/heads/{branch}"), check=False)
        if exists.returncode == 0:
            raise GitControllerError(
                "the publication branch already exists",
                code="GIT_BRANCH_ALREADY_EXISTS",
                details={"branch": branch},
            )
        self._run(("switch", "-c", branch), check=True)
        return self._commit_on_current_branch(
            intended,
            commit_message=commit_message,
            explicit_permission=True,
            expected_branch=branch,
        )

    create_branch_and_commit = publish_local_branch

    def commit(
        self,
        changed_paths: Iterable[str],
        *,
        commit_message: str,
        explicit_permission: bool,
        allow_unrelated_dirty: bool = False,
    ) -> GitPublishResult:
        if not explicit_permission:
            raise GitControllerError(
                "local Git commit requires explicit permission",
                code="GIT_PERMISSION_REQUIRED",
            )
        intended = self._normalize_paths(changed_paths)
        status = self._publication_status()
        self._check_clean_index(status)
        if not status.current_branch or status.current_branch == status.default_branch or status.current_branch.casefold() in _DEFAULT_BRANCH_NAMES:
            raise GitControllerError(
                "commits to the default branch are prohibited",
                code="DEFAULT_BRANCH_COMMIT_PROHIBITED",
                details={"branch": status.current_branch},
            )
        dirty = set(status.changed_paths)
        missing = set(intended) - dirty
        if missing:
            raise GitControllerError(
                "an intended path has no working-tree change",
                code="INTENDED_PATH_NOT_CHANGED",
                details={"paths": sorted(missing)},
            )
        unrelated = dirty - set(intended)
        if unrelated and not allow_unrelated_dirty:
            raise GitControllerError(
                "repository has unrelated dirty paths",
                code="DIRTY_SOURCE_REPOSITORY",
                details={"unrelated_paths": sorted(unrelated)},
            )
        return self._commit_on_current_branch(
            intended,
            commit_message=commit_message,
            explicit_permission=True,
            expected_branch=status.current_branch,
        )

    def _commit_on_current_branch(
        self,
        intended: tuple[str, ...],
        *,
        commit_message: str,
        explicit_permission: bool,
        expected_branch: str,
    ) -> GitPublishResult:
        if not explicit_permission:
            raise GitControllerError("explicit permission is required", code="GIT_PERMISSION_REQUIRED")
        self._validate_commit_message(commit_message)
        current = self.inspect()
        if current.current_branch != expected_branch:
            raise GitControllerError("Git branch changed unexpectedly", code="GIT_STATE_CHANGED")
        if current.current_branch == current.default_branch or current.current_branch.casefold() in _DEFAULT_BRANCH_NAMES:
            raise GitControllerError(
                "commits to the default branch are prohibited",
                code="DEFAULT_BRANCH_COMMIT_PROHIBITED",
            )
        self._assert_no_clean_filters(intended)
        self._run(("add", "--", *intended), check=True)
        staged_result = self._run(
            ("diff", "--cached", "--name-only", "--no-ext-diff", "-z"), check=True
        )
        staged = tuple(sorted(path for path in staged_result.stdout.split("\x00") if path))
        if set(staged) != set(intended):
            raise GitControllerError(
                "Git staged a path outside the intended set or omitted an intended path",
                code="GIT_STAGE_SCOPE_MISMATCH",
                details={"intended": list(intended), "staged": list(staged)},
            )
        # --no-verify prevents project-controlled commit hooks from becoming an
        # execution side channel.  The -c option is command-local, not global.
        self._run(
            ("-c", "commit.gpgsign=false", "commit", "--no-verify", "-m", commit_message),
            check=True,
        )
        sha = self._run(("rev-parse", "HEAD"), check=True).stdout.strip()
        return GitPublishResult(True, expected_branch, sha, intended)

    def push_current_branch(
        self,
        *,
        explicit_permission: bool,
        remote: str = "origin",
        force: bool = False,
    ) -> GitPublishResult:
        if force:
            raise GitControllerError("force push is prohibited", code="FORCE_PUSH_PROHIBITED")
        if not explicit_permission:
            raise GitControllerError("push requires explicit permission", code="GIT_PERMISSION_REQUIRED")
        if not _SAFE_REMOTE.fullmatch(remote):
            raise GitControllerError("remote name is invalid", code="INVALID_GIT_REMOTE")
        status = self._publication_status()
        if not status.current_branch or status.current_branch == status.default_branch or status.current_branch.casefold() in _DEFAULT_BRANCH_NAMES:
            raise GitControllerError(
                "pushing the default branch is prohibited",
                code="DEFAULT_BRANCH_PUSH_PROHIBITED",
            )
        if remote not in status.remotes:
            raise GitControllerError(
                "requested Git remote is not configured",
                code="GIT_REMOTE_NOT_FOUND",
                details={"remote": remote},
            )
        self._run(("push", "--set-upstream", remote, status.current_branch), check=True, timeout=120)
        return GitPublishResult(
            True,
            status.current_branch,
            status.head_sha or "",
            (),
            pushed=True,
            remote=remote,
        )

    @staticmethod
    def branch_name(job_id: str, slug: str = "change") -> str:
        if not _branch_safe_job_id(job_id):
            raise GitControllerError("job_id is not branch-safe", code="INVALID_JOB_ID")
        cleaned = re.sub(r"[^a-z0-9]+", "-", slug.casefold()).strip("-")[:40] or "change"
        return f"agent/{job_id}-{cleaned}"

    def _publication_status(self) -> GitRepositoryStatus:
        status = self.inspect()
        if not self.git:
            raise GitControllerError("Git executable was not found", code="GIT_NOT_AVAILABLE")
        if not status.is_repository:
            raise GitControllerError("path is not a Git repository", code="GIT_REPOSITORY_INVALID")
        if Path(status.repository_root or "").resolve() != self.repository_root:
            raise GitControllerError(
                "controller must be rooted at the repository top level",
                code="GIT_REPOSITORY_ROOT_MISMATCH",
            )
        return status

    @staticmethod
    def _check_clean_index(status: GitRepositoryStatus) -> None:
        if status.staged_paths:
            raise GitControllerError(
                "repository already contains staged changes",
                code="GIT_INDEX_NOT_CLEAN",
                details={"staged_paths": list(status.staged_paths)},
            )

    def _normalize_paths(self, paths: Iterable[str]) -> tuple[str, ...]:
        normalized: list[str] = []
        for raw in paths:
            try:
                relative = normalize_relative_path(raw)
            except ScopedFileError as exc:
                raise GitControllerError(
                    "Git paths must be repository-relative",
                    code="GIT_PATH_FORBIDDEN",
                    details={"path": str(raw), "reason": exc.code},
                ) from exc
            if path_matches(relative, (".git",)):
                raise GitControllerError(".git paths may not be staged", code="GIT_PATH_FORBIDDEN")
            resolved = self.repository_root.joinpath(*relative.split("/")).resolve(strict=False)
            if resolved != self.repository_root and self.repository_root not in resolved.parents:
                raise GitControllerError("Git path escaped repository", code="GIT_PATH_FORBIDDEN")
            normalized.append(relative)
        return tuple(sorted(dict.fromkeys(normalized)))

    def _assert_no_clean_filters(self, paths: tuple[str, ...]) -> None:
        """Refuse attributes that could execute a filter process during add."""

        result = self._run(("check-attr", "-z", "filter", "--", *paths), check=True)
        records = result.stdout.split("\x00")
        configured: dict[str, str] = {}
        for index in range(0, len(records) - 2, 3):
            path, attribute, value = records[index : index + 3]
            if attribute == "filter" and value not in {"", "unspecified", "unset"}:
                configured[path] = value
        if configured:
            raise GitControllerError(
                "Git clean filters are prohibited for staged paths",
                code="GIT_FILTER_FORBIDDEN",
                details={"filters": configured},
            )

    @staticmethod
    def _validate_commit_message(message: str) -> None:
        if not isinstance(message, str) or not message.strip() or len(message) > 200:
            raise GitControllerError("commit message must be 1-200 characters", code="INVALID_COMMIT_MESSAGE")
        if any(character in message for character in ("\x00", "\r", "\n")):
            raise GitControllerError("commit message may not contain control lines", code="INVALID_COMMIT_MESSAGE")

    def _detect_default_branch(self, current_branch: str | None) -> str | None:
        remote_head = self._run(
            ("symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"),
            check=False,
        )
        if remote_head.returncode == 0 and "/" in remote_head.stdout.strip():
            return remote_head.stdout.strip().split("/", 1)[1]
        branches = self._run(
            ("for-each-ref", "--format=%(refname:short)", "refs/heads"), check=False
        )
        local = {line.strip() for line in branches.stdout.splitlines() if line.strip()}
        if "main" in local:
            return "main"
        if "master" in local:
            return "master"
        # Conservative fallback: treating the only/current branch as default
        # prevents an accidental commit when default-branch discovery is weak.
        return current_branch

    def _run(
        self,
        arguments: tuple[str, ...],
        *,
        check: bool,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]:
        if not self.git:
            raise GitControllerError("Git executable was not found", code="GIT_NOT_AVAILABLE")
        try:
            result = subprocess.run(
                [
                    self.git,
                    "-c",
                    f"core.hooksPath={os.devnull}",
                    "-c",
                    "core.fsmonitor=false",
                    "-c",
                    "credential.helper=",
                    *arguments,
                ],
                cwd=self.repository_root,
                shell=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout or self.timeout_seconds,
                check=False,
                env=_git_environment(),
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise GitControllerError(
                "Git command could not be completed",
                code="GIT_COMMAND_ERROR",
                details={"operation": arguments[0], "error": str(exc)},
            ) from exc
        if check and result.returncode != 0:
            raise GitControllerError(
                "Git operation failed",
                code="GIT_COMMAND_FAILED",
                details={
                    "operation": arguments[0],
                    "returncode": result.returncode,
                    "stderr": result.stderr.strip()[:2_000],
                },
            )
        return result


def _parse_porcelain(output: str) -> tuple[set[str], set[str]]:
    changed: set[str] = set()
    staged: set[str] = set()
    records = [record for record in output.split("\x00") if record]
    index = 0
    while index < len(records):
        record = records[index]
        if len(record) < 4:
            index += 1
            continue
        index_state = record[0]
        relative = record[3:].replace("\\", "/")
        changed.add(relative)
        if index_state not in {" ", "?"}:
            staged.add(relative)
        if index_state in {"R", "C"} and index + 1 < len(records):
            index += 1
            source = records[index].replace("\\", "/")
            changed.add(source)
            if index_state not in {" ", "?"}:
                staged.add(source)
        index += 1
    return changed, staged


def _branch_safe_job_id(job_id: str) -> bool:
    return bool(
        isinstance(job_id, str)
        and _SAFE_JOB_ID.fullmatch(job_id)
        and job_id not in {".", ".."}
        and ".." not in job_id
        and not job_id.endswith((".", ".lock"))
        and "@{" not in job_id
    )


def _git_environment() -> dict[str, str]:
    environment = {
        key: os.environ[key]
        for key in (
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "HOME",
            "USERPROFILE",
            "TEMP",
            "TMP",
        )
        if key in os.environ
    }
    environment.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "",
            "GCM_INTERACTIVE": "Never",
            "LC_ALL": "C",
        }
    )
    return environment


__all__ = [
    "GitController",
    "GitControllerError",
    "GitPublishResult",
    "GitRepositoryStatus",
]
