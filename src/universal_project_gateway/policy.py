"""Canonical risk classification and conjunctive project policy decisions."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from .models import PolicyDecision, ProjectManifest, ProjectPermissions, RiskLevel

_WINDOWS_ABSOLUTE_PATH = re.compile(r"^[A-Za-z]:[/\\]")

_ACTION_ALIASES = {
    "get": "read",
    "inspect": "read",
    "list": "read",
    "read_file": "read",
    "search": "read",
    "show": "read",
    "diff": "read",
    "inspect_files": "read",
    "create": "write",
    "edit": "write",
    "modify": "write",
    "move": "write",
    "patch": "write",
    "replace": "write",
    "update": "write",
    "write_file": "write",
    "run_validation": "validate",
    "run_build": "build",
    "run_lint": "lint",
    "run_smoke_test": "smoke_test",
    "run_tests": "test",
    "smoke": "smoke_test",
    "branch": "local_commit",
    "commit": "local_commit",
    "create_branch": "local_commit",
    "publish": "local_commit",
    "remove": "delete",
    "delete_file": "delete",
    "request_delete": "delete",
    "deployment": "deploy",
    "credentials": "read_credentials",
    "force-push": "force_push",
    "force push": "force_push",
}

_R0_ACTIONS = {"read"}
_R1_ACTIONS = {"write"}
_R2_ACTIONS = {"build", "install", "lint", "smoke_test", "test", "validate"}
_R3_ACTIONS = {"local_commit", "push"}
_R4_ACTIONS = {
    "delete",
    "deploy",
    "force_push",
    "merge",
    "production_action",
    "read_credentials",
    "source_delete",
    "source_modify",
}


def classify_action(action: str) -> RiskLevel:
    normalized = _normalize_action(action)
    if normalized in _R0_ACTIONS:
        return RiskLevel.R0
    if normalized in _R1_ACTIONS:
        return RiskLevel.R1
    if normalized in _R2_ACTIONS:
        return RiskLevel.R2
    if normalized in _R3_ACTIONS:
        return RiskLevel.R3
    return RiskLevel.R4


def _normalize_action(action: str) -> str:
    if not isinstance(action, str):
        return ""
    candidate = action.strip().casefold().replace("-", "_")
    return _ACTION_ALIASES.get(candidate, candidate)


def _normalize_relative_path(path: str) -> str | None:
    if not isinstance(path, str) or not path.strip():
        return None
    candidate = path.strip().replace("\\", "/")
    if (
        candidate.startswith("/")
        or candidate.startswith("//")
        or _WINDOWS_ABSOLUTE_PATH.match(candidate)
    ):
        return None
    parsed = PurePosixPath(candidate)
    if any(part in {"", ".", ".."} for part in parsed.parts):
        return None
    return parsed.as_posix()


def is_protected_path(path: str, protected_paths: tuple[str, ...] | list[str]) -> bool:
    normalized = _normalize_relative_path(path)
    if normalized is None:
        return True
    candidate = normalized.casefold()
    pure_candidate = PurePosixPath(candidate)
    for raw_pattern in protected_paths:
        pattern = raw_pattern.replace("\\", "/").strip("/").casefold()
        if not pattern:
            continue
        if candidate == pattern or candidate.startswith(f"{pattern}/"):
            return True
        if any(character in pattern for character in "*?[") and pure_candidate.match(pattern):
            return True
    return False


def _permission_value(permissions: ProjectPermissions | Mapping[str, Any], name: str) -> bool:
    if isinstance(permissions, ProjectPermissions):
        return bool(getattr(permissions, name))
    return permissions.get(name) is True


class PolicyEngine:
    """Apply global prohibitions and project-declared permission reductions."""

    def decide(
        self,
        action: str | ProjectManifest,
        manifest: ProjectManifest | str | None = None,
        *,
        explicit: bool = False,
        branch: str | None = None,
        default_branch: str | None = None,
        path: str | None = None,
        permissions: ProjectPermissions | Mapping[str, Any] | None = None,
    ) -> PolicyDecision:
        # Accept ``decide(manifest, action)`` as a small compatibility courtesy.
        if isinstance(action, ProjectManifest):
            action, manifest = manifest if isinstance(manifest, str) else "", action
        normalized = _normalize_action(action)
        risk = classify_action(normalized)
        project_manifest = manifest if isinstance(manifest, ProjectManifest) else None
        project_permissions = permissions or (
            project_manifest.permissions if project_manifest is not None else None
        )

        if normalized not in _R0_ACTIONS | _R1_ACTIONS | _R2_ACTIONS | _R3_ACTIONS | _R4_ACTIONS:
            return PolicyDecision(
                allowed=False,
                risk_level=RiskLevel.R4,
                reason_code="UNKNOWN_ACTION",
                message="The requested action has no Gateway policy classification.",
            )
        if normalized in _R4_ACTIONS:
            return PolicyDecision(
                allowed=False,
                risk_level=RiskLevel.R4,
                reason_code="ACTION_PROHIBITED",
                message="Destructive, deployment, merge, credential, and direct-source actions are prohibited in this MVP.",
            )

        if path is not None:
            normalized_path = _normalize_relative_path(path)
            if normalized_path is None:
                return PolicyDecision(
                    allowed=False,
                    risk_level=RiskLevel.R4,
                    reason_code="PATH_OUTSIDE_SCOPE",
                    message="Paths must remain relative to the active job workspace.",
                )
            if project_manifest is not None and is_protected_path(
                normalized_path, project_manifest.protected_paths
            ):
                return PolicyDecision(
                    allowed=False,
                    risk_level=risk,
                    reason_code="PROTECTED_PATH",
                    message="The requested path is protected by the project manifest.",
                )

        if project_permissions is None:
            return PolicyDecision(
                allowed=False,
                risk_level=risk,
                reason_code="MANIFEST_REQUIRED",
                message="A validated project manifest is required for a policy decision.",
            )

        permission_name = {
            RiskLevel.R0: "read",
            RiskLevel.R1: "workspace_write",
            RiskLevel.R2: "validation",
            RiskLevel.R3: "git_publish",
        }[risk]
        if not _permission_value(project_permissions, permission_name):
            return PolicyDecision(
                allowed=False,
                risk_level=risk,
                reason_code="PERMISSION_DENIED",
                message=f"Project permission {permission_name!r} does not allow this action.",
            )

        if (
            risk is RiskLevel.R2
            and project_manifest is not None
            and normalized
            in {
                "build",
                "install",
                "lint",
                "smoke_test",
                "test",
            }
            and project_manifest.command(normalized) is None
        ):
            return PolicyDecision(
                allowed=False,
                risk_level=risk,
                reason_code="ACTION_NOT_DECLARED",
                message=f"Validation action {normalized!r} is not declared in the manifest.",
            )

        if risk is RiskLevel.R3:
            if not explicit:
                return PolicyDecision(
                    allowed=False,
                    risk_level=risk,
                    reason_code="EXPLICIT_PERMISSION_REQUIRED",
                    message="R3 publication requires explicit method input for this operation.",
                )
            branch_name = (branch or "").removeprefix("refs/heads/").casefold()
            prohibited_branches = {"main", "master"}
            if default_branch:
                prohibited_branches.add(default_branch.removeprefix("refs/heads/").casefold())
            if branch_name and branch_name in prohibited_branches:
                return PolicyDecision(
                    allowed=False,
                    risk_level=risk,
                    reason_code="DEFAULT_BRANCH_PROHIBITED",
                    message="Direct commits to a default branch are prohibited.",
                )
            if project_manifest is not None:
                policy_key = "allow_push" if normalized == "push" else "allow_local_branch"
                if project_manifest.publication_policy.get(policy_key) is not True:
                    return PolicyDecision(
                        allowed=False,
                        risk_level=risk,
                        reason_code="PUBLICATION_POLICY_DENIED",
                        message=f"Project publication policy {policy_key!r} is disabled.",
                    )

        return PolicyDecision(
            allowed=True,
            risk_level=risk,
            reason_code="ALLOWED",
            message="The action is allowed within the active project and job scope.",
        )

    def evaluate(self, *args: Any, **kwargs: Any) -> PolicyDecision:
        return self.decide(*args, **kwargs)

    def check_path(
        self,
        manifest: ProjectManifest,
        path: str,
        operation: str = "read",
    ) -> PolicyDecision:
        return self.decide(operation, manifest, path=path)


def assess_action(
    action: str,
    manifest: ProjectManifest,
    **kwargs: Any,
) -> PolicyDecision:
    return PolicyEngine().decide(action, manifest, **kwargs)
