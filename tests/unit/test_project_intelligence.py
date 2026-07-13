from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

import universal_project_gateway.context as context_module
from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.context import ContextCompiler
from universal_project_gateway.contracts import PROJECT_INTELLIGENCE_CONTRACT_VERSION
from universal_project_gateway.intelligence import (
    ProjectIntelligenceCache,
    ProjectIntelligenceError,
    ProjectIntelligenceScanner,
)
from universal_project_gateway.manifests import load_manifest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _copy_fixture(tmp_path: Path, name: str) -> Path:
    source = tmp_path / name
    shutil.copytree(REPOSITORY_ROOT / "fixtures" / name, source)
    return source


def _all_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _all_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _all_strings(child)]
    return []


def test_upg_intelligence_is_bounded_relative_and_versioned(tmp_path: Path) -> None:
    manifest = load_manifest(REPOSITORY_ROOT / "PROJECT_MANIFEST.yaml")
    cache = ProjectIntelligenceCache(GatewayConfig.from_root(tmp_path / "gateway"))

    result = cache.generate(manifest)
    document = result["intelligence"]

    assert document["schema_version"] == PROJECT_INTELLIGENCE_CONTRACT_VERSION
    assert document["project_id"] == "universal-project-gateway"
    assert document["manifest_path"] == "PROJECT_MANIFEST.yaml"
    assert document["source_root"] == "."
    assert document["module_summary"]["top_level_packages"] == [
        "universal_project_gateway"
    ]
    assert "pyproject.toml" in document["dependency_files"]
    assert "fixtures/node_demo/package.json" not in document["dependency_files"]
    assert all("__pycache__" not in path for path in document["test_summary"]["paths"])
    assert document["scan"]["files_fingerprinted"] <= document["scan"]["limits"][
        "max_files"
    ]
    assert Path(result["cache_path"]).parent == cache.root
    assert all(str(REPOSITORY_ROOT) not in value for value in _all_strings(document))


@pytest.mark.parametrize(
    ("fixture_name", "adapter_id", "dependency_file", "module_path"),
    [
        ("python_demo", "python", None, "src/greeting.py"),
        ("node_demo", "node", "package.json", "src/greeting.js"),
    ],
)
def test_fixture_intelligence_reports_runtime_and_module_hints(
    tmp_path: Path,
    fixture_name: str,
    adapter_id: str,
    dependency_file: str | None,
    module_path: str,
) -> None:
    source = _copy_fixture(tmp_path, fixture_name)
    document = ProjectIntelligenceScanner().scan(
        load_manifest(source / "PROJECT_MANIFEST.yaml")
    )

    assert document["runtime_adapters"] == [adapter_id]
    assert document["adapter_capabilities"][0]["adapter_id"] == adapter_id
    assert module_path in document["module_summary"]["module_paths"]
    assert document["test_summary"]["file_count"] >= 1
    if dependency_file is not None:
        assert dependency_file in document["dependency_files"]


def test_refresh_changes_source_fingerprint_but_stable_content_keeps_cache_hash(
    tmp_path: Path,
) -> None:
    source = _copy_fixture(tmp_path, "python_demo")
    manifest = load_manifest(source / "PROJECT_MANIFEST.yaml")
    cache = ProjectIntelligenceCache(GatewayConfig.from_root(tmp_path / "gateway"))

    first = cache.generate(manifest)["intelligence"]
    unchanged = cache.generate(manifest)["intelligence"]
    (source / "src" / "greeting.py").write_text(
        'def greeting():\n    return "changed"\n', encoding="utf-8"
    )
    changed = cache.generate(manifest)["intelligence"]

    assert unchanged["source_fingerprint"] == first["source_fingerprint"]
    assert unchanged["cache_hash"] == first["cache_hash"]
    assert changed["source_fingerprint"] != first["source_fingerprint"]
    assert changed["cache_hash"] != first["cache_hash"]


def test_tampered_cache_is_rejected(tmp_path: Path) -> None:
    source = _copy_fixture(tmp_path, "node_demo")
    cache = ProjectIntelligenceCache(GatewayConfig.from_root(tmp_path / "gateway"))
    result = cache.generate(load_manifest(source / "PROJECT_MANIFEST.yaml"))
    path = Path(result["cache_path"])
    document = json.loads(path.read_text(encoding="utf-8"))
    document["project_name"] = "tampered"
    path.write_text(json.dumps(document), encoding="utf-8")

    with pytest.raises(ProjectIntelligenceError) as exc_info:
        cache.get("node-demo")

    assert exc_info.value.code == "PROJECT_INTELLIGENCE_CACHE_INVALID"


def test_scanner_never_reads_protected_paths_or_executes_project_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _copy_fixture(tmp_path, "python_demo")
    protected = source / "secrets"
    protected.mkdir()
    secret = protected / "do-not-read.txt"
    secret.write_text("never-ingest", encoding="utf-8")
    manifest = load_manifest(source / "PROJECT_MANIFEST.yaml")
    original_open = Path.open

    def guarded_open(path: Path, *args: object, **kwargs: object):
        if protected in (path, *path.parents):
            raise AssertionError("protected content was opened")
        return original_open(path, *args, **kwargs)

    def forbidden_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("project execution is forbidden during intelligence generation")

    monkeypatch.setattr(Path, "open", guarded_open)
    monkeypatch.setattr(subprocess, "run", forbidden_run)

    document = ProjectIntelligenceScanner().scan(manifest)

    assert document["scan"]["omitted_path_count"] >= 1
    assert "never-ingest" not in json.dumps(document)


def test_context_compiler_embeds_only_compact_intelligence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _copy_fixture(tmp_path, "python_demo")
    manifest = load_manifest(source / "PROJECT_MANIFEST.yaml")
    cache = ProjectIntelligenceCache(GatewayConfig.from_root(tmp_path / "gateway"))
    compact = cache.compact(cache.generate(manifest))

    def forbidden_walk(*args: object, **kwargs: object):
        raise AssertionError("cached context must not walk the full project tree")

    monkeypatch.setattr(context_module, "_walk_project", forbidden_walk)

    pack = ContextCompiler(max_files=20, max_total_bytes=10_000).compile(
        source,
        manifest,
        {"target_scope": ["src/greeting.py"], "risk_level": "R0"},
        project_intelligence=compact,
    )

    intelligence = pack["project_intelligence"]
    assert intelligence["schema_version"] == PROJECT_INTELLIGENCE_CONTRACT_VERSION
    assert intelligence["cache_hash"] == compact["cache_hash"]
    assert "test_commands" not in intelligence
    assert len(json.dumps(intelligence)) < 20_000
