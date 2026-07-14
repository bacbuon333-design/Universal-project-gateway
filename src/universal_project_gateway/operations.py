"""Read-mostly local operator diagnostics, status, and conservative cleanup."""

from __future__ import annotations

import importlib.metadata
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from . import __version__
from .config import GatewayConfig
from .contracts import EVIDENCE_CONTRACT_VERSION, PROJECT_INTELLIGENCE_CONTRACT_VERSION
from .evidence_chain import EVIDENCE_SCHEMA_VERSION
from .models import GatewayError
from .scoped_fs import is_reparse_point

EXPECTED_DATABASE_SCHEMA_VERSION = 2
TERMINAL_JOB_STATES = frozenset({"completed", "failed", "cancelled"})
_SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class OperationsError(GatewayError):
    """Structured refusal from a local operations command."""

    default_code = "OPERATIONS_ERROR"


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _paths_overlap(left: Path, right: Path) -> bool:
    return _path_within(left, right) or _path_within(right, left)


def _filtered_process_environment() -> dict[str, str]:
    allowed = {
        "COMSPEC",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    }
    environment = {name: value for name, value in os.environ.items() if name.upper() in allowed}
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _run_git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str] | None:
    git = shutil.which("git")
    if git is None:
        return None
    try:
        return subprocess.run(
            [git, *arguments],
            cwd=root,
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            env=_filtered_process_environment(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _safe_remote(value: str) -> str:
    remote = value.strip()
    if not remote:
        return ""
    if "://" in remote:
        parts = urlsplit(remote)
        hostname = parts.hostname or ""
        if parts.port:
            hostname = f"{hostname}:{parts.port}"
        return urlunsplit((parts.scheme, hostname, parts.path, "", ""))
    if "@" in remote and ":" in remote:
        return remote.split("@", 1)[1]
    return remote


def _effective_registry(config: GatewayConfig):
    from .registry import ProjectRegistry

    if config.registry_path.is_file():
        return ProjectRegistry(config.registry_path, path_base=config.root_dir), config.registry_path
    seed = config.root_dir / "registry" / "projects.yaml"
    return ProjectRegistry(seed, path_base=config.root_dir), seed


def _database_uri(path: Path) -> str:
    return f"{path.resolve().as_uri()}?mode=ro"


def _read_database(config: GatewayConfig) -> dict[str, Any]:
    path = config.database_path
    if not path.is_file():
        return {
            "available": False,
            "readable": False,
            "schema_version": None,
            "migration_status": "not_initialized",
            "jobs": [],
        }
    try:
        with sqlite3.connect(_database_uri(path), uri=True, timeout=2) as connection:
            connection.row_factory = sqlite3.Row
            quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            schema_version = int(connection.execute("PRAGMA user_version").fetchone()[0])
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
            required = {"jobs", "job_events", "job_operations"}
            if not required.issubset(tables):
                return {
                    "available": True,
                    "readable": False,
                    "schema_version": schema_version,
                    "migration_status": "incomplete",
                    "quick_check": quick_check,
                    "missing_tables": sorted(required - tables),
                    "jobs": [],
                }
            rows = connection.execute(
                "SELECT job_id, project_id, status, created_at, updated_at, error_code "
                "FROM jobs ORDER BY updated_at DESC, job_id DESC"
            ).fetchall()
    except (OSError, sqlite3.Error, ValueError) as exc:
        return {
            "available": True,
            "readable": False,
            "schema_version": None,
            "migration_status": "unreadable",
            "error": str(exc),
            "jobs": [],
        }
    migration_status = (
        "current"
        if schema_version == EXPECTED_DATABASE_SCHEMA_VERSION
        else ("upgrade_required" if schema_version < EXPECTED_DATABASE_SCHEMA_VERSION else "newer")
    )
    return {
        "available": True,
        "readable": quick_check == "ok",
        "schema_version": schema_version,
        "migration_status": migration_status,
        "quick_check": quick_check,
        "jobs": [dict(row) for row in rows],
    }


def _git_status(root: Path) -> dict[str, Any]:
    availability = _run_git(root, "--version")
    if availability is None or availability.returncode != 0:
        return {"available": False, "branch": None, "dirty": None, "origin": None, "tag": None}
    branch_result = _run_git(root, "branch", "--show-current")
    status_result = _run_git(root, "status", "--porcelain", "--untracked-files=normal")
    origin_result = _run_git(root, "remote", "get-url", "origin")
    exact_tag_result = _run_git(root, "describe", "--tags", "--exact-match", "HEAD")
    nearest_tag_result = _run_git(root, "describe", "--tags", "--abbrev=0")
    dirty_count = None
    if status_result is not None and status_result.returncode == 0:
        dirty_count = len([line for line in status_result.stdout.splitlines() if line.strip()])
    exact_tag = (
        exact_tag_result.stdout.strip()
        if exact_tag_result is not None and exact_tag_result.returncode == 0
        else None
    )
    nearest_tag = (
        nearest_tag_result.stdout.strip()
        if nearest_tag_result is not None and nearest_tag_result.returncode == 0
        else None
    )
    commits_since_nearest_tag = None
    if nearest_tag:
        distance_result = _run_git(root, "rev-list", "--count", f"{nearest_tag}..HEAD")
        if distance_result is not None and distance_result.returncode == 0:
            try:
                commits_since_nearest_tag = int(distance_result.stdout.strip())
            except ValueError:
                commits_since_nearest_tag = None
    checkpoint_status = (
        "exact" if exact_tag else "ahead" if nearest_tag is not None else "unavailable"
    )
    return {
        "available": True,
        "version": availability.stdout.strip(),
        "branch": branch_result.stdout.strip() if branch_result and branch_result.returncode == 0 else None,
        "dirty": dirty_count is not None and dirty_count > 0,
        "dirty_entry_count": dirty_count,
        "origin": _safe_remote(origin_result.stdout) if origin_result and origin_result.returncode == 0 else None,
        "tag": exact_tag,
        "nearest_tag": nearest_tag,
        "checkpoint_status": checkpoint_status,
        "commits_since_nearest_tag": commits_since_nearest_tag,
    }


def _intelligence_summary(config: GatewayConfig, project_ids: list[str]) -> dict[str, Any]:
    from .intelligence import ProjectIntelligenceCache, ProjectIntelligenceError

    cache = ProjectIntelligenceCache(config)
    now = datetime.now(UTC)
    projects: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    for project_id in project_ids:
        try:
            result = cache.get(project_id)
            document = result["intelligence"]
            generated = _parse_time(document.get("generated_at"))
            age_hours = (now - generated).total_seconds() / 3600 if generated else None
            freshness = "recent" if age_hours is not None and age_hours <= 24 else "refresh_recommended"
            item = {
                "project_id": project_id,
                "status": freshness,
                "generated_at": document.get("generated_at"),
                "age_hours": round(age_hours, 2) if age_hours is not None else None,
                "schema_version": document.get("schema_version"),
                "cache_hash": document.get("cache_hash"),
            }
        except ProjectIntelligenceError as exc:
            status = "missing" if exc.code == "PROJECT_INTELLIGENCE_NOT_FOUND" else "invalid"
            item = {"project_id": project_id, "status": status, "code": exc.code}
        counts[item["status"]] += 1
        projects.append(item)
    return {
        "contract_version": PROJECT_INTELLIGENCE_CONTRACT_VERSION,
        "freshness_basis": "cache_age_only_no_source_rescan",
        "recent_threshold_hours": 24,
        "counts": dict(sorted(counts.items())),
        "projects": projects,
    }


def _latest_evidence(config: GatewayConfig) -> dict[str, Any]:
    from .evidence import EvidenceLedger

    root = config.artifacts_root
    if not root.is_dir() or is_reparse_point(root):
        return {"available": False, "verified": None, "path": None}
    candidates = [
        path
        for path in root.iterdir()
        if path.is_dir()
        and not is_reparse_point(path)
        and (path / "manifest.sha256.json").is_file()
    ]
    if not candidates:
        return {"available": False, "verified": None, "path": None}
    latest = max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))
    verification = EvidenceLedger(root).verify(latest)
    return {"available": True, "verified": verification.valid, **verification.to_dict()}


