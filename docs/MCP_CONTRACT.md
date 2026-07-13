# MCP contract

## Scope and transport

The MCP server exposes high-level Universal Project Gateway operations over
local stdio. It is a protocol adapter over the same service used by the CLI;
it does not expose a terminal, Python evaluator, machine-wide filesystem, or
raw subprocess primitive.

Start it locally with:

```text
python -m universal_project_gateway.mcp_server --transport stdio
```

No public transport, tunnel, OAuth flow, or ChatGPT Web connection is claimed
or tested by this MVP.

## Result convention

Tools return JSON-compatible structured values. Success values identify the
project or job and the operation-specific result. A refusal or operational
failure includes a stable code and safe message, for example:

```json
{
  "ok": false,
  "error": {
    "code": "PATH_OUTSIDE_WORKSPACE",
    "message": "The requested path is outside the active job workspace."
  }
}
```

Policy refusals also include `allowed`, `risk_level`, and `reason_code` when
appropriate. Stack traces, host secrets, and unrestricted absolute paths are
not protocol output.

## Discovery and project tools

### `gateway_get_status` (read-only)

Returns Gateway version, runtime health summary, and supported capabilities.
It does not install dependencies or modify the host.
The additive `contracts` object reports the active manifest, adapter,
execution, evidence, and project-intelligence contract identifiers.

### `gateway_list_projects` (read-only)

Returns registered project summaries. It accepts no arbitrary path.

### `gateway_list_adapters` (read-only)

Returns installed `upg.adapter/v1` declarations: adapter ID/version, supported
project types and platforms, named capabilities, required tools, and safety
notes. Listing does not inspect the host, install dependencies, prepare a
sandbox, or execute an adapter action.

### `gateway_register_project`

Input: `manifest_path`. The path must identify a local
`PROJECT_MANIFEST.yaml`; the service validates it, normalizes its project
source, rejects credentials and duplicate IDs, and persists safe registry
metadata.

### `gateway_get_project` (read-only)

Input: exact `project_id`. Returns the validated project summary and allowed
capabilities; protected content is never inlined.

### `gateway_get_project_intelligence` (read-only)

Input: exact registered `project_id`. Returns one already-generated,
hash-verified `upg.project_intelligence/v1` document and its Gateway-owned cache
path. It does not rescan project source, execute adapter actions, install
dependencies, or access a network. If no cache exists, it returns
`PROJECT_INTELLIGENCE_NOT_FOUND`; operators generate or refresh through the
local CLI before retrying.

## Job tools

### `gateway_prepare_task`

Input:

```json
{
  "project_id": "python-demo",
  "request": "Change the greeting",
  "target_paths": ["src/greeting.py"],
  "requested_operation": "modify",
  "publication_preference": "none"
}
```

Creates a durable job, normalized intent, context pack, and isolated workspace.
The result includes `job_id`, status, risk, workspace readiness, and whether AI
planning is still required. It never edits registered source.
If project intelligence is missing, preparation performs one safe bounded
generation and embeds only the compact cache reference/summary in context.

### `gateway_get_job` (read-only)

Input: `job_id`. Returns durable state, timestamps, validation summary,
evidence location when available, and redacted failure information.

## Scoped workspace tools

All workspace tools require `job_id`. Every file path is workspace-relative.

- `gateway_list_workspace_files` (read-only): bounded listing for an optional
  relative directory.
- `gateway_search_workspace` (read-only): literal bounded text search; not an
  arbitrary regular-expression engine or host search.
- `gateway_read_workspace_file` (read-only): bounded UTF-8 text read; binary
  content is not returned.
- `gateway_write_workspace_file`: create or replace bounded UTF-8 text when R1
  and manifest scope permit it.
- `gateway_move_workspace_file`: move one contained, non-protected relative path
  to another contained path.
- `gateway_request_delete`: record a non-executing deletion approval request;
  deletion remains unavailable in this MVP.
- `gateway_get_diff` (read-only): return or materialize the deterministic diff
  between source snapshot and active workspace.

Successful scoped operations, validation steps, and state transitions are
recorded as job events. Structured policy errors explain refusals. The server
rejects absolute paths, traversal, escaping links, protected paths, binary
mutation, and oversize payloads.

## Validation and evidence tools

### `gateway_validate`

Input: `job_id` and, when supported, a named action selected from the validated
manifest. The caller cannot supply an executable or arguments. The result
reports action, argv as executed, status (`passed`, `failed`, `skipped`, or
`not_run`), exit code, duration, timeout, and bounded/redacted output metadata.
Each check additively identifies `upg.execution/v1` and includes the resolved
adapter ID, adapter version, `upg.adapter/v1` contract, and capability. Sandbox
backend and safety metadata remain present under `sandbox`.

Mandatory requirements must pass before the service marks a task successful.

### `gateway_get_evidence` (read-only)

Input: `job_id`. Returns the evidence location and checksum verification
status. It does not return protected raw content.

## Publication tool

### `gateway_publish_local_branch`

Input includes `job_id` and `explicit: true`. This R3 operation is allowed
only when project permission,
publication policy, repository cleanliness, changed-path scope, and branch
policy all pass. It can create `agent/<job-id>-<slug>` and a local commit.

It cannot commit to the detected default branch, merge, force-push, change
global Git configuration, deploy, or obtain credentials. Push is not part of
the default MCP contract.

## Explicitly absent capabilities

The server must never register tools equivalent to:

```text
run_any_command
execute_python
execute_shell
browse_entire_machine
delete_source_path
deploy
merge
force_push
read_credentials
```

If a future tool expands authority, it requires a new threat-model review,
explicit risk classification, documentation, tests, and protocol versioning.
