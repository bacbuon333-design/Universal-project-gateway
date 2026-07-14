"""Run the controlled external-project UPG integration from creation to publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.operations import cleanup, doctor, status
from universal_project_gateway.service import GatewayService

if __package__:
    from .create_real_project_fixture import (
        INITIAL_GREETING,
        PROJECT_ID,
        UPDATED_GREETING,
        FixtureCreationError,
        create_real_project_fixture,
    )
    from .verify_gateway import verify_bundle
else:
    from create_real_project_fixture import (  # type: ignore[import-not-found]
        INITIAL_GREETING,
        PROJECT_ID,
        UPDATED_GREETING,
        FixtureCreationError,
        create_real_project_fixture,
    )
    from verify_gateway import verify_bundle  # type: ignore[import-not-found]

TARGET_PATHS = ("src/hello_web_app.py", "tests/test_app.py")


class IntegrationValidationError(RuntimeError):
    """A required real-project safety or behavior invariant failed."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise IntegrationValidationError(message)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _git_environment() -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in (
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "HOME",
            "USERPROFILE",
            "TEMP",
            "TMP",
        )
        if name in os.environ
    }
    environment.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"})
    return environment


def _git(project_root: Path, *arguments: str) -> str:
    git = shutil.which("git")
    if git is None:
        raise IntegrationValidationError("Git is required for publication verification")
    result = subprocess.run(
        [git, "-c", f"core.hooksPath={os.devnull}", *arguments],
        cwd=project_root,
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_git_environment(),
    )
    if result.returncode != 0:
        raise IntegrationValidationError(
            f"Git verification operation {arguments[0]!r} failed with "
            f"code {result.returncode}: {result.stderr.strip()[:500]}"
        )
    return result.stdout.strip()


def _tracked_hashes(project_root: Path) -> dict[str, str]:
    tracked = [line for line in _git(project_root, "ls-files").splitlines() if line]
    return {
        relative: hashlib.sha256(
            project_root.joinpath(*relative.split("/")).read_bytes()
        ).hexdigest()
        for relative in sorted(tracked)
    }


def _integration_config(
    gateway_root: Path,
    runtime_root: Path,
) -> GatewayConfig:
    base = GatewayConfig.from_root(gateway_root)
    runtime = runtime_root.resolve(strict=False)
    if _is_within(runtime, gateway_root):
        workspaces_root = base.workspaces_root
        artifacts_root = base.artifacts_root
    else:
        workspaces_root = runtime / "workspaces" / "jobs"
        artifacts_root = runtime / "artifacts" / "jobs"
    return replace(
        base,
        registry_path=runtime / "registry" / "projects.yaml",
        database_path=runtime / "gateway.db",
        workspaces_root=workspaces_root,
        artifacts_root=artifacts_root,
        intelligence_root=runtime / "project_intelligence",
    )


