"""Local MCP server exposing only high-level, job-scoped gateway operations."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .config import GatewayConfig
from .service import GatewayService

READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)
SCOPED_WRITE = ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False)


def create_mcp_server(
    config: GatewayConfig | None = None,
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> FastMCP:
    """Build a server whose tool closures share one local gateway service."""

    resolved = config or GatewayConfig.discover()
    gateway = GatewayService(resolved)
    server = FastMCP(
        "Universal Project Gateway",
        instructions=(
            "Discover a registered project, prepare a job, and use only job-relative "
            "workspace operations. Validation actions are manifest allowlists; R4 is prohibited."
        ),
        host=host,
        port=port,
        json_response=True,
        stateless_http=True,
    )

    @server.tool(annotations=READ_ONLY)
    def gateway_get_status() -> dict[str, Any]:
        """Return local Gateway health, version, and supported risk boundary."""

        return gateway.get_status()

    @server.tool(annotations=READ_ONLY)
    def gateway_list_projects() -> list[dict[str, Any]]:
        """List projects already registered with this Gateway instance."""

        return gateway.list_projects()

    @server.tool(annotations=SCOPED_WRITE)
    def gateway_register_project(manifest_path: str) -> dict[str, Any]:
        """Validate and register one PROJECT_MANIFEST.yaml by its exact local path."""

        return gateway.register_project(Path(manifest_path))

    @server.tool(annotations=READ_ONLY)
    def gateway_get_project(project_id: str) -> dict[str, Any]:
        """Get a registered project manifest and registry metadata by exact project ID."""

        return gateway.get_project(project_id)

    @server.tool(annotations=SCOPED_WRITE)
    def gateway_prepare_task(
        project_id: str,
        request: str,
        target_paths: list[str] | None = None,
        requested_operation: str | None = None,
        publication_preference: str = "none",
    ) -> dict[str, Any]:
        """Normalize a task and create its isolated per-job workspace and context pack."""

        return gateway.prepare_task(
            project_id,
            request,
            target_paths=target_paths or [],
            requested_operation=requested_operation,
            publication_preference=publication_preference,
        )

    @server.tool(annotations=READ_ONLY)
    def gateway_get_job(job_id: str) -> dict[str, Any]:
        """Read a persisted job and its ordered event log."""

        return gateway.inspect_job(job_id)

    @server.tool(annotations=READ_ONLY)
    def gateway_list_workspace_files(job_id: str, path: str = ".") -> dict[str, Any]:
        """List one directory inside a job workspace; paths must be workspace-relative."""

        return gateway.list_workspace_files(job_id, path)

    @server.tool(annotations=READ_ONLY)
    def gateway_search_workspace(
        job_id: str,
        query: str,
        path: str = ".",
        max_results: int = 100,
    ) -> dict[str, Any]:
        """Search bounded text files inside a job workspace for a literal string."""

        return gateway.search_workspace(job_id, query, path=path, max_results=max_results)

    @server.tool(annotations=READ_ONLY)
    def gateway_read_workspace_file(job_id: str, path: str) -> dict[str, Any]:
        """Read a size-bounded UTF-8 text file inside a job workspace."""

        return gateway.read_workspace_file(job_id, path)

    @server.tool(annotations=SCOPED_WRITE)
    def gateway_write_workspace_file(
        job_id: str,
        path: str,
        content: str,
        create: bool = False,
    ) -> dict[str, Any]:
        """Create or replace one text file inside a writable isolated job workspace."""

        return gateway.write_workspace_file(job_id, path, content, create=create)

    @server.tool(annotations=SCOPED_WRITE)
    def gateway_move_workspace_file(job_id: str, source: str, destination: str) -> dict[str, Any]:
        """Move one workspace file between two validated workspace-relative paths."""

        return gateway.move_workspace_file(job_id, source, destination)

    @server.tool(annotations=SCOPED_WRITE)
    def gateway_request_delete(job_id: str, path: str) -> dict[str, Any]:
        """Record a deletion approval request; this MVP never executes the deletion."""

        return gateway.request_delete(job_id, path)

    @server.tool(annotations=READ_ONLY)
    def gateway_get_diff(job_id: str) -> dict[str, Any]:
        """Compute a deterministic unified patch from source snapshot to job workspace."""

        return gateway.get_diff(job_id)

    @server.tool(annotations=SCOPED_WRITE)
    def gateway_validate(job_id: str) -> dict[str, Any]:
        """Run only the project's mandatory manifest-allowlisted validation actions."""

        return gateway.validate(job_id)

    @server.tool(annotations=READ_ONLY)
    def gateway_get_evidence(job_id: str) -> dict[str, Any]:
        """Return evidence location and independently verify its SHA-256 manifest."""

        return gateway.get_evidence(job_id)

    @server.tool(annotations=SCOPED_WRITE)
    def gateway_publish_local_branch(job_id: str, explicit: bool = False) -> dict[str, Any]:
        """With explicit consent and project R3 permission, create a non-default local branch commit."""

        return gateway.publish_local_branch(job_id, explicit=explicit)

    return server


def serve(
    *,
    config: GatewayConfig | None = None,
    transport: str = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    """Run stdio or localhost-only Streamable HTTP transport."""

    if transport not in {"stdio", "streamable-http"}:
        raise ValueError("transport must be 'stdio' or 'streamable-http'")
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("HTTP transport is restricted to a localhost address")
    create_mcp_server(config, host=host, port=port).run(transport=transport)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Universal Project Gateway MCP server")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    config = GatewayConfig.from_root(args.root) if args.root else GatewayConfig.discover()
    serve(config=config, transport=args.transport, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
