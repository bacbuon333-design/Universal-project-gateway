# Architecture

## System identity

Universal Project Gateway (UPG) is a synchronous, local control plane for
project-scoped software changes. It separates an AI client's intent from the
authority to inspect files, mutate a copy, execute validation, and publish a
local Git commit. A project manifest supplies the project-specific facts; the
Gateway core remains stack- and domain-neutral.

This MVP is a locally testable architectural proof, not a production security
boundary.

## Vertical slice

```text
AI, MCP client, or CLI
          |
          v
  Gateway service and policy
          |
          +---- registry + validated PROJECT_MANIFEST.yaml
          |
          +---- SQLite job and event store
          |
          +---- context-pack compiler (bounded, redacted)
          |
          +---- workspace manager ----> workspaces/jobs/<job-id>/workspace
          |                |
          |                +---- scoped text filesystem
          |                +---- allowlisted runtime adapter
          |
          +---- deterministic diff + evidence ledger
                              |
                              v
                       artifacts/jobs/<job-id>
```

The CLI and MCP server are thin protocol surfaces over the same service. They
do not receive broader filesystem or process authority than the service.

## Components

### Manifest and registry

`PROJECT_MANIFEST.yaml` describes identity, source location, memory, protected
paths, allowed validation actions, and publication policy. Registration
validates the manifest and stores only safe project metadata. Resolution is by
exact project ID or exact normalized registered path; an arbitrary path does
not become trusted because a caller supplied it.

### Intent and policy

The deterministic intent compiler normalizes a bounded request into target
scope, expected operations, validation, publication mode, and risk. It reports
`requires_ai_planning` when heuristics cannot safely characterize the work.
Policy then makes an explicit allow/refuse decision. The compiler does not
grant authority, and natural language never becomes executable input.

### Jobs and events

SQLite records each job and append-style events. Canonical job states are
`queued`, `prepared`, `running`, `waiting_for_approval`, `completed`, `failed`,
and `cancelled`. State transitions are validated. A synchronous runner is
sufficient for the MVP, while durable records leave a recovery seam for a
future worker model.

### Context packs

The context compiler combines Gateway rules, the validated manifest, declared
memory, optional project state, a bounded tree, requested targets, protected
paths, validation requirements, publication policy, and Git metadata. It skips
dependencies, VCS internals, outputs, caches, binaries, artifacts, and
protected paths. Size and file-count limits are recorded along with omissions
and truncation; the context pack never implies full-repository understanding.

### Isolated workspaces and scoped files

A job copies the registered project into
`workspaces/jobs/<job-id>/workspace/`, excluding unsafe or expensive content.
The source remains read-only during ordinary work. All file methods require a
job ID and a workspace-relative path. Canonical containment checks run before
access; path traversal, absolute paths, and escaping links are refused.

Only bounded UTF-8 text operations are mutable in this MVP. Binary content is
metadata-only. A deletion request may be recorded for approval, but deletion
does not execute.

### Runtime adapters

Runtime adapters translate a named manifest action such as `test` into a
reviewed argv array. The Python adapter permits selected interpreter module
operations; the Node adapter permits selected Node/package scripts. Processes
run with `shell=False`, an explicit workspace working directory, a timeout, a
small environment allowlist, and captured output. There is no generic execute
method exposed to callers.

### Evidence ledger

Each terminal job writes task, intent, context, snapshot, operations, changed
files, diff, validation, process logs, environment, and final-report evidence.
`manifest.sha256.json` covers every evidence file except itself. Evidence is
deterministically serialized where practical and secrets are redacted.
Mandatory validation must pass before a job can report success.

### Constrained Git publication

R3 publication is separate from ordinary editing and requires both manifest
permission and explicit method input. It creates a non-default branch named
`agent/<job-id>-<slug>`, stages only intended paths, and creates a local commit.
Direct default-branch commits, merge, force-push, global configuration changes,
and implicit deployment are outside the authority model.

## End-to-end sequence

1. Validate and register a project manifest.
2. Compile intent and policy; persist a queued job.
3. Build bounded context and copy the registered source into a fresh workspace.
4. Inspect and modify only approved workspace-relative text paths.
5. Execute required named validation through the project's adapter.
6. Compare the workspace with the source and create `patch.diff`.
7. Finalize the evidence ledger, checksums, and job state.
8. Optionally request the separately gated local-branch publication path.

The demo repeats this flow with a new job ID. It never resets another job's
workspace or evidence.

## Persistent and generated data

Durable repository contracts live in `docs/`, `state/`, `registry/`, and each
fixture manifest. Mutable runtime data lives under ignored directories:

```text
var/                         SQLite and mutable runtime registry
workspaces/jobs/<job-id>/    isolated working copies
artifacts/jobs/<job-id>/     evidence bundles
```

No database or generated artifact is a source-of-truth replacement for the
registered project's manifest.

## Extension rules

New stacks implement the runtime adapter interface and receive only named,
manifest-declared actions. New protocols call the existing service; they do
not add filesystem or process escape hatches. New business domains are managed
projects with their own manifests and memory, never conditionals in Gateway
core.