def doctor(config: GatewayConfig) -> dict[str, Any]:
    """Perform comprehensive checks without installing, migrating, or starting services."""

    checks: list[dict[str, Any]] = []

    def add(name: str, status: str, message: str, **details: Any) -> None:
        checks.append({"name": name, "status": status, "message": message, "details": details})

    version = sys.version_info
    add("python_version", "PASS" if version >= (3, 11) else "FAIL", sys.version.split()[0])
    venv_python = config.root_dir / ".venv" / "Scripts" / "python.exe"
    add(
        "virtual_environment",
        "PASS" if venv_python.is_file() else "WARN",
        "repository virtual environment is present" if venv_python.is_file() else "run the verified setup flow before full operation",
        path=str(venv_python),
        active=Path(sys.prefix).resolve(strict=False) == (config.root_dir / ".venv").resolve(strict=False),
    )
    try:
        installed_version = importlib.metadata.version("universal-project-gateway")
        add("package_import", "PASS", "installed package metadata and import are available", version=installed_version)
    except importlib.metadata.PackageNotFoundError:
        add("package_import", "WARN", "source import works but editable package metadata is unavailable", version=__version__)

    git = _git_status(config.root_dir)
    add("git_availability", "PASS" if git["available"] else "FAIL", git.get("version") or "Git is unavailable")
    if git["available"]:
        add("git_worktree", "WARN" if git["dirty"] else "PASS", "working tree has changes" if git["dirty"] else "working tree is clean", branch=git["branch"], dirty_entry_count=git["dirty_entry_count"])
        add("git_origin", "PASS" if git["origin"] else "WARN", git["origin"] or "origin is not configured")
        if git["tag"]:
            checkpoint_status = "PASS"
            checkpoint_message = f"HEAD exactly matches checkpoint {git['tag']}"
        elif git["nearest_tag"]:
            checkpoint_status = "WARN"
            distance = git["commits_since_nearest_tag"]
            distance_text = f"{distance} commit(s)" if distance is not None else "one or more commits"
            checkpoint_message = (
                f"HEAD is {distance_text} beyond nearest checkpoint {git['nearest_tag']}"
            )
        else:
            checkpoint_status = "WARN"
            checkpoint_message = "no reachable checkpoint tag"
        add(
            "git_checkpoint",
            checkpoint_status,
            checkpoint_message,
            exact=bool(git["tag"]),
            nearest_tag=git["nearest_tag"],
            commits_since_nearest_tag=git["commits_since_nearest_tag"],
        )

    required = [
        config.root_dir / "PROJECT_MANIFEST.yaml",
        config.root_dir / "registry" / "projects.yaml",
        config.root_dir / "src" / "universal_project_gateway",
        config.root_dir / "scripts",
        config.root_dir / "tests",
        config.root_dir / "state",
    ]
    missing = [str(path) for path in required if not path.exists()]
    add("required_paths", "PASS" if not missing else "FAIL", "required repository paths are present" if not missing else "required repository paths are missing", missing=missing)
    runtime_dirs = [config.database_path.parent, config.workspaces_root, config.artifacts_root, config.intelligence_cache_root]
    missing_runtime = [str(path) for path in runtime_dirs if not path.is_dir()]
    add("runtime_directories", "PASS" if not missing_runtime else "WARN", "runtime directories are present" if not missing_runtime else "runtime directories will be created only by an authorized command", missing=missing_runtime)

    try:
        from .manifests import validate_manifest

        result = validate_manifest(config.root_dir / "PROJECT_MANIFEST.yaml")
        add("root_manifest", "PASS" if result.valid else "FAIL", "root manifest is valid" if result.valid else "root manifest validation failed", result=result.to_dict())
    except Exception as exc:  # trust-boundary diagnostic must report, not crash
        add("root_manifest", "FAIL", "root manifest could not be checked", error=type(exc).__name__)

    project_ids: list[str] = []
    try:
        registry, registry_path = _effective_registry(config)
        records = registry.list()
        for record in records:
            registry.get_manifest(record.project_id)
        project_ids = [record.project_id for record in records]
        add("registry", "PASS" if records else "WARN", f"validated {len(records)} registered project(s)", path=str(registry_path), project_ids=project_ids)
    except GatewayError as exc:
        add("registry", "FAIL", exc.message, code=exc.code)

    database = _read_database(config)
    if not database["available"]:
        database_status = "WARN"
        database_message = "SQLite job database has not been initialized"
    elif not database["readable"] or database["migration_status"] in {"incomplete", "unreadable", "newer"}:
        database_status = "FAIL"
        database_message = "SQLite job database failed a read-only health check"
    elif database["migration_status"] != "current":
        database_status = "WARN"
        database_message = "SQLite job database requires migration by the normal startup flow"
    else:
        database_status = "PASS"
        database_message = "SQLite job database is readable and current"
    add("sqlite_jobs", database_status, database_message, **{key: value for key, value in database.items() if key != "jobs"})

    try:
        from .runtime.registry import built_in_adapter_registry

        adapters = [item.to_dict() for item in built_in_adapter_registry().list_capabilities()]
        add("adapter_registry", "PASS" if adapters else "FAIL", f"{len(adapters)} built-in adapter(s) available", adapter_ids=[item["adapter_id"] for item in adapters])
    except GatewayError as exc:
        add("adapter_registry", "FAIL", exc.message, code=exc.code)

    try:
        from .sandbox import LocalProcessSandboxBackend, UnsafeLocalSandboxBackend

        backends = [UnsafeLocalSandboxBackend(), LocalProcessSandboxBackend()]
        add("sandbox_backends", "PASS", "development sandbox backends are importable", backends=[{"backend_id": item.backend_id, "safety_level": item.safety_level} for item in backends], default=UnsafeLocalSandboxBackend.backend_id)
    except Exception as exc:
        add("sandbox_backends", "FAIL", "sandbox backends could not be loaded", error=type(exc).__name__)

    try:
        intelligence = _intelligence_summary(config, project_ids)
        invalid = intelligence["counts"].get("invalid", 0)
        missing_count = intelligence["counts"].get("missing", 0)
        intelligence_status = "FAIL" if invalid else ("WARN" if missing_count else "PASS")
        add("project_intelligence", intelligence_status, "cache files were hash-verified without rescanning source", summary=intelligence)
    except GatewayError as exc:
        add("project_intelligence", "FAIL", exc.message, code=exc.code)

    try:
        evidence = _latest_evidence(config)
        evidence_status = "WARN" if not evidence["available"] else ("PASS" if evidence["verified"] else "FAIL")
        add("latest_evidence", evidence_status, "no evidence bundle is available" if not evidence["available"] else "latest evidence bundle verified" if evidence["verified"] else "latest evidence bundle failed verification", evidence=evidence)
    except (GatewayError, OSError) as exc:
        add("latest_evidence", "FAIL", "latest evidence could not be verified", error=type(exc).__name__)

    try:
        from .mcp_server import create_mcp_server

        add("mcp_smoke", "PASS", "MCP SDK and server factory import succeeded; no transport was started", factory_callable=callable(create_mcp_server))
    except ImportError as exc:
        add("mcp_smoke", "FAIL", "MCP server import failed", error=str(exc))

    overall = "FAIL" if any(item["status"] == "FAIL" for item in checks) else "WARN" if any(item["status"] == "WARN" for item in checks) else "PASS"
    return {"status": overall, "version": __version__, "root": str(config.root_dir), "generated_at": _utc_now(), "checks": checks}


