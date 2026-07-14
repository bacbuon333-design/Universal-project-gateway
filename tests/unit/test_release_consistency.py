from __future__ import annotations

import json
import tomllib
from pathlib import Path

from universal_project_gateway import __version__

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_VERSION = "0.2.0+local"
RELEASE_TAG = "v0.2.0-local"
REAL_PROJECT_CHECKPOINT = "9d1414ef3056888ff5c651466ea688f53317fb65"


def test_release_version_metadata_is_consistent() -> None:
    project = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    state = json.loads(
        (REPOSITORY_ROOT / "state" / "CURRENT_STATE.json").read_text(encoding="utf-8")
    )

    assert project["project"]["version"] == PACKAGE_VERSION
    assert __version__ == PACKAGE_VERSION
    assert state["mvp_version"] == PACKAGE_VERSION
    assert state["release_candidate"]["package_version"] == PACKAGE_VERSION
    assert state["release_candidate"]["reserved_git_tag"] == RELEASE_TAG
    assert state["release_candidate"]["tag_policy"] == (
        "do_not_create_move_or_delete_in_upg_v02_rc_001"
    )
    assert state["release_candidate"]["v0_1_9_tag_target"] == REAL_PROJECT_CHECKPOINT
    assert state["release_candidate"]["v0_1_9_verified"] is True


def test_release_documents_preserve_the_local_trusted_project_boundary() -> None:
    release_notes_path = REPOSITORY_ROOT / "docs" / "RELEASE_NOTES_v0.2.0-local.md"
    readiness_path = REPOSITORY_ROOT / "docs" / "LOCAL_V02_READINESS.md"
    release_notes = release_notes_path.read_text(encoding="utf-8")

    assert release_notes_path.is_file()
    assert readiness_path.is_file()
    for heading in (
        "## What is ready",
        "## What is not ready",
        "## Sandbox status",
        "## Evidence status",
        "## Project intelligence status",
        "## External-project integration status",
        "## Recommended next phases",
    ):
        assert heading in release_notes
    for boundary in (
        "trusted local projects",
        "no public or remote MCP endpoint",
        "not approved for untrusted project execution",
        RELEASE_TAG,
    ):
        assert boundary in release_notes
