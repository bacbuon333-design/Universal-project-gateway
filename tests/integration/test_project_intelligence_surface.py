from __future__ import annotations

import asyncio
import json
import shutil
from pathlib import Path

import pytest

from universal_project_gateway.cli import main as cli_main
from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.contracts import PROJECT_INTELLIGENCE_CONTRACT_VERSION
from universal_project_gateway.mcp_server import create_mcp_server
from universal_project_gateway.service import GatewayService

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _registered_fixture(tmp_path: Path) -> tuple[GatewayConfig, Path]:
    source = tmp_path / "source" / "node_demo"
    shutil.copytree(REPOSITORY_ROOT / "fixtures" / "node_demo", source)
    config = GatewayConfig.from_root(tmp_path / "gateway")
    GatewayService(config).register_project(source / "PROJECT_MANIFEST.yaml")
    return config, source


def test_cli_generate_list_and_show_project_intelligence(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config, _ = _registered_fixture(tmp_path)

    generated_code = cli_main(
        ["--root", str(config.root_dir), "intelligence", "generate", "node-demo"]
    )
    generated = json.loads(capsys.readouterr().out)
    list_code = cli_main(["--root", str(config.root_dir), "intelligence", "list"])
    listed = json.loads(capsys.readouterr().out)
    show_code = cli_main(
        ["--root", str(config.root_dir), "intelligence", "show", "node-demo"]
    )
    shown = json.loads(capsys.readouterr().out)

    assert (generated_code, list_code, show_code) == (0, 0, 0)
    assert generated["intelligence"]["schema_version"] == (
        PROJECT_INTELLIGENCE_CONTRACT_VERSION
    )
    assert listed[0]["project_id"] == "node-demo"
    assert shown["intelligence"]["cache_hash"] == generated["intelligence"]["cache_hash"]


def test_mcp_project_intelligence_read_is_read_only_and_does_not_refresh(
    tmp_path: Path,
) -> None:
    config, source = _registered_fixture(tmp_path)
    generated = GatewayService(config).generate_project_intelligence("node-demo")
    server = create_mcp_server(config)
    tools = {tool.name: tool for tool in asyncio.run(server.list_tools())}
    fingerprint = generated["intelligence"]["source_fingerprint"]
    (source / "src" / "greeting.js").write_text(
        "export const greeting = () => 'changed';\n", encoding="utf-8"
    )

    content, structured = asyncio.run(
        server.call_tool("gateway_get_project_intelligence", {"project_id": "node-demo"})
    )

    assert content
    assert tools["gateway_get_project_intelligence"].annotations.readOnlyHint is True
    assert structured["intelligence"]["source_fingerprint"] == fingerprint
