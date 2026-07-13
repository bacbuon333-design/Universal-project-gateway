from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from universal_project_gateway.context import ContextCompiler
from universal_project_gateway.evidence import EVIDENCE_FILES, EvidenceLedger
from universal_project_gateway.models import CommandSpec
from universal_project_gateway.runtime.node_adapter import NodeAdapter
from universal_project_gateway.runtime.python_adapter import PythonAdapter
from universal_project_gateway.scoped_fs import ScopedWorkspace
from universal_project_gateway.workspaces import WorkspaceManager


def test_workspace_edit_diff_is_snapshot_backed_and_reports_stale_source(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    target = source / "src" / "greeting.py"
    target.write_text('def greeting():\n    return "Hello"\n', encoding="utf-8")

    manager = WorkspaceManager(tmp_path / "jobs")
    snapshot = manager.create("job-diff", source)
    scoped = ScopedWorkspace(snapshot.workspace_root)
    scoped.replace_in_text("src/greeting.py", '"Hello"', '"Hello from UPG"')

    first = manager.diff("job-diff")
    second = manager.diff("job-diff")
    assert first.patch == second.patch
    assert first.files_changed[0]["change_type"] == "modified"
    assert "-    return \"Hello\"" in first.patch
    assert "+    return \"Hello from UPG\"" in first.patch
    assert target.read_text(encoding="utf-8").endswith('return "Hello"\n')
    assert first.stale_source_warning is False

    target.write_text('def greeting():\n    return "source changed"\n', encoding="utf-8")
    stale = manager.diff("job-diff")
    assert stale.patch == first.patch
    assert stale.stale_source_warning is True
    assert stale.stale_source_details["changed_paths"] == ["src/greeting.py"]


def test_context_pack_is_bounded_and_excludes_protected_and_dependency_content(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "src" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / "AGENTS.md").write_text("project memory\n", encoding="utf-8")
    (source / ".env").write_text("TOKEN=never-copy\n", encoding="utf-8")
    (source / "node_modules").mkdir()
    (source / "node_modules" / "package.js").write_text("secret dependency", encoding="utf-8")
    manifest = {
        "project_id": "bounded-demo",
        "memory_files": ["AGENTS.md"],
        "important_paths": ["src"],
        "protected_paths": [".env"],
        "validation_requirements": ["test"],
        "publication_policy": {"allow_local_branch": False},
        "state_file": None,
    }
    intent = {"target_scope": ["src/app.py"], "risk_level": "R1"}

    pack = ContextCompiler(max_files=20, max_total_bytes=1_000).compile(
        source,
        manifest,
        intent,
    )

    tree_paths = {item["path"] for item in pack["project_tree"]}
    selected_paths = {item["path"] for item in pack["selected_files"]}
    omitted = {(item["path"], item["reason"]) for item in pack["omitted_paths"]}
    assert tree_paths == {"AGENTS.md", "src/app.py"}
    assert selected_paths == {"AGENTS.md", "src", "src/app.py"}
    assert (".env", "protected") in omitted
    assert ("node_modules", "excluded") in omitted
    assert "never-copy" not in json.dumps(pack)
    assert "not a claim of full-repository understanding" in pack["scope_statement"]


def test_python_adapter_runs_only_the_declared_unittest_action(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    tests = workspace / "tests"
    tests.mkdir(parents=True)
    (tests / "test_ok.py").write_text(
        "import unittest\n\n"
        "class TestOk(unittest.TestCase):\n"
        "    def test_ok(self):\n"
        "        self.assertEqual(2 + 2, 4)\n",
        encoding="utf-8",
    )
    adapter = PythonAdapter(
        workspace,
        {"test": CommandSpec(("python", "-m", "unittest", "discover", "-s", "tests"))},
    )

    result = adapter.run_tests()
    assert result.status == "passed"
    assert result.returncode == 0
    assert result.argv[1:4] == ("-m", "unittest", "discover")
    assert adapter.run_build().status == "not_run"


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_node_adapter_runs_builtin_test_runner_without_a_shell(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "greeting.test.js").write_text(
        "const test = require('node:test');\n"
        "const assert = require('node:assert/strict');\n"
        "test('works', () => assert.equal(2 + 2, 4));\n",
        encoding="utf-8",
    )
    adapter = NodeAdapter(workspace, {"test": CommandSpec(("node", "--test"))})

    result = adapter.run_tests()
    assert result.status == "passed"
    assert result.returncode == 0
    assert result.argv[1:] == ("--test",)


def test_evidence_finalize_creates_complete_verifiable_bundle(tmp_path: Path) -> None:
    ledger = EvidenceLedger(tmp_path / "evidence")
    ledger.initialize("job-evidence", task={"request": "safe edit"})
    ledger.write("job-evidence", "patch.diff", "--- a/file\n+++ b/file\n")
    manifest_path = ledger.finalize(
        "job-evidence", final_report={"status": "completed", "success": True}
    )

    evidence_path = ledger.job_path("job-evidence")
    assert {path.name for path in evidence_path.iterdir()} == {
        *EVIDENCE_FILES,
        "manifest.sha256.json",
    }
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert list(manifest["files"]) == sorted(EVIDENCE_FILES)
    assert ledger.verify("job-evidence").valid is True
