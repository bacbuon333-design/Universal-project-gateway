from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import yaml

from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.manifests import load_manifest, validate_manifest
from universal_project_gateway.registry import ProjectRegistry
from universal_project_gateway.service import GatewayService

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ROOT_MANIFEST = REPOSITORY_ROOT / "PROJECT_MANIFEST.yaml"
SEED_REGISTRY = REPOSITORY_ROOT / "registry" / "projects.yaml"


def test_root_manifest_loads_with_allowlisted_validation() -> None:
    result = validate_manifest(ROOT_MANIFEST)

    assert result.valid, result.to_dict()
    manifest = load_manifest(ROOT_MANIFEST)
    assert manifest.project_id == "universal-project-gateway"
    assert manifest.project_type == "python"
    assert manifest.local_path == REPOSITORY_ROOT
    assert manifest.runtime_adapters == ("python",)
    assert manifest.validation_requirements == ("lint", "test")
    assert manifest.permissions.read is True
    assert manifest.permissions.workspace_write is True
    assert manifest.permissions.validation is True
    assert manifest.publication_policy == {
        "allow_local_branch": True,
        "allow_push": False,
        "allow_merge": False,
    }

    managed = manifest.stack["managed_path_groups"]
    assert managed == {
        "source": ["src/universal_project_gateway/"],
        "documentation": ["README.md", "docs/", "state/CURRENT_STATE.json"],
        "tests": ["tests/"],
        "scripts": [
            "scripts/",
            "REGISTER_PROJECT.bat",
            "RUN_DEMO.bat",
            "START_GATEWAY.bat",
            "VERIFY_GATEWAY.bat",
        ],
    }
    for action in manifest.validation_requirements:
        command = manifest.command(action)
        assert command is not None
        assert command.argv[0:2] == ("python", "-m")
        assert command.argv[2] in {"compileall", "pytest"}


def test_seed_registry_contains_portable_upg_registration() -> None:
    document = yaml.safe_load(SEED_REGISTRY.read_text(encoding="utf-8"))

    assert document["schema_version"] == "1.0"
    assert [project["project_id"] for project in document["projects"]] == [
        "universal-project-gateway"
    ]
    assert document["projects"][0]["manifest_path"] == "PROJECT_MANIFEST.yaml"
    assert document["projects"][0]["local_path"] == "."
    assert document["projects"][0]["manifest_sha256"] == hashlib.sha256(
        ROOT_MANIFEST.read_bytes()
    ).hexdigest()

    registry = ProjectRegistry(SEED_REGISTRY, path_base=REPOSITORY_ROOT)
    record = registry.get("universal-project-gateway")
    assert record.local_path == REPOSITORY_ROOT
    assert record.manifest_path == ROOT_MANIFEST
    assert registry.get_manifest(record.project_id).project_id == record.project_id


def test_upg_project_can_be_registered_in_a_fresh_registry(tmp_path: Path) -> None:
    registry = ProjectRegistry(tmp_path / "projects.yaml")

    registered = registry.register(ROOT_MANIFEST)

    assert registered.project_id == "universal-project-gateway"
    assert registry.list() == [registered]
    assert registry.get_manifest(registered.project_id).local_path == REPOSITORY_ROOT


def test_seeded_upg_project_prepares_an_isolated_self_management_workspace(
    tmp_path: Path,
) -> None:
    base = GatewayConfig.from_root(REPOSITORY_ROOT)
    config = replace(
        base,
        registry_path=tmp_path / "var" / "registry" / "projects.yaml",
        database_path=tmp_path / "var" / "gateway.db",
        workspaces_root=tmp_path / "workspaces" / "jobs",
        artifacts_root=tmp_path / "artifacts" / "jobs",
    )
    gateway = GatewayService(config)
    source_before = ROOT_MANIFEST.read_bytes()

    prepared = gateway.prepare_task(
        "universal-project-gateway",
        "Inspect the UPG self-registration metadata.",
        target_paths=["PROJECT_MANIFEST.yaml", "registry/projects.yaml"],
        requested_operation="inspect",
    )

    workspace = Path(prepared["workspace"])
    assert prepared["job"]["status"] == "prepared"
    assert prepared["intent"]["risk_level"] == "R0"
    assert prepared["intent"]["required_validation"] == ["lint", "test"]
    assert workspace.parent.parent == config.workspaces_root
    assert (workspace / "PROJECT_MANIFEST.yaml").is_file()
    assert (workspace / "registry" / "projects.yaml").is_file()
    assert not (workspace / ".git").exists()
    assert not (workspace / ".venv").exists()
    assert not (workspace / "var").exists()
    assert not (workspace / "artifacts").exists()
    assert not (workspace / "workspaces").exists()
    assert ROOT_MANIFEST.read_bytes() == source_before
