from __future__ import annotations

import asyncio
from pathlib import Path

from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.mcp_server import create_mcp_server

EXPECTED_TOOLS = {
    "gateway_get_status",
    "gateway_list_projects",
    "gateway_register_project",
    "gateway_get_project",
    "gateway_prepare_task",
    "gateway_get_job",
    "gateway_list_workspace_files",
    "gateway_search_workspace",
    "gateway_read_workspace_file",
    "gateway_write_workspace_file",
    "gateway_move_workspace_file",
    "gateway_request_delete",
    "gateway_get_diff",
    "gateway_validate",
    "gateway_get_evidence",
    "gateway_publish_local_branch",
}

FORBIDDEN_TOOLS = {
    "run_any_command",
    "execute_python",
    "execute_shell",
    "browse_entire_machine",
    "delete_source_path",
    "deploy",
    "merge",
    "force_push",
    "read_credentials",
}


def test_mcp_registers_only_explicit_high_level_gateway_tools(tmp_path: Path) -> None:
    server = create_mcp_server(GatewayConfig.from_root(tmp_path / "gateway"))
    tools = asyncio.run(server.list_tools())
    by_name = {tool.name: tool for tool in tools}

    assert set(by_name) == EXPECTED_TOOLS
    assert not FORBIDDEN_TOOLS & set(by_name)
    assert all(tool.description and tool.inputSchema for tool in tools)
    assert by_name["gateway_get_status"].annotations.readOnlyHint is True
    assert by_name["gateway_read_workspace_file"].annotations.readOnlyHint is True
    assert by_name["gateway_write_workspace_file"].annotations.readOnlyHint is False
    assert by_name["gateway_request_delete"].annotations.destructiveHint is False


def test_mcp_status_handler_delegates_to_the_gateway_service(tmp_path: Path) -> None:
    server = create_mcp_server(GatewayConfig.from_root(tmp_path / "gateway"))

    result = asyncio.run(server.call_tool("gateway_get_status", {}))

    content, structured = result
    assert content
    assert structured["system_id"] == "universal-project-gateway"
    assert structured["status"] == "ready"
    assert structured["risk_boundary"]["prohibited"] == ["R4"]
