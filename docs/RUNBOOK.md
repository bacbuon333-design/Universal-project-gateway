# Local runbook

## Prerequisites

- Windows PowerShell or Command Prompt
- Python 3.11 or newer (`py -3.11` or `python`)
- Git for Git-controller tests
- Node.js 18 or newer for the Node fixture validation

Docker, cloud accounts, API keys, GitHub credentials, external databases, and
a public MCP tunnel are not required.

## First setup

From the repository root:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps -e ".[dev]"
.\.venv\Scripts\python.exe -m universal_project_gateway.cli doctor
```

If the Python launcher is unavailable, replace `py -3.11` with a Python 3.11+
executable. Do not install dependencies globally. The doctor reports `PASS`,
`WARN`, or `FAIL` for Python, writable runtime directories, SQLite, Git, the
MCP dependency, and fixtures without unexpectedly changing the machine.

## Complete verification

Run:

```bat
VERIFY_GATEWAY.bat
```

It creates or reuses `.venv`, installs the pinned local project, runs Ruff and
compile checks, verifies the root and fixture manifests, runs unit/integration
and security tests, runs the deterministic demo twice, and verifies the newest
evidence bundle. The first failing command stops the batch file with a nonzero
exit code.

Equivalent individual checks are:

```powershell
.\.venv\Scripts\python.exe -m ruff check src scripts tests
.\.venv\Scripts\python.exe -m compileall -q src scripts tests
.\.venv\Scripts\python.exe scripts\verify_manifest.py PROJECT_MANIFEST.yaml fixtures\python_demo\PROJECT_MANIFEST.yaml fixtures\node_demo\PROJECT_MANIFEST.yaml
.\.venv\Scripts\python.exe -m pytest tests\unit tests\integration
.\.venv\Scripts\python.exe -m pytest tests\security
.\.venv\Scripts\python.exe scripts\run_demo.py
.\.venv\Scripts\python.exe scripts\run_demo.py
.\.venv\Scripts\python.exe scripts\verify_gateway.py --latest
git diff --check
```

When Node.js or an optional platform feature is absent, only a test designed to
detect that feature may skip, with its reason shown. Core path isolation and
the Python vertical slice must not skip.

## Run the demo

```bat
RUN_DEMO.bat
```

Expected milestone lines are:

```text
project registered
job prepared
workspace created
file modified
validation passed
patch created
evidence verified
```

The demo registers both fixture manifests, exercises the Python fixture, and
prints its unique job ID and evidence path. Confirm that:

1. `fixtures/python_demo/src/greeting.py` still contains `Hello`.
2. `workspaces/jobs/<job-id>/workspace/src/greeting.py` contains
   `Hello from UPG`.
3. `artifacts/jobs/<job-id>/patch.diff` shows only the intended greeting edit.
4. `manifest.sha256.json` verifies.
5. A second run has a different job ID and leaves the first bundle unchanged.

## Register and inspect projects

```bat
REGISTER_PROJECT.bat fixtures\python_demo\PROJECT_MANIFEST.yaml
```

Or use the CLI directly:

```powershell
upg project register fixtures\python_demo\PROJECT_MANIFEST.yaml
upg project register fixtures\node_demo\PROJECT_MANIFEST.yaml
upg project list
upg project show python-demo
```

Registration rejects duplicate IDs, malformed manifests, credentials, and
untrusted paths. The versioned `registry/projects.yaml` seeds a new local
registry; mutable registry and job state are persisted under ignored `var/`.

## Prepare and validate a UPG self-management job

The root `PROJECT_MANIFEST.yaml` registers this repository as
`universal-project-gateway`. A fresh Gateway runtime copies its portable seed
record from `registry/projects.yaml`; relative paths in that seed are resolved
against the configured Gateway root. Check the active record first:

```powershell
$python = ".\.venv\Scripts\python.exe"
& $python -m universal_project_gateway.cli project show universal-project-gateway
```

If the ignored `var/registry/projects.yaml` was created before self-registration
was added, register the root manifest once. Do not repeat registration after it
succeeds because duplicate project IDs are intentionally refused.

```powershell
& $python -m universal_project_gateway.cli project register PROJECT_MANIFEST.yaml
```

Prepare a read-only task with explicit workspace-relative targets, then capture
the generated job ID:

```powershell
$prepared = & $python -m universal_project_gateway.cli task prepare `
  --project universal-project-gateway `
  --request "Inspect the UPG self-registration metadata." `
  --target PROJECT_MANIFEST.yaml `
  --target registry/projects.yaml `
  --operation inspect `
  --idempotency-key "upg-inspection-001" | ConvertFrom-Json
