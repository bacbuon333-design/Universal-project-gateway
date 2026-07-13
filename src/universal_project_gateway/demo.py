"""Deterministic end-to-end demonstration of the Python fixture workflow."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from .config import GatewayConfig
from .service import GatewayService


def demo_config(root: str | Path) -> GatewayConfig:
    """Keep demo registry state isolated while retaining every job artifact."""

    base = GatewayConfig.from_root(root)
    return replace(
        base,
        registry_path=base.root_dir / "var" / "demo" / "projects.yaml",
        database_path=base.root_dir / "var" / "demo" / "gateway.db",
    )


def run_demo(root: str | Path | None = None) -> dict[str, Any]:
    repository_root = Path(root).resolve() if root else Path(__file__).resolve().parents[2]
    config = demo_config(repository_root)
    config.registry_path.unlink(missing_ok=True)
    gateway = GatewayService(config)
    python_manifest = repository_root / "fixtures" / "python_demo" / "PROJECT_MANIFEST.yaml"
    node_manifest = repository_root / "fixtures" / "node_demo" / "PROJECT_MANIFEST.yaml"

    project = gateway.register_project(python_manifest)
    node_project = gateway.register_project(node_manifest)
    print("project registered")
    prepared = gateway.prepare_task(
        project["project_id"],
        'Change the greeting from "Hello" to "Hello from UPG".',
        target_paths=["src/greeting.py"],
        requested_operation="modify",
    )
    job_id = prepared["job"]["job_id"]
    print("job prepared")
    print("workspace created")

    inspected = gateway.read_workspace_file(job_id, "src/greeting.py")
    if 'return "Hello"' not in inspected["content"]:
        raise RuntimeError("Demo fixture did not contain the expected original greeting")
    changed = gateway.replace_workspace_text(
        job_id,
        "src/greeting.py",
        'return "Hello"',
        'return "Hello from UPG"',
        max_replacements=1,
    )
    if changed.get("replacements") != 1:
        raise RuntimeError("Demo edit was not a single bounded replacement")
    print("file modified")

    validation = gateway.validate(job_id)
    if not validation["passed"]:
        raise RuntimeError("Demo fixture validation failed")
    print("validation passed")
    diff = gateway.get_diff(job_id)
    if "Hello from UPG" not in diff.get("patch", ""):
        raise RuntimeError("Demo patch does not contain the intended edit")
    print("patch created")
    evidence = gateway.get_evidence(job_id)
    if not evidence["verified"]:
        raise RuntimeError("Demo evidence checksum verification failed")
    print("evidence verified")
    print(f"job ID: {job_id}")
    print(f"evidence: {evidence['path']}")
    return {
        "success": True,
        "job_id": job_id,
        "registered_projects": [project["project_id"], node_project["project_id"]],
        "evidence_path": evidence["path"],
        "workspace_path": prepared["workspace"],
        "validation": validation,
    }


__all__ = ["demo_config", "run_demo"]
