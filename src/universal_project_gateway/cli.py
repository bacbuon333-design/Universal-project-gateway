"""Command-line interface for the Universal Project Gateway."""

from __future__ import annotations

import argparse
import json
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
    """Compatibility wrapper for the comprehensive local doctor."""

    from .operations import doctor as run_doctor

    return run_doctor(config)


def _print_status(result: dict[str, Any]) -> None:
    jobs = result["jobs"]
    registry = result["registry"]
    intelligence = result["intelligence"]
    print(f"Universal Project Gateway {result['version']}")
    print(f"Checkpoint: {result['checkpoint'] or 'unavailable'}")
    print(f"Projects: {registry['project_count']}")
    print(f"Jobs: {jobs['total']} ({json.dumps(jobs['by_state'], sort_keys=True)})")
    print(f"Adapters: {result['adapters']['count']}")
    print(
        "Intelligence: "
        f"{json.dumps(intelligence['counts'], sort_keys=True)} "
        f"[{intelligence['freshness_basis']}]"
    )
    print(
        "Sandbox: "
        f"{result['sandbox']['default_backend_id']} "
        f"({result['sandbox']['default_safety_level']})"
    )
    print(
        "Evidence: "
        f"{result['evidence']['contract_version']} schema "
        f"{result['evidence']['schema_version']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="upg", description="Universal Project Gateway")
    parser.add_argument("--root", type=Path, help="Gateway repository root (default: discover)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("doctor", help="Inspect local prerequisites without installing anything")
    status_command = commands.add_parser("status", help="Report local registry and runtime status")
    status_command.add_argument("--json", action="store_true", dest="json_output")
    cleanup_command = commands.add_parser(
        "cleanup", help="Plan conservative cleanup of terminal-job runtime data"
    )
    cleanup_mode = cleanup_command.add_mutually_exclusive_group()
    cleanup_mode.add_argument("--dry-run", action="store_true", help="Plan only (default)")
    cleanup_mode.add_argument("--execute", action="store_true", help="Delete approved candidates")
    cleanup_command.add_argument("--workspaces", action="store_true", help="Select job workspaces")
    cleanup_command.add_argument("--artifacts", action="store_true", help="Select job artifacts")
    cleanup_command.add_argument("--keep-last", type=int, default=10, metavar="N")

    project = commands.add_parser("project", help="Manage the persistent project registry")
    project_commands = project.add_subparsers(dest="project_command", required=True)
    register = project_commands.add_parser("register", help="Register a validated project manifest")
    register.add_argument("manifest", type=Path)
    project_commands.add_parser("list", help="List registered projects")
    show = project_commands.add_parser("show", help="Show a registered project")
    show.add_argument("project_id")

    adapter = commands.add_parser("adapter", help="Inspect installed adapter capabilities")
    adapter_commands = adapter.add_subparsers(dest="adapter_command", required=True)
    adapter_commands.add_parser("list", help="List versioned adapter capabilities")

    intelligence = commands.add_parser(
        "intelligence", help="Generate or inspect deterministic project metadata caches"
    )
    intelligence_commands = intelligence.add_subparsers(
        dest="intelligence_command", required=True
    )
    generate = intelligence_commands.add_parser(
        "generate", help="Refresh one registered project's bounded cache"
    )
    generate.add_argument("project_id")
    intelligence_commands.add_parser("list", help="List generated verified caches")
    show_intelligence = intelligence_commands.add_parser(
        "show", help="Read one generated cache without rescanning the project"
    )
    show_intelligence.add_argument("project_id")

    task = commands.add_parser("task", help="Prepare and operate scoped jobs")
    task_commands = task.add_subparsers(dest="task_command", required=True)
    prepare = task_commands.add_parser(
        "prepare", help="Compile intent and create an isolated workspace"
    )
    prepare.add_argument("--project", required=True, dest="project_id")
    prepare.add_argument("--request", required=True)
    prepare.add_argument("--target", action="append", default=[])
    prepare.add_argument("--operation")
    prepare.add_argument("--publication", default="none", choices=("none", "local_commit", "push"))
    prepare.add_argument("--idempotency-key")
    for name, help_text in (
        ("inspect", "Inspect a persisted job and its events"),
        ("diff", "Compute the workspace patch"),
        ("evidence", "Inspect and verify the evidence bundle"),
    ):
        command = task_commands.add_parser(name, help=help_text)
        command.add_argument("job_id")
    validate = task_commands.add_parser("validate", help="Run mandatory allowlisted validation")
    validate.add_argument("job_id")
    validate.add_argument("--idempotency-key")
    cancel = task_commands.add_parser("cancel", help="Persist a cooperative cancellation request")
    cancel.add_argument("job_id")
    cancel.add_argument("--reason")
    recover = task_commands.add_parser("recover", help="Recover one job whose lease has expired")
    recover.add_argument("job_id")

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

        if args.command == "status":
            from .operations import status

            result = status(config)
            if args.json_output:
                _json(result)
            else:
                _print_status(result)
            return 0

        if args.command == "cleanup":
            from .operations import cleanup

            select_all = not args.workspaces and not args.artifacts
            result = cleanup(
                config,
                dry_run=not args.execute,
                workspaces=args.workspaces or select_all,
                artifacts=args.artifacts or select_all,
                keep_last=args.keep_last,
            )
            _json(result)
            return 0

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
        if args.command == "adapter":
            _json(gateway.list_adapters())
            return 0
        if args.command == "intelligence":
            if args.intelligence_command == "generate":
                _json(gateway.generate_project_intelligence(args.project_id))
            elif args.intelligence_command == "list":
                _json(gateway.list_project_intelligence())
            else:
                _json(gateway.get_project_intelligence(args.project_id))
            return 0
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
                    idempotency_key=args.idempotency_key,
                )
            )
        elif args.task_command == "inspect":
            _json(gateway.inspect_job(args.job_id))
        elif args.task_command == "diff":
            _json(gateway.get_diff(args.job_id))
        elif args.task_command == "validate":
            result = gateway.validate(args.job_id, idempotency_key=args.idempotency_key)
            _json(result)
            return 0 if result.get("passed") else 1
        elif args.task_command == "cancel":
            _json(gateway.request_cancellation(args.job_id, reason=args.reason))
        elif args.task_command == "recover":
            _json(gateway.recover_expired_job(args.job_id))
        elif args.task_command == "evidence":
            result = gateway.get_evidence(args.job_id)
            _json(result)
            return 0 if result.get("verified") else 1
        return 0
    except (GatewayError, ValueError, FileNotFoundError) as exc:
        payload = (
            exc.to_dict()
            if isinstance(exc, GatewayError)
            else {
                "code": type(exc).__name__.upper(),
                "message": str(exc),
                "details": {},
            }
        )
        print(json.dumps(payload, indent=2, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
