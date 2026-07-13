from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from universal_project_gateway.cli import main as cli_main
from universal_project_gateway.contracts import (
    ADAPTER_CONTRACT_VERSION,
    CONTRACT_VERSIONS,
    EVIDENCE_CONTRACT_VERSION,
    EXECUTION_CONTRACT_VERSION,
    MANIFEST_CONTRACT_VERSION,
    PROJECT_INTELLIGENCE_CONTRACT_VERSION,
    get_contract_schema,
)
from universal_project_gateway.manifests import load_manifest, validate_manifest_data
from universal_project_gateway.runtime import built_in_adapter_registry

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PYTHON_MANIFEST = REPOSITORY_ROOT / "fixtures" / "python_demo" / "PROJECT_MANIFEST.yaml"
NODE_MANIFEST = REPOSITORY_ROOT / "fixtures" / "node_demo" / "PROJECT_MANIFEST.yaml"


def _fixture_data(path: Path) -> dict[str, object]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict)
    return document


def test_versioned_contract_constants_have_isolated_schemas() -> None:
    assert dict(CONTRACT_VERSIONS) == {
        "manifest": "upg.manifest/v1",
        "adapter": "upg.adapter/v1",
        "execution": "upg.execution/v1",
        "evidence": "upg.evidence/v1",
        "project_intelligence": "upg.project_intelligence/v1",
    }
    for version in (
        MANIFEST_CONTRACT_VERSION,
        ADAPTER_CONTRACT_VERSION,
        EXECUTION_CONTRACT_VERSION,
        EVIDENCE_CONTRACT_VERSION,
        PROJECT_INTELLIGENCE_CONTRACT_VERSION,
    ):
        schema = get_contract_schema(version)
        assert schema["$id"] == version
        schema["$id"] = "changed"
        assert get_contract_schema(version)["$id"] == version
    with pytest.raises(ValueError, match="Unknown UPG contract"):
        get_contract_schema("upg.unknown/v1")


def test_builtin_python_and_node_adapters_declare_versioned_capabilities() -> None:
    registry = built_in_adapter_registry()
    capabilities = {item.adapter_id: item for item in registry.list_capabilities()}

    assert list(capabilities) == ["node", "python"]
    assert capabilities["python"].contract_version == ADAPTER_CONTRACT_VERSION
    assert capabilities["python"].adapter_version == "1.0.0"
    assert {"inspect", "lint", "test", "build", "smoke"} <= set(
        capabilities["python"].capabilities
    )
    assert capabilities["node"].contract_version == ADAPTER_CONTRACT_VERSION
    assert capabilities["node"].required_tools == ("node>=18",)


@pytest.mark.parametrize(
    ("manifest_path", "adapter_id"),
    [(PYTHON_MANIFEST, "python"), (NODE_MANIFEST, "node")],
)
def test_capability_lookup_resolves_fixture_validation(
    manifest_path: Path,
    adapter_id: str,
) -> None:
    manifest = load_manifest(manifest_path)

    resolution = built_in_adapter_registry().resolve(manifest, "test")

    assert resolution.adapter.adapter_id == adapter_id
    assert resolution.capability == "test"
    assert resolution.runtime_action == "test"
    assert resolution.to_dict()["contract_version"] == ADAPTER_CONTRACT_VERSION


def test_unknown_adapter_and_capability_are_rejected_by_manifest_validation() -> None:
    unknown_adapter = _fixture_data(PYTHON_MANIFEST)
    unknown_adapter["runtime_adapters"] = ["missing-adapter"]
    adapter_result = validate_manifest_data(unknown_adapter)

    unsupported_capability = _fixture_data(PYTHON_MANIFEST)
    unsupported_capability["adapter_requirements"] = [
        {
            "adapter_id": "python",
            "contract_version": ADAPTER_CONTRACT_VERSION,
            "capabilities": ["deploy"],
        }
    ]
    capability_result = validate_manifest_data(unsupported_capability)

    assert "UNKNOWN_RUNTIME_ADAPTER" in {issue.code for issue in adapter_result.errors}
    assert "ADAPTER_CAPABILITY_UNSUPPORTED" in {
        issue.code for issue in capability_result.errors
    }


def test_manifest_adapter_expectations_are_optional_but_enforced_when_present() -> None:
    legacy = validate_manifest_data(_fixture_data(PYTHON_MANIFEST))
    versioned = _fixture_data(PYTHON_MANIFEST)
    versioned["contract_version"] = MANIFEST_CONTRACT_VERSION
    versioned["adapter_requirements"] = [
        {
            "adapter_id": "python",
            "adapter_version": "1.0.0",
            "contract_version": ADAPTER_CONTRACT_VERSION,
            "capabilities": ["lint", "test"],
        }
    ]
    versioned_result = validate_manifest_data(versioned)
    incompatible = _fixture_data(PYTHON_MANIFEST)
    incompatible["adapter_requirements"] = [
        {
            "adapter_id": "python",
            "adapter_version": "99.0.0",
            "contract_version": ADAPTER_CONTRACT_VERSION,
            "capabilities": ["test"],
        }
    ]
    incompatible_result = validate_manifest_data(incompatible)

    assert legacy.valid is True
    assert legacy.manifest is not None
    assert legacy.manifest.contract_version == MANIFEST_CONTRACT_VERSION
    assert legacy.manifest.adapter_requirements == ()
    assert versioned_result.valid is True
    assert versioned_result.manifest is not None
    assert versioned_result.manifest.adapter_requirements[0].capabilities == ("lint", "test")
    assert "ADAPTER_VERSION_INCOMPATIBLE" in {
        issue.code for issue in incompatible_result.errors
    }


def test_cli_lists_adapter_capabilities_without_running_an_action(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = cli_main(["--root", str(tmp_path / "gateway"), "adapter", "list"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert [item["adapter_id"] for item in output] == ["node", "python"]
    assert all(item["contract_version"] == ADAPTER_CONTRACT_VERSION for item in output)
