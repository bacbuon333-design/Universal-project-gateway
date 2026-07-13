from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from universal_project_gateway.manifests import (
    ManifestValidationError,
    load_manifest,
    validate_manifest,
    validate_manifest_data,
)
from universal_project_gateway.registry import (
    DuplicateProjectError,
    ProjectRegistry,
    RegisteredManifestChangedError,
    UnregisteredPathError,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PYTHON_MANIFEST = REPOSITORY_ROOT / "fixtures" / "python_demo" / "PROJECT_MANIFEST.yaml"
NODE_MANIFEST = REPOSITORY_ROOT / "fixtures" / "node_demo" / "PROJECT_MANIFEST.yaml"


def _valid_data() -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "project_id": "sample-project",
        "name": "Sample",
        "description": "A harmless fixture",
        "project_type": "python",
        "sources": {"local_path": ".", "github_repository": None},
        "stack": {"language": "Python"},
        "important_paths": ["src/example.py"],
        "entrypoints": {"library": "src/example.py"},
        "memory_files": ["AGENTS.md"],
        "commands": {
            "install": None,
            "lint": {"argv": ["python", "-m", "compileall", "src"]},
            "test": {"argv": ["python", "-m", "pytest"]},
            "build": None,
            "smoke_test": None,
        },
        "permissions": {
            "read": True,
            "workspace_write": True,
            "validation": True,
            "git_publish": False,
        },
        "protected_paths": [".env", "secrets/"],
        "validation_requirements": ["test"],
        "publication_policy": {
            "allow_local_branch": False,
            "allow_push": False,
            "allow_merge": False,
        },
        "runtime_adapters": ["python"],
        "state_file": None,
    }


def _write_manifest(directory: Path, data: dict[str, object]) -> Path:
    directory.mkdir(parents=True)
    path = directory / "PROJECT_MANIFEST.yaml"
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


@pytest.mark.parametrize("path", [PYTHON_MANIFEST, NODE_MANIFEST])
def test_foundation_fixture_manifests_are_valid(path: Path) -> None:
    result = validate_manifest(path)

    assert result.valid, result.to_dict()
    assert result.manifest is not None
    assert result.manifest.local_path == path.parent.resolve()
    assert result.manifest.command("test") is not None
    assert result.manifest.command("test").argv


def test_foundation_manifest_returns_multiple_structured_errors() -> None:
    data = _valid_data()
    data["project_id"] = "../Unsafe ID"
    data["important_paths"] = ["../outside.py"]
    data["commands"] = {**data["commands"], "test": "python -m pytest"}  # type: ignore[arg-type]
    data["api_token"] = "do-not-store-this"

    result = validate_manifest_data(data)
    codes = {error.code for error in result.errors}

    assert not result.valid
    assert {
        "INVALID_PROJECT_ID",
        "UNSAFE_RELATIVE_PATH",
        "COMMAND_MUST_USE_ARGV",
        "SECRET_FIELD_FORBIDDEN",
        "MISSING_VALIDATION_COMMAND",
    } <= codes
    assert all(error.path and error.message for error in result.errors)
    assert result.to_dict()["errors"][0]["field"]


def test_foundation_manifest_rejects_arbitrary_execution_and_credentials() -> None:
    data = _valid_data()
    commands = copy.deepcopy(data["commands"])
    assert isinstance(commands, dict)
    commands["test"] = {"argv": ["python", "-c", "print('unsafe')"]}
    data["commands"] = commands
    data["sources"] = {
        "local_path": ".",
        "github_repository": "https://user:password@example.invalid/repository",
    }

    result = validate_manifest_data(data)
    codes = {error.code for error in result.errors}

    assert "EMBEDDED_CREDENTIAL_FORBIDDEN" in codes
    assert "ARBITRARY_PYTHON_FORBIDDEN" in codes


def test_foundation_load_manifest_raises_structured_error(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path / "source", {**_valid_data(), "schema_version": "99"})

    with pytest.raises(ManifestValidationError) as raised:
        load_manifest(path)

    assert raised.value.code == "INVALID_MANIFEST"
    assert raised.value.errors
    assert raised.value.to_dict()["details"]["errors"]


def test_foundation_registry_persists_and_resolves_exact_paths(tmp_path: Path) -> None:
    registry_path = tmp_path / "state" / "projects.yaml"
    registry = ProjectRegistry(registry_path)

    record = registry.register(PYTHON_MANIFEST)
    reloaded = ProjectRegistry(registry_path)

    assert reloaded.get("python-demo") == record
    assert reloaded.list() == [record]
    assert reloaded.resolve("python-demo") == record
    assert reloaded.resolve_path(PYTHON_MANIFEST.parent) == record
    assert reloaded.get_manifest("python-demo").project_id == "python-demo"
    with pytest.raises(UnregisteredPathError):
        reloaded.resolve_path(PYTHON_MANIFEST.parent / "src")


def test_foundation_registry_rejects_duplicate_project_id(tmp_path: Path) -> None:
    registry = ProjectRegistry(tmp_path / "projects.yaml")
    registry.register(PYTHON_MANIFEST)

    with pytest.raises(DuplicateProjectError) as raised:
        registry.register(PYTHON_MANIFEST)

    assert raised.value.code == "DUPLICATE_PROJECT_ID"
    assert len(registry.list()) == 1


def test_foundation_registry_detects_manifest_changes_after_registration(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    path = _write_manifest(source, _valid_data())
    registry = ProjectRegistry(tmp_path / "projects.yaml")
    registry.register(path)
    path.write_text(path.read_text(encoding="utf-8") + "\n# changed\n", encoding="utf-8")

    with pytest.raises(RegisteredManifestChangedError) as raised:
        registry.get_manifest("sample-project")

    assert raised.value.code == "REGISTERED_MANIFEST_CHANGED"
