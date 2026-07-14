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
          +---- ProjectIntelligenceCache (`upg.project_intelligence/v1`)
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
          +---- AdapterRegistry (`upg.adapter/v1`)
          |         +---- PythonAdapter capabilities
          |         +---- NodeAdapter capabilities
          |         +---- named action resolution ----> SandboxBackend
          |                                  +--> UnsafeLocalSandboxBackend (default)
          |                                  +--> LocalProcessSandboxBackend (opt-in)
          +---- deterministic patch + evidence ledger
                +---- 12 compatibility files + SHA-256 manifest
                +---- append-only event chain + unsigned attestation
                                      |
                                      v
                               artifacts/jobs/<job-id>
```

The CLI and MCP server remain thin protocol surfaces over `GatewayService`.
The facade delegates to `ControlPlane`, which authorizes and orchestrates a
`Runner`. Protocol clients do not receive direct runner, filesystem, evidence,
or process authority.

These are dependency and responsibility boundaries, not operating-system
security boundaries. `LocalRunner` remains in-process and has the same host
identity as the Control Plane. The sandbox interface isolates process-launch
policy in code, but neither local backend constrains the child with a separate
kernel identity or filesystem namespace. SQLite lease ownership remains
concurrency control rather than process isolation or remote-worker
authentication.

## Components

### Manifest and registry

`PROJECT_MANIFEST.yaml` describes identity, source location, memory, protected
paths, allowed validation actions, and publication policy. Registration
validates the manifest and stores only safe project metadata. Resolution is by
exact project ID or exact normalized registered path; an arbitrary path does
not become trusted because a caller supplied it.

Manifest schema `1.0` maps to contract `upg.manifest/v1`. Existing manifests
without a `contract_version` or `adapter_requirements` field retain their
original meaning. A manifest may additionally pin an installed adapter
contract/version and require named capabilities; registration refuses an
unknown adapter, incompatible project type/platform, unsupported capability,
or unsatisfied exact version before a job is created.

### Project intelligence cache

`ProjectIntelligenceScanner` produces a deterministic, rule-based summary from
a validated manifest and a bounded tree fingerprint. It records relative
important/protected paths, entrypoints, allowlisted validation/build commands,
adapter capabilities, dependency-file hints, and compact module/test/docs
maps. Python and Node receive only filename/layout conventions; project modules
are never imported, commands are never executed, and no model, network, vector
store, embedding service, or dependency installation is involved.

The walker sorts entries, refuses links/reparse points, skips manifest-protected
and sensitive/default-excluded paths before content access, and enforces file,
per-file byte, and total hash-byte limits. Source and cache hashes use canonical
UTF-8 JSON and project-relative paths. `generated_at` and `cache_hash` are
excluded from the semantic cache-hash material so unchanged source metadata has
a stable hash while retaining an operational generation timestamp.

Verified JSON documents live under Gateway-controlled ignored state at
`var/project_intelligence/<project-id>.json`, never in a registered project's
managed source paths. `intelligence generate` performs the bounded refresh;
`intelligence show` and MCP reads verify and return the existing cache without
rescanning. Job preparation safely creates a missing cache once, then injects
only a compact subset into the context pack. The cache is advisory metadata;
the current manifest remains the authority for policy and validation.

### Local operations layer

`operations.py` provides Windows-first, process-local observability without
adding a daemon, dashboard, remote worker, or execution endpoint. `doctor`
composes independent `PASS`/`WARN`/`FAIL` checks and deliberately opens the job
database read-only: migration and runtime-directory creation remain normal
Gateway startup responsibilities. Its MCP smoke check imports the server
factory but never constructs a service or starts a transport.

Doctor treats only an exact tag at `HEAD` as a passing Git checkpoint. When
HEAD is beyond the nearest reachable tag it emits a warning with the commit
distance, and status exposes the same additive checkpoint metadata so an
operator cannot mistake an old tag for the current release.

`status` is a read-only snapshot of the portable/runtime registry, schema-v2
job metadata, built-in adapter declarations, cached intelligence age, default
sandbox label, and evidence schema. It reports no lease tokens, request text,
environment values, or protected content. Intelligence freshness describes
cache age only and cannot establish current-source equivalence.

`cleanup` owns the only new deletion path. Dry-run is the default; execution
requires explicit `--execute`. Eligibility is the intersection of a terminal
SQLite job, an immediate safe-named directory under a configured runtime root,
and the retention window. Canonical overlap checks refuse every registered
source root and durable/protected Gateway path before deletion begins.

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
`WorkspaceManager`, `ScopedWorkspace`, the Python/Node runtime adapters, a
`SandboxBackend`, and `EvidenceLedger`. It prepares one sandbox handle for a
validation phase, passes only adapter-reviewed requests to it, collects
execution metadata, and destroys the handle before evidence is finalized.

Cancellation is cooperative. The runner checks before and after each named
validation action, while the Control Plane checks between preparation,
validation, source-copy, and Git-publication phases. It records cancellation
and evidence deterministically, but it does not terminate an operating-system
process tree already executing an adapter action.

The runner does not own the project registry, manifest discovery, intent
compiler, policy engine, or job state machine. It cannot register an arbitrary
source path or accept arbitrary executable text. Additional sandbox backends
require a separate threat-model and contract review and must not expand the
runtime action vocabulary or bypass adapter argv validation.

`GatewayService` remains a compatibility facade. Existing CLI, MCP, demo, and
Python callers retain their method names and result shapes while implementation
work is delegated through `ControlPlane` and `LocalRunner`.

### Context packs

The context compiler combines Gateway rules, the validated manifest, declared
memory, optional project state, a bounded tree, requested targets, protected
paths, validation requirements, publication policy, and Git metadata. It skips
dependencies, VCS internals, outputs, caches, binaries, artifacts, and
protected paths. Size and file-count limits are recorded along with omissions
and truncation. A compact verified project-intelligence entry supplies the
latest cache/source hashes and structural summaries without duplicating the
full scan. The context pack never implies full-repository understanding.

### Isolated workspaces and scoped files

A job copies the registered project into
`workspaces/jobs/<job-id>/workspace/`, excluding unsafe or expensive content.
The source remains read-only during ordinary work. All file methods require a
job ID and a workspace-relative path. Canonical containment checks run before
access; path traversal, absolute paths, and escaping links are refused.

Only bounded UTF-8 text operations are mutable in this MVP. Binary content is
metadata-only. A deletion request may be recorded for approval, but deletion
does not execute.

### Versioned contracts and adapter registry

Five additive contract identifiers separate compatibility families from their
implementation schemas: `upg.manifest/v1`, `upg.adapter/v1`,
`upg.execution/v1`, `upg.evidence/v1`, and
`upg.project_intelligence/v1`. Machine-readable schema descriptions live in
`contracts.py`. Existing manifest schema `1.0` and evidence schema `2.0` remain
intact; the contract identifiers do not silently renumber either format.

`AdapterRegistry` owns installed adapter declarations and deterministic action
resolution. Each declaration records adapter ID/version/contract, supported
project types and platforms, named capabilities, required tools, and bounded
safety notes. The reviewed built-ins are Python and Node. `LocalRunner` asks
the registry to resolve each mandatory action, then records the resolution in
the validation result, environment evidence, and evidence-chain phase events.
An explicitly selected `commands.<action>.adapter` must be declared and
compatible; ambiguous or unsupported resolution is refused.

Runtime adapters translate a named manifest action such as `test` into a
reviewed `SandboxExecutionRequest` under `upg.execution/v1`. The Python adapter
permits selected interpreter module operations; the Node adapter permits
selected Node/package scripts. Adapters do not launch subprocesses. There is
no generic execute method exposed to callers. The CLI `adapter list` command
and MCP `gateway_list_adapters` tool expose only read-only declarations and do
not probe tools or start processes.

`SandboxBackend` owns prepare, execute, collect, and destroy. Requests contain
only a fixed runtime action, resolved argv, contained cwd, bounded timeout,
explicit environment, and advisory network policy. Results retain the previous
command-result fields and add backend ID, safety level, `shell=False`,
environment-filtering, network-policy, and limitation metadata.

`UnsafeLocalSandboxBackend` is the development-compatible default and preserves
the previous `subprocess.run` behavior. Its name and evidence explicitly state
that it is not an OS security boundary. `LocalProcessSandboxBackend` is an
opt-in foundation using an independently filtered environment, strict cwd
containment, `shell=False`, timeout enforcement, a new process group/session,
and best-effort cleanup. It still cannot enforce filesystem, user, CPU/memory,
or network isolation without platform facilities.

### Evidence ledger

Each terminal job writes task, intent, context, snapshot, operations, changed
files, diff, validation, process logs, environment, and final-report evidence.
The original 12 files and their field shapes remain compatibility contracts.
`manifest.sha256.json` covers those files plus the additive
`evidence_events.jsonl` and `attestation.json`; the manifest never covers
itself. Pre-v2 bundles containing only the 12 compatibility files remain
verifiable.

The JSONL chain is byte-appended rather than rewritten. Every event records a
monotonic sequence, UTC timestamp, job/project identity, component actor,
canonical payload, payload hash, previous event hash, and event hash. Canonical
JSON uses UTF-8, sorted keys, compact separators, finite numbers, and SHA-256.
Event payloads reject absolute host paths; compatibility documents may still
contain operational paths where the older schema requires them.

The final `evidence_finalized` event is referenced by `attestation.json`, along
with gateway/source/sandbox/validation metadata. To avoid a circular digest,
the attestation's `manifest_checksum` hashes the sorted digest map of the 12
compatibility files. The final checksum manifest then covers all 14 evidence
files, including the chain and attestation.

When project intelligence is available, the context pack, validation result,
environment record, phase events, and attestation carry its schema version and
semantic cache hash (plus the source fingerprint where relevant). These fields
are additive and do not change the 12-file compatibility bundle or chain
verification rules.

The local-development signer is explicitly unsigned (`signature_algorithm:
none`). The chain detects ordinary deletion, insertion, reordering, and
payload mutation, including cases where only the outer checksum is refreshed.
It is not an immutable audit log and cannot prove authorship or resist an
attacker who rewrites the complete chain, attestation, and checksum manifest.
Mandatory validation must pass before a job can report success.
New attestations identify the additive `upg.evidence/v1` contract; verifiers
continue accepting evidence-schema-v2 attestations created before this field
was introduced.

### Constrained Git publication

R3 publication is separate from ordinary editing and requires both manifest
permission and explicit method input. It creates a non-default branch named
`agent/<job-id>-<slug>`, stages only intended paths, and creates a local commit.
Direct default-branch commits, merge, force-push, global configuration changes,
and implicit deployment are outside the authority model.

## End-to-end sequence

1. Validate and register a project manifest.
2. Generate or reuse verified bounded project intelligence, then compile intent
   and policy; atomically create or replay a queued job by its
   optional prepare idempotency key.
3. A local worker claims the job, enters `preparing`, and the Control Plane
   builds bounded context while the Runner copies the registered source into a
   fresh workspace. The stable compatibility state becomes `prepared`.
4. The Control Plane authorizes each operation; the Runner inspects or modifies
   only approved workspace-relative text paths.
5. The worker claims the prepared job, enters `validating`, prepares a sandbox
   handle, heartbeats between named actions, and checks cooperative cancellation
   before backend execution and at every action boundary.
6. The Runner compares the workspace with its baseline and creates
   `patch.diff`.
7. The Control Plane commits a terminal state. The Runner appends terminal and
   evidence-finalized events, emits unsigned attestation metadata, then writes
   checksums covering all compatibility and chain files. Repeated validation
   with the same key returns the recorded result.
8. Optionally claim the separately gated `publishing` phase. Repeated publish
   with the same key returns the original result without a second commit.

The demo repeats this flow with a new job ID. It never resets another job's
workspace or evidence.

## Persistent and generated data

Durable repository contracts live in `docs/`, `state/`, `registry/`, and each
fixture manifest. Mutable runtime data lives under ignored directories:

```text
var/                         SQLite and mutable runtime registry
var/project_intelligence/    verified advisory project metadata caches
workspaces/jobs/<job-id>/    isolated working copies
artifacts/jobs/<job-id>/     evidence bundles
```

No database or generated artifact is a source-of-truth replacement for the
registered project's manifest.

## Extension rules

New stacks add a reviewed adapter declaration and implementation to the
built-in registry and receive only named, manifest-declared actions. Dynamic
plugin discovery and domain-specific adapters are not implemented in this
checkpoint. New execution backends implement the Runner
responsibilities without moving policy or project discovery into the execution
plane. New protocols call the compatibility facade or Control Plane; they do
not add filesystem or process escape hatches. New business domains are managed
projects with their own manifests and memory, never conditionals in Gateway
core.
