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
DOCTOR_GATEWAY.bat
```

If the Python launcher is unavailable, replace `py -3.11` with a Python 3.11+
executable. Do not install dependencies globally. The doctor reports `PASS`,
`WARN`, or `FAIL` for Python/venv/import readiness, Git branch/status/origin and
checkpoint, required paths, registry and manifest validity, read-only SQLite
health/migration status, adapters, sandbox backends, project-intelligence
caches, latest evidence verification, and MCP imports. It does not create
runtime directories, initialize/migrate SQLite, refresh caches, install
packages, or start a transport.

An exact tag at `HEAD` is a passing checkpoint. A reachable older tag is only
a `WARN` and includes the number of commits since that checkpoint. Do not treat
the nearest tag as the current release. For the complete local-v0.2 verdict,
limitations, and pre-tag checklist, see
[`LOCAL_V02_READINESS.md`](LOCAL_V02_READINESS.md).

## Inspect local status

Use the human summary interactively or request stable JSON for automation:

```powershell
upg status
upg status --json
```

The report includes registered projects, job counts by state, the latest
completed and failed jobs, exact or nearest Git checkpoint status and distance,
adapter declarations,
the default sandbox safety label, and evidence contract/schema versions.
Intelligence freshness is explicitly `cache_age_only_no_source_rescan`: recent
means generated within 24 hours, not proof that source is unchanged. Run the
explicit intelligence generation command when a refresh is required.

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

To update an existing clean `main` checkout and immediately verify it, run:

```bat
PULL_AND_VERIFY.bat
```

The helper refuses dirty worktrees and non-`main` branches, uses
`git pull --ff-only origin main`, and never stashes, resets, merges, or
force-pushes operator work. It fails closed if Git cannot inspect status or
determine the current branch. `VERIFY_GATEWAY.bat` also verifies that the
selected/reused virtual environment runs Python 3.11 or newer before package
installation or test execution.

## Local v0.2 pre-tag audit flow

From a clean, non-default audit branch/worktree:

```powershell
cmd /c VERIFY_GATEWAY.bat
upg intelligence generate universal-project-gateway
cmd /c DOCTOR_GATEWAY.bat
upg status --json
upg cleanup --dry-run --keep-last 10
upg adapter list
.\.venv\Scripts\python.exe scripts\verify_gateway.py --latest
cmd /c ".venv\Scripts\python.exe -m universal_project_gateway.mcp_server --transport stdio < nul"
```

The final MCP command is a local startup/EOF smoke test, not a public binding.
Require zero `FAIL` doctor checks, inspect all warnings, confirm cleanup reports
`dry_run: true` and `deleted_count: 0`, and preserve the latest evidence path.
The release-candidate review confirmed that `v0.1.9` resolves exactly to the
real-project checkpoint `9d1414ef3056888ff5c651466ea688f53317fb65`.
The package version for the local-v0.2 candidate is `0.2.0+local`; the release
tag name is `v0.2.0-local`. Verification must never create, move, or delete a
tag. Reconcile any existing tag that does not identify the reviewed release
commit through a separately authorized maintainer procedure.

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

## Select and inspect a sandbox backend

CLI, MCP, and ordinary `GatewayService` construction use
`UnsafeLocalSandboxBackend` for development compatibility. The name is
deliberate: it keeps the previous local subprocess behavior and is not an OS
security boundary. Use it only with trusted local projects.

`LocalProcessSandboxBackend` is an opt-in hardening foundation for an embedded
Python caller:

```python
from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.runner import LocalRunner
from universal_project_gateway.sandbox import LocalProcessSandboxBackend
from universal_project_gateway.service import GatewayService

config = GatewayConfig.discover()
runner = LocalRunner(config, sandbox_backend=LocalProcessSandboxBackend())
gateway = GatewayService(config, runner=runner)
```

This backend filters the environment independently, refuses a cwd outside the
prepared workspace, always disables the shell, enforces the declared timeout,
and performs best-effort process cleanup. It does not require Docker, Hyper-V,
Windows Sandbox, WSL, admin privileges, or dependency installation.

After validation, inspect `validation.json` and `environment.json` in the job's
evidence directory. Each executed check records backend ID, safety level,
runtime action, argv, cwd, timeout, return code, shell and environment flags,
network-policy enforcement, and limitation notes. `environment.json` also
records the prepared/destroyed handle and collected executions. Environment
values and ambient secrets are not recorded.

Treat `deny_requested` network policy as evidence of intent only. Neither local
backend can enforce network denial without an OS/container facility. Also note
that cooperative cancellation prevents a not-yet-started action but does not
kill a process already running; timeout cleanup is best effort.

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

## Validate a controlled external Git project

Use a new path that is clearly outside the UPG checkout, `workspaces/`,
`artifacts/`, and every `.git` directory. The following command creates and
tests a small dependency-free Python WSGI repository:

```powershell
.\.venv\Scripts\python.exe scripts\validate_real_project_integration.py `
  --gateway-root $PWD `
  --project-root "Z:\UPG Test Projects\hello-web-app"
