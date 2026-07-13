from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from universal_project_gateway.intent import IntentCompiler, InvalidIntentError
from universal_project_gateway.manifests import load_manifest
from universal_project_gateway.models import ProjectPermissions, PublicationMode, RiskLevel
from universal_project_gateway.policy import PolicyEngine, classify_action

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def manifest():
    return load_manifest(REPOSITORY_ROOT / "fixtures" / "python_demo" / "PROJECT_MANIFEST.yaml")


def test_foundation_intent_normalizes_a_clear_edit_deterministically() -> None:
    compiler = IntentCompiler()

    first = compiler.compile(
        "python-demo",
        "Change the greeting in the target file.",
        target_paths=["src\\greeting.py", "src/greeting.py"],
        required_validation=["test", "test"],
    )
    second = compiler.compile(
        "python-demo",
        "Change the greeting in the target file.",
        target_paths=["src/greeting.py"],
        required_validation=["test"],
    )

    assert first == second
    assert first.task_type == "modification"
    assert first.target_scope == ("src/greeting.py",)
    assert first.expected_operations == ("read_files", "write_files")
    assert first.risk_level is RiskLevel.R1
    assert first.publication_mode is PublicationMode.NONE
    assert not first.requires_ai_planning


def test_foundation_intent_classifies_validation_publication_and_r4() -> None:
    compiler = IntentCompiler()

    validation = compiler.compile("python-demo", "Run the tests", requested_operation="test")
    publication = compiler.compile(
        "python-demo", "Commit this change", publication_preference="local_commit"
    )
    destructive = compiler.compile("python-demo", "Delete the source and deploy it")

    assert validation.risk_level is RiskLevel.R2
    assert publication.risk_level is RiskLevel.R3
    assert destructive.risk_level is RiskLevel.R4
    assert destructive.task_type == "prohibited"


def test_foundation_intent_marks_uncertain_requests_and_rejects_escape() -> None:
    compiler = IntentCompiler()

    uncertain = compiler.compile("python-demo", "Make it nicer somehow")
    assert uncertain.requires_ai_planning
    assert uncertain.task_type == "unknown"

    with pytest.raises(InvalidIntentError) as raised:
        compiler.compile("python-demo", "Inspect it", target_paths=["../outside.txt"])
    assert raised.value.code == "UNSAFE_TARGET_PATH"


def test_foundation_policy_allows_only_manifest_permitted_scope(manifest) -> None:
    policy = PolicyEngine()

    assert policy.decide("read", manifest, path="src/greeting.py").allowed
    assert policy.decide("write", manifest, path="src/greeting.py").allowed
    assert policy.decide("test", manifest).allowed

    protected = policy.decide("read", manifest, path="secrets/key.txt")
    escaped = policy.decide("write", manifest, path="../source.py")
    assert not protected.allowed and protected.reason_code == "PROTECTED_PATH"
    assert not escaped.allowed and escaped.reason_code == "PATH_OUTSIDE_SCOPE"
    assert escaped.risk_level is RiskLevel.R4


@pytest.mark.parametrize("action", ["delete", "request_delete", "merge", "force_push", "deploy"])
def test_foundation_policy_prohibits_r4_globally(manifest, action: str) -> None:
    decision = PolicyEngine().decide(action, manifest, explicit=True)

    assert decision.to_dict() == {
        "allowed": False,
        "risk_level": "R4",
        "reason_code": "ACTION_PROHIBITED",
        "message": decision.message,
    }
    assert classify_action(action) is RiskLevel.R4


def test_foundation_policy_r3_needs_project_policy_explicit_input_and_safe_branch(
    manifest,
) -> None:
    permissions = ProjectPermissions(True, True, True, True)
    publishable = replace(
        manifest,
        permissions=permissions,
        publication_policy={
            "allow_local_branch": True,
            "allow_push": False,
            "allow_merge": False,
        },
    )
    policy = PolicyEngine()

    assert policy.decide("local_commit", publishable).reason_code == "EXPLICIT_PERMISSION_REQUIRED"
    assert (
        policy.decide(
            "local_commit",
            publishable,
            explicit=True,
            branch="main",
            default_branch="main",
        ).reason_code
        == "DEFAULT_BRANCH_PROHIBITED"
    )
    assert policy.decide(
        "local_commit", publishable, explicit=True, branch="agent/job-safe"
    ).allowed