def run_real_project_integration(
    gateway_root: str | os.PathLike[str],
    project_root: str | os.PathLike[str],
    *,
    runtime_root: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Exercise the public Gateway API against one external Git repository."""

    gateway_path = Path(gateway_root).expanduser().resolve(strict=True)
    project_path = Path(project_root).expanduser().resolve(strict=False)
    run_id = uuid.uuid4().hex
    runtime_path = (
        Path(runtime_root).expanduser().resolve(strict=False)
        if runtime_root is not None
        else gateway_path / "var" / "real-project-integration" / run_id
    )
    _require(not _is_within(project_path, gateway_path), "external project is inside UPG")
    _require(not _is_within(gateway_path, project_path), "external project contains UPG")
    fixture = create_real_project_fixture(project_path, gateway_root=gateway_path)

    _require(_git(project_path, "branch", "--show-current") == "main", "fixture is not on main")
    _require(_git(project_path, "status", "--porcelain") == "", "fixture is dirty")
    _require(_git(project_path, "remote") == "", "fixture unexpectedly has a remote")
    initial_main = _git(project_path, "rev-parse", "main")
    initial_hashes = _tracked_hashes(project_path)

    config = _integration_config(gateway_path, runtime_path)
    gateway = GatewayService(config)
    registered = gateway.register_project(project_path / "PROJECT_MANIFEST.yaml")
    _require(registered["project_id"] == PROJECT_ID, "external registration identity changed")
    registered_ids = [item["project_id"] for item in gateway.list_projects()]
    _require(PROJECT_ID in registered_ids, "external project is missing from registry")

    intelligence = gateway.generate_project_intelligence(PROJECT_ID)
    intelligence_path = Path(intelligence["cache_path"]).resolve(strict=True)
    intelligence_document = intelligence["intelligence"]
    _require(
        _is_within(intelligence_path, config.intelligence_cache_root),
        "intelligence cache escaped Gateway-controlled state",
    )
    _require(
        not _is_within(intelligence_path, project_path),
        "intelligence cache was written into external source",
    )

    prepared = gateway.prepare_task(
        PROJECT_ID,
        "Change the greeting, update its test, validate, and create a local review branch",
        target_paths=TARGET_PATHS,
        requested_operation="edit",
        publication_preference="local_commit",
        idempotency_key=f"real-prepare-{run_id}",
    )
    job_id = prepared["job"]["job_id"]
    workspace_path = Path(prepared["workspace"]).resolve(strict=True)
    evidence_path = Path(prepared["evidence"]).resolve(strict=True)
    _require(_is_within(workspace_path, config.workspaces_root), "workspace escaped its root")
    _require(not _is_within(workspace_path, project_path), "workspace is inside source")
    _require(not _is_within(project_path, workspace_path), "workspace contains source")

    context_pack = json.loads(
        (evidence_path / "context_pack.json").read_text(encoding="utf-8")
    )
    compact_intelligence = context_pack.get("project_intelligence", {})
    _require(
        compact_intelligence.get("cache_hash") == intelligence_document["cache_hash"],
        "context pack does not reference generated intelligence",
    )
    _require("test_commands" not in compact_intelligence, "context intelligence is not compact")

    inspection = gateway.read_workspace_file(job_id, TARGET_PATHS[0])
    _require(
        INITIAL_GREETING in inspection["content"],
        "scoped workspace inspection did not read the expected source",
    )

    source_operation = gateway.replace_workspace_text(
        job_id,
        TARGET_PATHS[0],
        INITIAL_GREETING,
        UPDATED_GREETING,
        max_replacements=1,
    )
    test_operation = gateway.replace_workspace_text(
        job_id,
        TARGET_PATHS[1],
        INITIAL_GREETING,
        UPDATED_GREETING,
        max_replacements=1,
    )
    _require(source_operation["replacements"] == 1, "source greeting was not changed once")
    _require(test_operation["replacements"] == 1, "test greeting was not changed once")

    patch = gateway.get_diff(job_id)
    changed_paths = sorted(item["path"] for item in patch["files_changed"])
    _require(changed_paths == sorted(TARGET_PATHS), "patch contains unintended paths")
    _require(UPDATED_GREETING in patch["patch"], "patch does not contain the intended greeting")
    _require(_tracked_hashes(project_path) == initial_hashes, "source changed before publication")
    _require(_git(project_path, "status", "--porcelain") == "", "source became dirty before publication")
    _require(_git(project_path, "branch", "--show-current") == "main", "main changed before publication")

    validation = gateway.validate(job_id, idempotency_key=f"real-validate-{run_id}")
    _require(validation["passed"] is True, "external project validation failed")
    checks = validation["checks"]
    _require([item["action"] for item in checks] == ["lint", "test"], "unexpected validation actions")
    _require(all(item["status"] == "passed" for item in checks), "a validation action did not pass")
    _require(all(item["sandbox"]["shell_disabled"] for item in checks), "validation enabled a shell")
    _require(_tracked_hashes(project_path) == initial_hashes, "validation mutated source")

    evidence_before_publish = gateway.get_evidence(job_id)
    _require(evidence_before_publish["verified"] is True, "evidence did not verify")
    independent_before = verify_bundle(evidence_path)
    _require(independent_before["ok"] is True, "independent evidence verification failed")
    attestation = json.loads((evidence_path / "attestation.json").read_text(encoding="utf-8"))
    events = [
        json.loads(line)
        for line in (evidence_path / "evidence_events.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    _require(events[-1]["event_type"] == "evidence_finalized", "evidence final event is invalid")
    _require(
        attestation["final_event_hash"] == events[-1]["event_hash"],
        "attestation does not bind the final event",
    )

    publication_key = f"real-publish-{run_id}"
    published = gateway.publish_local_branch(
        job_id,
        explicit=True,
        idempotency_key=publication_key,
    )
    replay = gateway.publish_local_branch(
        job_id,
        explicit=True,
        idempotency_key=publication_key,
    )
    _require(replay == published, "publication idempotency did not replay the original result")
    _require(published["success"] is True, "local branch publication failed")
    _require(published["pushed"] is False, "external project was pushed")
    _require(sorted(published["committed_paths"]) == sorted(TARGET_PATHS), "publication committed unintended paths")
    _require(published["branch"].startswith(f"agent/{job_id}-"), "publication branch is not job-scoped")
    _require(_git(project_path, "branch", "--show-current") == published["branch"], "source is not on the review branch")
    _require(_git(project_path, "rev-parse", "main") == initial_main, "main ref changed")
    _require(_git(project_path, "status", "--porcelain") == "", "published source is dirty")
    _require(_git(project_path, "rev-list", "--count", "main..HEAD") == "1", "publication created duplicate commits")
    published_paths = sorted(_git(project_path, "diff", "--name-only", "main..HEAD").splitlines())
    _require(published_paths == sorted(TARGET_PATHS), "published branch differs outside intended paths")
    _require(INITIAL_GREETING in _git(project_path, "show", f"main:{TARGET_PATHS[0]}"), "main source was mutated")
    _require(UPDATED_GREETING in _git(project_path, "show", f"HEAD:{TARGET_PATHS[0]}"), "published source lacks change")
    _require(_git(project_path, "remote") == "", "publication configured a remote")

    evidence_after_publish = gateway.get_evidence(job_id)
    independent_after = verify_bundle(evidence_path)
    _require(evidence_after_publish["verified"] is True, "post-publication evidence failed")
    _require(independent_after["ok"] is True, "post-publication independent verification failed")

    cleanup_plan = cleanup(config, dry_run=True, keep_last=0)
    candidate_paths = [Path(item["path"]).resolve() for item in cleanup_plan["candidates"]]
    _require(cleanup_plan["deleted_count"] == 0, "cleanup dry-run deleted runtime data")
    _require(
        all(not _is_within(project_path, candidate) and not _is_within(candidate, project_path) for candidate in candidate_paths),
        "cleanup included the external project",
    )
    _require(project_path.is_dir(), "cleanup removed the external project")

    doctor_report = doctor(config)
    status_report = status(config)
    status_project_ids = [
        item["project_id"] for item in status_report["registry"]["projects"]
    ]
    _require(doctor_report["status"] != "FAIL", "doctor failed for the external runtime")
    _require(PROJECT_ID in status_project_ids, "status does not include the external project")
    _require(
        status_report["jobs"]["latest_completed"]["job_id"] == job_id,
        "status does not report the completed external job",
    )

    return {
        "success": True,
        "run_id": run_id,
        "external_project": fixture,
        "gateway_runtime": {
            "registry_path": str(config.registry_path),
            "database_path": str(config.database_path),
            "intelligence_root": str(config.intelligence_cache_root),
        },
        "registry": {"project_ids": registered_ids, "external_record": registered},
        "intelligence": {
            "cache_path": str(intelligence_path),
            "schema_version": intelligence_document["schema_version"],
            "cache_hash": intelligence_document["cache_hash"],
            "inside_project": False,
            "context_compact": True,
        },
        "job": {
            "job_id": job_id,
            "workspace_path": str(workspace_path),
            "scoped_inspection_succeeded": True,
            "source_unchanged_before_publish": True,
        },
        "patch": {"changed_paths": changed_paths, "contains_only_intended_changes": True},
        "validation": {
            "passed": True,
            "actions": [item["action"] for item in checks],
            "sandbox_backend_ids": [item["sandbox"]["backend_id"] for item in checks],
        },
        "evidence": {
            "path": str(evidence_path),
            "verified": True,
            "files_checked": independent_after["files_checked"],
            "events_checked": independent_after["events_checked"],
            "chain_checked": independent_after["chain_checked"],
            "attestation_final_hash_matches": True,
        },
        "publication": {
            **published,
            "idempotent_replay": True,
            "main_commit_unchanged": True,
            "commit_count": 1,
            "remote_count": 0,
        },
        "cleanup": {
            "dry_run": cleanup_plan["dry_run"],
            "candidate_count": cleanup_plan["candidate_count"],
            "deleted_count": cleanup_plan["deleted_count"],
            "external_project_preserved": True,
        },
        "operations": {
            "doctor_status": doctor_report["status"],
            "status_project_ids": status_project_ids,
            "status_job_counts": status_report["jobs"]["by_state"],
        },
        "limitations": [
            "Validation used the default unsafe-local subprocess backend, not an OS sandbox.",
            "The evidence attestation is unsigned local-development metadata.",
            "Publication created one local review branch and did not push or merge it.",
            "The external fixture is controlled trusted test code, not a production rollout.",
        ],
    }


def _default_project_root() -> Path:
    if os.name == "nt":
        return Path("Z:/UPG Test Projects/hello-web-app")
    return Path("/tmp/UPG Test Projects/hello-web-app")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gateway-root", type=Path, default=repository_root)
    parser.add_argument("--project-root", type=Path, default=_default_project_root())
    parser.add_argument("--runtime-root", type=Path)
    args = parser.parse_args()
    try:
        result = run_real_project_integration(
            args.gateway_root,
            args.project_root,
            runtime_root=args.runtime_root,
        )
    except (FixtureCreationError, IntegrationValidationError) as exc:
        print(
            json.dumps(
                {"success": False, "error": type(exc).__name__, "message": str(exc)},
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