def status(config: GatewayConfig) -> dict[str, Any]:
    """Build a read-only local status snapshot."""

    registry, registry_path = _effective_registry(config)
    records = registry.list()
    project_ids = [record.project_id for record in records]
    database = _read_database(config)
    jobs = database.pop("jobs")
    counts = Counter(str(job["status"]) for job in jobs)

    def latest(state: str) -> dict[str, Any] | None:
        return next((dict(job) for job in jobs if job["status"] == state), None)

    from .runtime.registry import built_in_adapter_registry
    from .sandbox import UnsafeLocalSandboxBackend

    adapters = [item.to_dict() for item in built_in_adapter_registry().list_capabilities()]
    git = _git_status(config.root_dir)
    evidence = _latest_evidence(config)
    return {
        "system_id": "universal-project-gateway",
        "version": __version__,
        "generated_at": _utc_now(),
        "root": str(config.root_dir),
        "checkpoint": git.get("tag") or git.get("nearest_tag"),
        "git": git,
        "registry": {
            "path": str(registry_path),
            "project_count": len(records),
            "projects": [{"project_id": item.project_id, "name": item.name, "project_type": item.project_type} for item in records],
        },
        "jobs": {
            "database": database,
            "total": len(jobs),
            "by_state": dict(sorted(counts.items())),
            "latest_completed": latest("completed"),
            "latest_failed": latest("failed"),
        },
        "adapters": {"count": len(adapters), "items": adapters},
        "intelligence": _intelligence_summary(config, project_ids),
        "sandbox": {"default_backend_id": UnsafeLocalSandboxBackend.backend_id, "default_safety_level": UnsafeLocalSandboxBackend.safety_level},
        "evidence": {"contract_version": EVIDENCE_CONTRACT_VERSION, "schema_version": EVIDENCE_SCHEMA_VERSION, "latest": evidence},
    }