$jobId = $prepared.job.job_id
$prepared.workspace
$prepared.evidence
```

The source checkout remains read-only during this job. Confirm the workspace is
under `workspaces/jobs/$jobId/workspace`, then run the two mandatory named
actions from the manifest and verify the checksummed evidence:

```powershell
& $python -m universal_project_gateway.cli task validate $jobId `
  --idempotency-key "upg-inspection-validation-001"
& $python -m universal_project_gateway.cli task evidence $jobId
& $python scripts\verify_gateway.py "artifacts\jobs\$jobId"
```

The recorded validation argv must resolve to the active Python executable plus
`-m compileall ...` and `-m pytest ...`. Any caller-supplied executable, shell
operator, appended flag, installation, push, merge, deployment, or R4 action
remains outside this workflow.

## Lease, cancellation, recovery, and replay operations

Preparation, validation, and publication accept bounded idempotency keys. A
repeated prepare key for identical input returns the existing job/workspace. A
completed validation or publication key returns its stored result without
running another process or creating another Git commit. Reusing a prepare key
with different input is refused.

Inspect durable ownership and event history without exposing the bearer lease:

```powershell
& $python -m universal_project_gateway.cli task inspect $jobId
```

The public job payload shows worker ID, attempt, heartbeat, and lease expiry,
but deliberately omits `lease_token`. Claim and heartbeat are internal worker
operations; do not add the token to logs, task requests, or evidence.

Request cooperative cancellation:

```powershell
& $python -m universal_project_gateway.cli task cancel $jobId `
  --reason "Operator stopped the local job"
```

A queued, prepared, waiting, or recovery job cancels immediately. An active
worker observes the flag at its next phase/action boundary. UPG does not yet
kill a validation process tree already in progress; wait for the action timeout
or return before treating cancellation as terminal.

If inspection shows an expired lease, run the exact-job recovery command:

```powershell
& $python -m universal_project_gateway.cli task recover $jobId
```

Recovery refuses a live lease. A claim that expired before its phase began
returns to its stable origin. An expiry during preparation, validation, running,
or publication becomes `recovery_required`; preserve the workspace/evidence and
review possible partial effects instead of blindly replaying it.

## Start local MCP

```bat
START_GATEWAY.bat
```

The default is stdio:

```powershell
.\.venv\Scripts\python.exe -m universal_project_gateway.mcp_server --transport stdio
```

Stdio is intended for a local MCP client that launches the process. Do not bind
this MVP publicly or place an ad-hoc tunnel in front of it.

## Evidence verification

For the latest job:

```powershell
.\.venv\Scripts\python.exe scripts\verify_gateway.py --latest
```

For a specific bundle, pass its directory if supported by the helper or use
the CLI's evidence operation. Verification recalculates every recorded SHA-256
digest and rejects missing, extra-required, or changed covered files. The
checksum manifest does not cover itself by design.

Validation evidence distinguishes:

- `passed`: action executed and met its success condition;
- `failed`: action executed but did not pass;
- `skipped`: action intentionally omitted with a recorded reason;
- `not_run`: no attempt occurred.

A final report must not claim success unless all mandatory requirements passed.

## Safe cleanup and reset

Generated data is isolated under `var/`, `workspaces/`, and `artifacts/`. The
demo may reset only runtime records it created for its own deterministic setup;
it must not recursively remove registered source or another job's output.

Before manual cleanup, close Gateway processes and verify the canonical target
is inside this repository. Remove individual job directories by exact job ID.
Never use a broad deletion command against a computed or empty path.

## Troubleshooting

### `python-demo` test fails before a demo edit

That is expected when the fixture source still returns `Hello`. Its validation
test intentionally expects `Hello from UPG`; validate the isolated post-edit
workspace, not the registered source.

### Node fixture is skipped

Run `node --version`. Node 18+ is required and no `npm install` is needed.

### A path operation is refused

Use a workspace-relative path and confirm it is not protected. Do not weaken
canonical containment checks to work around a refusal. Inspect the structured
reason code and active job workspace instead.

### Source is stale

The registered source changed after workspace creation. Preserve the existing
evidence, create a new job/workspace from the new source, and reapply only the
intended change. Do not overwrite the source or conceal the warning.

### Evidence checksum fails

Treat the bundle as modified or incomplete. Do not regenerate only the checksum
to make it pass. Preserve the failing bundle for diagnosis and rerun the job to
produce a new evidence directory.

### Publication is refused

Confirm the manifest allows Git publication, the call explicitly requested R3,
the repository is clean and non-default-branch publication is possible, and
only intended paths are staged. Never work around refusal with force, merge, or
global Git changes.

## Incident handling

If a secret appears in output or evidence, stop the process, restrict access to
the local artifacts, rotate the secret outside UPG, and retain only a safely
redacted diagnostic record. Checksums provide integrity, not confidentiality.
