# Universal Project Gateway

Universal Project Gateway (UPG) is a small, locally runnable architectural
proof for safely applying an AI-assisted change to one of several registered
software projects. It registers a manifest, prepares a durable job, copies the
project into an isolated workspace, permits scoped text operations, executes
only manifest-declared validation actions, and writes a checksummed evidence
bundle.

The same Gateway manages the dependency-free Python and Node.js fixtures in
this repository. No Animation, Trading, Revit, Auto Call, video, or other
project-specific business logic belongs in the Gateway core.

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
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe scripts\run_demo.py
```

Or run the complete Windows verification entry point:

```bat
VERIFY_GATEWAY.bat
```

The deterministic demo registers both fixture manifests, then creates a fresh
Python-fixture job workspace, changes its greeting from `Hello` to
`Hello from UPG`, runs its tests, creates a patch and evidence ledger, and
verifies the ledger. The source fixture is not modified. Each run uses a new
job ID and preserves prior evidence.

## CLI

After installation, these commands form the supported local interface:

```text
upg doctor
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
- `registry/projects.yaml`: versioned seed catalog; mutable registrations are
  persisted under ignored `var/registry/`, while the demo uses `var/demo/`.
- `state/CURRENT_STATE.json`: conservative implementation and verification
  checkpoint.
- `docs/`: architecture, trust model, manifest and MCP contracts, runbook,
  roadmap, and design decision record.
- `scripts/`: demo and verification helpers.
- `tests/`: unit, integration, and security tests.

Generated job workspaces and evidence are intentionally ignored under
`workspaces/` and `artifacts/`. See [the runbook](docs/RUNBOOK.md) for recovery
and verification, and [the security model](docs/SECURITY_MODEL.md) before
extending any authority.
