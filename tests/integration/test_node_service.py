from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from universal_project_gateway.service import GatewayService


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_node_fixture_uses_the_same_service_vertical_slice(
    gateway_factory: Callable[[str], tuple[GatewayService, Path]],
) -> None:
    gateway, source = gateway_factory("node_demo")
    source_target = source / "src" / "greeting.js"
    source_before = source_target.read_bytes()
    prepared = gateway.prepare_task(
        "node-demo",
        "Change the greeting and run the tests",
        target_paths=["src/greeting.js"],
        requested_operation="edit",
    )
    job_id = prepared["job"]["job_id"]

    gateway.replace_workspace_text(
        job_id,
        "src/greeting.js",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )
    diff = gateway.get_diff(job_id)
    validation = gateway.validate(job_id)

    assert [item["path"] for item in diff["files_changed"]] == ["src/greeting.js"]
    assert 'return "Hello from UPG"' in diff["patch"]
    assert validation["passed"] is True
    assert validation["evidence_verified"] is True
    assert validation["checks"][0]["argv"][0].lower().endswith(("node", "node.exe"))
    assert validation["checks"][0]["argv"][1:] == [
        "--test",
        "tests/greeting.test.js",
    ]
    assert validation["checks"][0]["adapter"]["adapter_id"] == "node"
    assert validation["checks"][0]["adapter"]["resolved_capability"] == "test"
    assert gateway.get_evidence(job_id)["verified"] is True
    assert source_target.read_bytes() == source_before
