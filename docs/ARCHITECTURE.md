# Architecture

## System identity

Universal Project Gateway (UPG) is a synchronous, local control plane for
project-scoped software changes. It separates an AI client's intent from the
authority to inspect files, mutate a copy, execute validation, and publish a
local Git commit. A project manifest supplies the project-specific facts; the
Gateway core remains stack- and domain-neutral.

This MVP is a locally testable architectural proof, not a production security
boundary.

## Control Plane and Runner boundary

```text
AI, MCP client, or CLI
          |
          v
  GatewayService compatibility facade
          |
          v
      ControlPlane
          +---- registry + validated PROJECT_MANIFEST.yaml
          +---- intent compiler + R0-R4 policy
          +---- SQLite job, lease, event, and idempotency store
          +---- bounded context compiler
          +---- constrained Git publication
          |
          | validated manifest, persisted job, named actions
          v
      Runner protocol
          |
          v
      LocalRunner (current implementation)
          +---- workspace manager ----> workspaces/jobs/<job-id>/workspace
          +---- scoped text filesystem
          +---- allowlisted runtime adapter
          +---- deterministic patch + evidence ledger
                                      |
                                      v
                               artifacts/jobs/<job-id>
```

The CLI and MCP server remain thin protocol surfaces over `GatewayService`.
The facade delegates to `ControlPlane`, which authorizes and orchestrates a
`Runner`. Protocol clients do not receive direct runner, filesystem, evidence,
or process authority.

This is a dependency and responsibility boundary, not an operating-system
security boundary. `LocalRunner` remains in-process and has the same host
identity as the Control Plane. SQLite now assigns durable phase ownership to a
local worker identity, but that lease is concurrency control rather than
process isolation or remote-worker authentication.

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

### Jobs, leases, and events

SQLite schema version 2 records jobs, append-style events, worker leases, and
idempotent operation results. The formal states are `queued`, `claimed`,
`preparing`, `running`, `validating`, `waiting_for_approval`, `publishing`,
`completed`, `failed`, `cancelled`, and `recovery_required`. `prepared` remains
as a compatibility state for an isolated workspace waiting for its next local
phase.

A claim atomically records a worker ID, unpredictable bearer lease token,
expiry, heartbeat, origin state, and incremented attempt. Only the owning
worker with an unexpired token can advance `claimed`, `preparing`, `running`,
`validating`, or `publishing`. Lease tokens are never returned by the public
job serializer or written to evidence and events.

Heartbeat refreshes are durable events. An expired lease that has not entered
an effectful phase can return to its stable origin state. Expiry during
preparation, validation, running, or publication moves the job to
`recovery_required`, because replay safety cannot be assumed. This is a local
SQLite ownership foundation, not a distributed queue or remote worker model.

Prepare idempotency is unique per project and key. Validation and publication
use a separate per-job operation ledger that stores `started`, `completed`, or
`failed` plus a replayable result. Reusing a key with different prepare input
is refused; an in-progress duplicate returns a structured conflict rather than
starting a second effect.

### Control Plane

`ControlPlane` owns project lookup, manifest loading, intent compilation,
policy decisions, durable job transitions, context compilation, event
orchestration, and the high-level API behavior used by every protocol surface.
It does not open workspace files or construct child-process argv directly.

The Control Plane passes the runner only persisted job metadata, a validated
`ProjectManifest`, workspace-relative paths, and fixed validation action names.
Natural-language request text never becomes a runner command. R3 Git
publication remains a separate Control Plane gate after successful validation.
The Control Plane claims each effectful phase, supplies cooperative heartbeat
and cancellation callbacks to `LocalRunner`, and releases the lease only when
a stable state has been committed.

### Runner protocol and LocalRunner

`Runner` defines the bounded execution seam for workspace preparation, scoped
file operations, validation, patch generation, and evidence production.
`LocalRunner` implements the existing synchronous behavior by composing
`WorkspaceManager`, `ScopedWorkspace`, the Python/Node runtime adapters, and
`EvidenceLedger`.

Cancellation is cooperative. The runner checks before and after each named
validation action, while the Control Plane checks between preparation,
validation, source-copy, and Git-publication phases. It records cancellation
and evidence deterministically, but it does not terminate an operating-system
process tree already executing an adapter action.

The runner does not own the project registry, manifest discovery, intent
compiler, policy engine, or job state machine. It cannot register an arbitrary
source path or accept arbitrary executable text. A future sandbox backend may
implement the same responsibilities only after a separate threat model and
contract review; no such backend is part of this checkpoint.

`GatewayService` remains a compatibility facade. Existing CLI, MCP, demo, and
Python callers retain their method names and result shapes while implementation
work is delegated through `ControlPlane` and `LocalRunner`.

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
2. Compile intent and policy; atomically create or replay a queued job by its
   optional prepare idempotency key.
3. A local worker claims the job, enters `preparing`, and the Control Plane
   builds bounded context while the Runner copies the registered source into a
   fresh workspace. The stable compatibility state becomes `prepared`.
4. The Control Plane authorizes each operation; the Runner inspects or modifies
   only approved workspace-relative text paths.
5. The worker claims the prepared job, enters `validating`, heartbeats between
   named actions, and checks cooperative cancellation at every action boundary.
6. The Runner compares the workspace with its baseline and creates
   `patch.diff`.
7. The Control Plane commits a terminal state and the Runner finalizes the
   backward-compatible evidence ledger and checksums. Repeated validation with
   the same key returns the recorded result.
8. Optionally claim the separately gated `publishing` phase. Repeated publish
   with the same key returns the original result without a second commit.

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
manifest-declared actions. New execution backends implement the Runner
responsibilities without moving policy or project discovery into the execution
plane. New protocols call the compatibility facade or Control Plane; they do
not add filesystem or process escape hatches. New business domains are managed
projects with their own manifests and memory, never conditionals in Gateway
core.