```

The destination must not exist. The creator refuses overwrite, links/reparse
parents, paths inside UPG, and paths containing `.git`. It initializes a local
repository with an invalid test-only email, a clean `main`, and no remotes.
The integration then performs these gates:

1. Register the exact external manifest and confirm arbitrary paths remain
   untrusted.
2. Generate `upg.project_intelligence/v1` under ignored Gateway state and
   confirm no cache is written into the external project.
3. Prepare a job whose workspace is contained by the configured workspace root
   and disjoint from source.
4. Replace the greeting and its exact test through scoped workspace methods;
   require the patch to contain only those two paths.
5. Run only manifest-declared `lint` (`compileall`) and `test` (`unittest`)
   actions through the Python adapter and sandbox backend.
6. Verify the 14-file evidence bundle, event chain, payloads, checksum manifest,
   and final-attestation binding independently.
7. Confirm source is byte-for-byte clean on `main`, then grant explicit R3 and
   create one `agent/<job-id>-workspace-change` commit containing only the two
   intended paths.
8. Replay publication with the same key, require the same result and exactly
   one commit, and confirm the `main` ref is unchanged.
9. Run doctor/status against the isolated runtime and a cleanup dry-run that
   must not include or delete the external project.

The command intentionally leaves the external repository on its local review
branch for inspection. It never configures a remote, pushes, merges, resets,
installs dependencies, or removes the project. Preserve its reported runtime,
job, workspace, intelligence, and evidence paths for review. For another run,
choose another absent destination instead of deleting or rewriting the first.

The full test suite exercises the same workflow in a disposable external temp
directory. This is controlled trusted test code running through the default
`unsafe-local` backend, not a production security or rollout claim.

## Generate and inspect project intelligence

Refresh one registered project with a bounded, deterministic metadata scan,
then list or show verified caches:

```powershell
upg intelligence generate universal-project-gateway
upg intelligence list
upg intelligence show universal-project-gateway
```

Cache files live at
`var/project_intelligence/<project-id>.json`. `generate` reads only safe,
non-linked, non-protected project files within configured file/byte bounds and
hashes them without executing code. It records relative structure, dependency
filenames, module/test/docs summaries, manifest commands, and installed adapter
declarations. It does not install dependencies, invoke project commands, call a
model or network service, or inspect protected content.

`list`, `show`, and MCP `gateway_get_project_intelligence` verify the semantic
cache hash and do not rescan source. Run `generate` explicitly when source or
the manifest changes. A missing cache is created safely during first task
preparation, and later preparations reuse it until an operator refreshes it.
Treat the cache as an advisory context optimization, never as a replacement for
manifest validation or current-source checks.

## Inspect adapter contracts and capabilities

Adapter discovery is read-only and does not inspect executables or start a
sandbox process:

```powershell
upg adapter list
```

The built-in result contains `python` and `node`, each with adapter version,
`upg.adapter/v1`, supported project types/platforms, named capabilities,
required tools, and safety notes. MCP clients receive the same values from
`gateway_list_adapters`.

Legacy manifest schema `1.0` files need no migration. A manifest that wants an
explicit compatibility gate may add:

```yaml
contract_version: upg.manifest/v1
adapter_requirements:
  - adapter_id: python
    adapter_version: "1.0.0"
    contract_version: upg.adapter/v1
    capabilities: [lint, test]
```

Run `scripts\verify_manifest.py` after changing expectations. An unknown
adapter/capability, project-type mismatch, unsupported platform, wrong contract
or exact version, or ambiguous resolution is a registration error. Do not
weaken requirements or substitute a generic command to bypass the refusal.

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

Preparation includes a compact `upg.project_intelligence/v1` reference in
`context_pack.json`. After validation, the same cache hash is recorded in
`validation.json`, `environment.json`, evidence-chain phase events, and
`attestation.json`.

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
digest and rejects missing, extra-required, or changed covered files. For
evidence schema v2 it also checks JSONL canonical form, sequence order, payload
hashes, event hashes, previous-hash continuity, final-event/attestation binding,
and the compatibility-file manifest digest. The checksum manifest does not
cover itself by design.

A current bundle contains the original 12 compatibility files plus:

- `evidence_events.jsonl`: byte-appended canonical phase events;
- `attestation.json`: final job/source/sandbox/validation metadata;
- `manifest.sha256.json`: SHA-256 coverage for all 14 evidence files.

New `attestation.json` files identify `upg.evidence/v1`, while validation
checks identify `upg.execution/v1` and contain their resolved adapter metadata.
`environment.json.adapter_registry` records the same resolution alongside the
unchanged sandbox backend metadata. Older evidence-schema-v2 attestations
without the additive contract field remain verifiable.

The verifier still accepts a valid legacy bundle with only the original 12
files and manifest, reporting `chain_checked: false`. A current bundle reports
`chain_checked: true` and a positive `events_checked` count.

Do not edit, reorder, remove, or manually regenerate individual event lines.
If verification fails, preserve the entire bundle for diagnosis and create a
new job. Refreshing only `manifest.sha256.json` cannot repair broken event
continuity or an attestation mismatch.

`attestation.json` currently declares the signer as
`universal-project-gateway-local-development` with `signature_algorithm: none`.
This is structured future-signing metadata, not proof of identity or a trusted
timestamp. Do not describe it as cryptographically signed.

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

Preview conservative cleanup first:

```powershell
upg cleanup --dry-run --keep-last 10
upg cleanup --dry-run --workspaces --keep-last 5
upg cleanup --dry-run --artifacts --keep-last 5
```

With no target flag, both workspace and artifact roots are inspected. Only
immediate directories whose IDs match older SQLite jobs in `completed`,
`failed`, or `cancelled` state are candidates. Active, recent, unknown,
linked/reparse, malformed, or escaped paths are skipped. Registered source
roots, `.git`, registry, root manifest, state, and database paths are refused
even if configuration is wrong.

After reviewing every candidate and closing Gateway processes, repeat with
`--execute` to remove those exact directories. The command does not clean
`var/`, migrate the database, delete registry/state, or infer paths from user
text. Never use a broad manual deletion against a computed or empty path.

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