def _cleanup_roots(config: GatewayConfig, *, workspaces: bool, artifacts: bool) -> list[tuple[str, Path]]:
    selected = []
    if workspaces:
        selected.append(("workspace", config.workspaces_root))
    if artifacts:
        selected.append(("artifact", config.artifacts_root))
    return selected


def _cleanup_root_overlaps_source(
    config: GatewayConfig,
    kind: str,
    root: Path,
    source_roots: list[Path],
) -> bool:
    resolved = root.resolve(strict=False)
    approved_repository_root = (
        config.root_dir / ("workspaces/jobs" if kind == "workspace" else "artifacts/jobs")
    ).resolve(strict=False)
    for source in source_roots:
        if _path_within(source, resolved):
            return True
        if _path_within(resolved, source) and not (
            source == config.root_dir.resolve(strict=False)
            and resolved == approved_repository_root
        ):
            return True
    return False


def cleanup(
    config: GatewayConfig,
    *,
    dry_run: bool = True,
    workspaces: bool = True,
    artifacts: bool = True,
    keep_last: int = 10,
) -> dict[str, Any]:
    """Plan or execute cleanup of old terminal-job runtime directories only."""

    if isinstance(keep_last, bool) or not isinstance(keep_last, int) or not 0 <= keep_last <= 10_000:
        raise OperationsError("keep_last must be an integer from 0 to 10000", code="INVALID_KEEP_LAST")
    if not workspaces and not artifacts:
        raise OperationsError("select at least one cleanup target", code="CLEANUP_TARGET_REQUIRED")

    registry, _ = _effective_registry(config)
    source_roots = [record.local_path.resolve() for record in registry.list()]
    protected = [
        config.root_dir / ".git",
        config.root_dir / "registry",
        config.root_dir / "state",
        config.root_dir / "PROJECT_MANIFEST.yaml",
        config.registry_path,
        config.database_path,
    ]
    roots = _cleanup_roots(config, workspaces=workspaces, artifacts=artifacts)
    for kind, root in roots:
        resolved_root = root.resolve(strict=False)
        if (
            is_reparse_point(root)
            or _cleanup_root_overlaps_source(config, kind, root, source_roots)
            or any(_paths_overlap(resolved_root, item) for item in protected)
        ):
            raise OperationsError("cleanup root overlaps a registered source or protected path", code="CLEANUP_ROOT_PROTECTED", details={"root": str(root)})

    database = _read_database(config)
    if database["available"] and not database["readable"]:
        raise OperationsError("job database must be readable before cleanup", code="CLEANUP_DATABASE_UNREADABLE")
    jobs = database["jobs"]
    terminal = [job for job in jobs if job["status"] in TERMINAL_JOB_STATES]
    kept_ids = {str(job["job_id"]) for job in terminal[:keep_last]}
    eligible_ids = {str(job["job_id"]) for job in terminal[keep_last:]}
    active_ids = {str(job["job_id"]) for job in jobs if job["status"] not in TERMINAL_JOB_STATES}
    candidates: list[dict[str, str]] = []
    skipped: list[dict[str, str]] = []

    for kind, root in roots:
        if not root.is_dir():
            skipped.append({"kind": kind, "path": str(root), "reason": "root_not_present"})
            continue
        for child in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
            reason = None
            if not child.is_dir() or is_reparse_point(child):
                reason = "not_a_plain_directory"
            elif not _SAFE_JOB_ID.fullmatch(child.name) or ".." in child.name:
                reason = "unsafe_job_id"
            elif child.resolve(strict=False).parent != root.resolve(strict=False):
                reason = "path_escape"
            elif child.name in kept_ids:
                reason = "retained_recent_job"
            elif child.name in active_ids:
                reason = "active_job"
            elif child.name not in eligible_ids:
                reason = "unknown_or_nonterminal_job"
            elif any(_path_within(item, child) for item in source_roots) or any(
                _paths_overlap(child, item) for item in protected
            ):
                raise OperationsError("cleanup candidate overlaps a registered source or protected path", code="CLEANUP_PATH_PROTECTED", details={"path": str(child)})
            if reason:
                skipped.append({"kind": kind, "path": str(child), "reason": reason})
            else:
                candidates.append({"kind": kind, "job_id": child.name, "path": str(child.resolve())})

    deleted: list[dict[str, str]] = []
    if not dry_run:
        root_by_kind = {kind: root.resolve(strict=False) for kind, root in roots}
        for candidate in candidates:
            path = Path(candidate["path"])
            expected_root = root_by_kind[candidate["kind"]]
            if (
                not path.is_dir()
                or is_reparse_point(path)
                or path.resolve(strict=False).parent != expected_root
                or any(_path_within(item, path) for item in source_roots)
                or any(_paths_overlap(path, item) for item in protected)
            ):
                raise OperationsError("cleanup candidate changed after planning", code="CLEANUP_CANDIDATE_CHANGED", details={"path": str(path)})
        for candidate in candidates:
            shutil.rmtree(Path(candidate["path"]))
            deleted.append(candidate)
    return {
        "dry_run": dry_run,
        "keep_last": keep_last,
        "targets": [kind for kind, _ in roots],
        "candidate_count": len(candidates),
        "candidates": candidates,
        "deleted_count": len(deleted),
        "deleted": deleted,
        "skipped": skipped,
        "safety": "Only immediate terminal-job directories under configured runtime roots are eligible; registered sources and durable Gateway paths are refused.",
    }


__all__ = ["OperationsError", "cleanup", "doctor", "status"]
