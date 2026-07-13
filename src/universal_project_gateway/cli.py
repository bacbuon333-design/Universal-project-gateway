"""Command-line interface for the Universal Project Gateway."""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from . import __version__
from .config import GatewayConfig
from .models import GatewayError, json_ready


def _json(value: Any) -> None:
    print(json.dumps(json_ready(value), indent=2, sort_keys=True, ensure_ascii=False))


def doctor(config: GatewayConfig) -> dict[str, Any]:
    """Run side-effect-light local readiness checks."""

    checks: list[dict[str, str]] = []

    def add(name: str, status: str, message: str) -> None:
        checks.append({"name": name, "status": status, "message": message})

    version = sys.version_info
    add(
        "python",
        "PASS" if version >= (3, 11) else "FAIL",
        f"{version.major}.{version.minor}.{version.micro}",
    )
    try:
        sqlite3.connect(":memory:").execute("SELECT 1").fetchone()
        add("sqlite", "PASS", sqlite3.sqlite_version)
    except sqlite3.Error as exc:
        add("sqlite", "FAIL", str(exc))

    for name, directory in (
        ("var_directory", config.database_path.parent),
        ("workspace_directory", config.workspaces_root),
        ("artifacts_directory", config.artifacts_root),
    ):
        parent = next((p for p in (directory, *directory.parents) if p.exists()), None)
        writable = bool(parent and parent.is_dir())
        add(name, "PASS" if writable else "FAIL", str(directory))

    git = shutil.which("git")
    add("git", "PASS" if git else "WARN", git or "Git is unavailable; R3 is disabled")
    try:
        import mcp  # noqa: F401

        add("mcp_sdk", "PASS", "official Python MCP SDK import succeeded")
    except ImportError as exc:
        add("mcp_sdk", "FAIL", str(exc))

    fixtures = [config.root_dir / "fixtures" / name / "PROJECT_MANIFEST.yaml" for name in ("python_demo", "node_demo")]
    missing = [str(path) for path in fixtures if not path.is_file()]
    add(
        "fixtures",
        "PASS" if not missing else "FAIL",
        "Python and Node fixtures found" if not missing else f"Missing: {', '.join(missing)}",
    )
    overall = "FAIL" if any(item["status"] == "FAIL" for item in checks) else (
        "WARN" if any(item["status"] == "WARN" for item in checks) else "PASS"
    )
    return {"status": overall, "version": __version__, "root": str(config.root_dir), "checks": checks}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="upg", description="Universal Project Gateway")
    parser.add_argument("--root", type=Path, help="Gateway repository root (default: discover)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Inspect local prerequisites without installing anything")

    project = commands.add_parser("project", help="Manage the persistent project registry")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    register = project_commands.add_parser("register", help="Register a validated project manifest")
    register.add_argument("manifest", type=Path)
    project_commands.add_parser("list", help="List registered projects")
    show = project_commands.add_parser("show", help="Show a registered project")
    show.add_argument("project_id")

    task = commands.add_parser("task", help="Prepare and operate scoped jobs")
    task_commands = task.add_subparsers(dest="task_command", required=True)
    prepare = task_commands.add_parser("prepare", help="Compile intent and create an isolated workspace")
    prepare.add_argument("--project", required=True, dest="project_id")
    prepare.add_argument("--request", required=True)
    prepare.add_argument("--target", action="append", default=[])
    prepare.add_argument("--operation")
    prepare.add_argument("--publication", default="none", choices=("none", "local_commit", "push"))
    for name, help_text in (
        ("inspect", "Inspect a persisted job and its events"),
        ("diff", "Compute the workspace patch"),
        ("validate", "Run mandatory allowlisted validation"),
        ("evidence", "Inspect and verify the evidence bundle"),
    ):
        command = task_commands.add_parser(name, help=help_text)
        command.add_argument("job_id")

    commands.add_parser("demo", help="Run the deterministic Python fixture vertical slice")

    mcp = commands.add_parser("mcp", help="Run MCP integration")
    mcp_commands = mcp.add_subparsers(dest="mcp_command", required=True)
    serve = mcp_commands.add_parser("serve", help="Start the local MCP server")
    serve.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    config = GatewayConfig.from_root(args.root) if args.root else GatewayConfig.discover()
    try:
        if args.command == "doctor":
            result = doctor(config)
            _json(result)
            return 1 if result["status"] == "FAIL" else 0

        if args.command == "mcp":
            from .mcp_server import serve

            serve(config=config, transport=args.transport, host=args.host, port=args.port)
            return 0

        if args.command == "demo":
            from .demo import run_demo

            result = run_demo(config.root_dir)
            _json(result)
            return 0

        from .service import GatewayService

        gateway = GatewayService(config)
        if args.command == "project":
            if args.project_command == "register":
                _json(gateway.register_project(args.manifest))
            elif args.project_command == "list":
                _json(gateway.list_projects())
            else:
                _json(gateway.get_project(args.project_id))
            return 0

        if args.task_command == "prepare":
            _json(
                gateway.prepare_task(
                    args.project_id,
                    args.request,
                    target_paths=args.target,
                    requested_operation=args.operation,
                    publication_preference=args.publication,
                )
            )
        elif args.task_command == "inspect":
            _json(gateway.inspect_job(args.job_id))
        elif args.task_command == "diff":
            _json(gateway.get_diff(args.job_id))
        elif args.task_command == "validate":
            result = gateway.validate(args.job_id)
            _json(result)
            return 0 if result.get("passed") else 1
        elif args.task_command == "evidence":
            result = gateway.get_evidence(args.job_id)
            _json(result)
            return 0 if result.get("verified") else 1
        return 0
    except (GatewayError, ValueError, FileNotFoundError) as exc:
        payload = exc.to_dict() if isinstance(exc, GatewayError) else {
            "code": type(exc).__name__.upper(),
            "message": str(exc),
            "details": {},
        }
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
