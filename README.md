# Universal Project Gateway

Universal Project Gateway (UPG) is a small, locally runnable architectural
proof for safely applying an AI-assisted change to one of several registered
software projects. It registers a manifest, prepares a durable job, copies the
project into an isolated workspace, permits scoped text operations, executes
only manifest-declared validation actions, and writes a checksummed evidence
bundle.

The same Gateway manages the dependency-free Python and Node.js fixtures in
this repository. The repository also has a root `PROJECT_MANIFEST.yaml` and a
portable seed registration, so UPG can prepare and validate changes to itself
inside the same per-job workspace boundary. No Animation, Trading, Revit,
Auto Call, video, or other project-specific business logic belongs in the
Gateway core.

> This MVP is not a production security boundary. It is a locally testable
> architectural proof. It has no public endpoint, remote authentication,
> deployment path, or tested ChatGPT Web connection.

## Quick start on Windows

Python 3.11 or newer is required. Git and Node.js are optional for the core;
Git enables publication tests and Node.js enables the second fixture test.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e ".[dev]"
.\.venv\Scripts\python.exe scripts\verify_manifest.py PROJECT_MANIFEST.yaml
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\run_demo.py
```

Or run the complete Windows verification entry point:

```bat
VERIFY_GATEWAY.bat
```

For day-to-day local operations, use the conservative Windows entry points:

```bat
DOCTOR_GATEWAY.bat
PULL_AND_VERIFY.bat
```

`DOCTOR_GATEWAY.bat` performs read-only readiness checks and never installs or
migrates anything. `PULL_AND_VERIFY.bat` works only on a clean `main`, pulls
`origin/main` with `--ff-only`, and stops if either pull or full verification
fails.

The deterministic demo registers both fixture manifests, then creates a fresh
Python-fixture job workspace, changes its greeting from `Hello` to
`Hello from UPG`, runs its tests, creates a patch and evidence ledger, and
verifies the ledger. The source fixture is not modified. Each run uses a new
job ID and preserves prior evidence.

## Controlled external-project proof

UPG also has an integration harness for a real, separate local Git repository.
Choose a new empty destination outside this repository, its workspaces, and its
artifacts:

```powershell
.\.venv\Scripts\python.exe scripts\validate_real_project_integration.py `
  --project-root "Z:\UPG Test Projects\hello-web-app"
```

The harness creates a dependency-free Python WSGI app with its own manifest,
tests, README, agent instructions, and clean `main`. It registers the absolute
external path, generates intelligence only in Gateway-controlled state,
prepares an isolated workspace, changes source plus its test, runs allowlisted
`compileall` and `unittest` actions, verifies evidence, then explicitly creates
one local `agent/<job-id>-...` branch and commit. It repeats publication with
the same idempotency key and requires the result and commit count to remain
unchanged. No remote is configured, nothing is pushed or merged, and cleanup
is dry-run only. The destination must not already exist; use a new path for a
new run rather than overwriting prior evidence or Git history.

## CLI

After installation, these commands form the supported local interface:

```text
upg doctor
upg status
upg status --json
upg cleanup --dry-run --keep-last 10
upg project show universal-project-gateway
upg project register fixtures\python_demo\PROJECT_MANIFEST.yaml
upg project list
upg project show python-demo
upg task prepare --project python-demo --request "Change the greeting"
upg task inspect <job-id>
upg task diff <job-id>
upg task validate <job-id>
upg task evidence <job-id>
upg demo
upg mcp serve
```

Run `upg --help` for the installed command surface. CLI and MCP operations
return structured results; failures are not hidden behind a zero exit code.

`upg doctor` checks the checkout, registry, root manifest, SQLite schema,
adapters, sandbox backends, cached intelligence, latest evidence, and MCP
imports without starting a server. `upg status` reads registry/job/adapter and
cache summaries; its cache freshness is based on cache age only and does not
rescan source. Cleanup is a plan by default. Actual removal requires
`upg cleanup --execute`; even then, only immediate directories belonging to
older terminal jobs are eligible, and registered source or durable Gateway
paths are always refused.

## Manage UPG with UPG

`registry/projects.yaml` seeds `universal-project-gateway` into a fresh runtime
registry. Its relative seed paths are resolved against the configured Gateway
root, so the checkout remains portable. If `var/registry/projects.yaml` already
predates this registration, register the root manifest once with
`upg project register PROJECT_MANIFEST.yaml`.

The smallest self-management workflow prepares an inspection job, creates an
isolated snapshot, runs only the root manifest's mandatory `lint` and `test`
actions, and verifies the resulting evidence:

```powershell
$python = ".\.venv\Scripts\python.exe"
$prepared = & $python -m universal_project_gateway.cli task prepare `
  --project universal-project-gateway `
  --request "Inspect the UPG self-registration metadata." `
  --target PROJECT_MANIFEST.yaml `
  --target registry/projects.yaml `
  --operation inspect | ConvertFrom-Json
$jobId = $prepared.job.job_id
& $python -m universal_project_gateway.cli task validate $jobId
& $python -m universal_project_gateway.cli task evidence $jobId
```

The manifest's `stack.managed_path_groups` describes the source, documentation,
test, and script groups managed by this project. Enforcement remains the
current schema's canonical workspace containment, `protected_paths`,
permissions, fixed action names, and Python adapter argv allowlist. The
self-registration does not add a generic command runner.

## Local MCP server

Start the stdio server with either:

```powershell
python -m universal_project_gateway.mcp_server --transport stdio
```

```bat
START_GATEWAY.bat
```

Stdio is local process transport, not a public service. A future ChatGPT Web
connection would require a separately deployed HTTPS endpoint with strong
authentication, per-user authorization, request limits, auditing, and an
independent security review. Do not expose this MVP through an ad-hoc tunnel.

## Repository guide

- `src/universal_project_gateway/`: policy, jobs, workspaces, adapters, evidence,
  CLI, and MCP server.
- `fixtures/`: unrelated Python and Node.js managed projects.
- `PROJECT_MANIFEST.yaml`: the validated contract for managing UPG itself.
- `registry/projects.yaml`: portable versioned seed catalog containing UPG;
  mutable registrations are persisted under ignored `var/registry/`, while
  the demo uses `var/demo/`.
- `state/CURRENT_STATE.json`: conservative implementation and verification
  checkpoint.
- `docs/`: architecture, trust model, manifest and MCP contracts, runbook,
  roadmap, and design decision record.
- `scripts/`: demo and verification helpers.
- `scripts/create_real_project_fixture.py` and
  `scripts/validate_real_project_integration.py`: controlled external-project
  creation and end-to-end proof; they are not production deployment tools.
- `tests/`: unit, integration, and security tests.

Generated job workspaces and evidence are intentionally ignored under
`workspaces/` and `artifacts/`. See [the runbook](docs/RUNBOOK.md) for recovery
and verification, and [the security model](docs/SECURITY_MODEL.md) before
extending any authority.
