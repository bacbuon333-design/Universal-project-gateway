# Roadmap

UPG develops by increasing assurance before increasing authority. Domain
features remain in managed projects rather than Gateway core.

## MVP checkpoint: local vertical slice

- Validated project manifests and persistent local registry
- Deterministic intent and structured policy decisions
- SQLite jobs/events and constrained state transitions
- Bounded context packs with omissions recorded
- Per-job copied workspaces and scoped UTF-8 text operations
- Allowlisted Python and Node validation adapters
- Deterministic patch and checksummed evidence ledger
- Optional constrained local branch/commit path
- CLI and local stdio MCP surfaces
- Windows batch verification and two unrelated fixtures

Exit evidence for this checkpoint is the observed test report, two successful
demo job IDs, verified bundles, a clean `git diff --check`, and an accurate
`state/CURRENT_STATE.json`. Documentation alone is not completion.

## Completed checkpoint: Control Plane and LocalRunner boundary

`UPG-ARCH-002` separates high-level authorization and orchestration from local
execution while preserving the v0.1 interfaces and evidence schema:

- `ControlPlane` owns registry, manifest, intent, policy, jobs, context, and
  high-level API behavior.
- `Runner` defines workspace, scoped file, validation, patch, and evidence
  responsibilities without exposing arbitrary execution.
- `LocalRunner` preserves the synchronous in-process implementation.
- `GatewayService` remains the compatibility facade for CLI, MCP, demo, and
  Python callers.

This checkpoint creates an implementation seam; it does not claim process or
kernel isolation. Exit evidence requires focused delegation tests, the entire
pre-existing suite, self-registration coverage, two demos, and independently
verified checksum evidence.

## Completed checkpoint: durable local job ownership and recovery

`UPG-JOB-002` adds SQLite-backed concurrency and replay foundations without
changing the synchronous local runner deployment:

- schema-v2 jobs persist worker, lease, heartbeat, attempt, idempotency,
  cancellation, recovery, and last-error metadata;
- effectful phases require an unexpired, unpredictable worker lease;
- heartbeat refreshes and cancellation requests are append-style job events;
- expired claim-only work safely returns to its origin, while interrupted
  effectful work enters `recovery_required`;
- prepare, validation, and publication keys prevent duplicate job/workspace,
  process, and Git-commit effects;
- existing CLI, MCP, fixture, self-registration, evidence, and Git paths remain
  local and synchronous.

This checkpoint does not add a remote worker, distributed queue, process-tree
termination, or OS sandbox. Exit evidence requires lease/recovery tests,
idempotent publication proving one commit, the full regression/security suite,
two demos, and an independently verified evidence bundle.

## Next: local hardening

1. Add property and fuzz tests for Windows path normalization, reparse points,
   size limits, registry corruption, and manifest argv validation.
2. Add an operator-reviewed reconciliation workflow for jobs in
   `recovery_required`, including workspace/source diagnostics.
3. Move validation into a separately reviewed OS-level sandbox with no ambient
   credential access and bounded CPU, memory, filesystem, process, and network.
4. Define evidence retention, encryption-at-rest options, audit export, and
   signed attestations.
5. Version the service and MCP schemas and add compatibility tests.
6. Add human review UX for patch, validation, and R3 approval.

## Later: separately secured remote MCP

Only after local hardening and a new threat model:

- deploy a private HTTPS endpoint with managed identity;
- authenticate users and MCP clients with short-lived credentials;
- authorize each user/project/action and isolate tenants;
- add request replay protection, rate/size limits, and immutable audit events;
- store secrets outside manifests and task/evidence content;
- sandbox every project operation and restrict egress;
- require explicit, reviewable approvals for R3;
- test a ChatGPT Web connector against that endpoint in a non-production
  environment.

The smallest safe remote step is not a public tunnel. It is a design and test
of authenticated, per-project authorization in front of an already sandboxed
runner.

## Explicitly out of scope

- arbitrary shell or Python execution;
- direct source editing as a normal operation;
- automatic merge, force-push, or production deployment;
- credential storage or model API calls;
- cloud queues before local durability is proven;
- remote desktop control;
- live financial actions;
- Revit, Blender, Animation, Auto Call, video rendering, or other domain logic;
- autonomous self-modification.

If a future use case needs one of these capabilities, it requires a separate
system boundary and design decision rather than an undocumented Gateway tool.
