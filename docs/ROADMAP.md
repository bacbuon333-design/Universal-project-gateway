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

## Completed checkpoint: sandbox backend foundation

`UPG-SBX-001` removes process-launch ownership from runtime adapters and adds a
bounded execution backend seam without claiming OS isolation:

- `SandboxBackend` and typed handle/request/result contracts cover workspace
  preparation, fixed-action execution, collection, cleanup, timeout, and
  pre-execution cancellation;
- `UnsafeLocalSandboxBackend` is the explicitly unsafe compatibility default;
- opt-in `LocalProcessSandboxBackend` adds independent environment filtering,
  canonical cwd containment, `shell=False`, timeouts, process groups/sessions,
  and best-effort cleanup;
- validation and checksum evidence include additive sandbox safety metadata;
- CLI, MCP, demo, registry, self-registration, lease, evidence, and Git behavior
  remain synchronous and backward compatible.

This checkpoint does not provide kernel filesystem/user/resource isolation or
enforce network denial. Exit evidence requires focused sandbox/security tests,
the full regression suite, two demos, manifest verification, and an
independently verified evidence bundle.

## Completed checkpoint: append-only evidence hash chain

`UPG-EVD-002` adds evidence schema v2 while preserving every v1 compatibility
file and legacy checksum verification:

- canonical UTF-8 JSONL events link sequence, payload hash, previous hash, and
  event hash across preparation, mutation, sandbox validation, patch, terminal,
  and finalization phases;
- unsigned `attestation.json` binds the final event to gateway, job, project,
  source, sandbox, validation, and compatibility-manifest metadata;
- both library and standalone verifiers reject missing, reordered, malformed,
  or tampered events and final-attestation mismatches;
- the checksum manifest covers all 14 evidence files while old 12-file bundles
  remain accepted as checksum-only evidence.

This checkpoint does not add trusted signing, immutable storage, remote
attestation, or a trusted timestamp. Exit evidence requires tamper/reorder
tests, the complete regression/security suite, two demos, self-management
validation, and independent chain verification.

## Completed checkpoint: versioned adapter contract registry

`UPG-CONTRACT-002` adds capability-based runtime discovery while preserving
existing manifest, CLI, MCP, sandbox, and evidence consumers:

- constants and descriptive schemas identify `upg.manifest/v1`,
  `upg.adapter/v1`, `upg.execution/v1`, and `upg.evidence/v1`;
- `AdapterRegistry` registers reviewed Python and Node declarations and
  resolves each named validation action by project type, platform, capability,
  and optional explicit adapter selection;
- legacy schema-`1.0` manifests remain valid, while optional requirements can
  enforce adapter contract, exact version, and capabilities at registration;
- validation and evidence add adapter metadata without removing sandbox or
  evidence-chain fields;
- read-only CLI and MCP discovery lists declarations without probing tools or
  executing runtime actions.

This checkpoint does not implement dynamic plugin loading or any video, Revit,
trading, Auto Call, or other domain adapter. Exit evidence requires registry
compatibility/refusal tests, both fixture flows, self-management validation,
the complete regression/security suite, and independent evidence-chain
verification.

## Completed checkpoint: deterministic project intelligence cache

`UPG-INTEL-001` adds bounded reusable structural metadata without adding an AI
or execution authority:

- `upg.project_intelligence/v1` describes project identity, relative paths,
  entrypoints, allowlisted commands, adapter capabilities, dependency hints,
  and compact module/test/docs summaries;
- sorted, limit-aware Python/Node/generic scanning fingerprints safe files but
  skips protected, sensitive, excluded, and linked paths before content access;
- semantic cache and source hashes use canonical relative JSON and exclude host
  paths; Gateway stores verified documents only in ignored runtime state;
- context packs consume a compact cache subset instead of repeating a full
  tree scan, while explicit CLI generation controls refresh;
- read-only CLI/MCP retrieval does not rescan or execute project code;
- validation evidence and the existing event chain retain sandbox/adapter
  metadata and add the intelligence schema/cache hash without breaking the
  compatibility files.

This checkpoint does not add LLM summaries, repository ingestion, vector or
embedding stores, dynamic adapters, dependency installation, remote workers,
public endpoints, OS sandboxing, or a dashboard. Exit evidence requires UPG,
Python, and Node cache tests; fingerprint refresh and protected-path refusal;
CLI/MCP/context/evidence coverage; full verification; and an independently
verified self-management bundle.

## Next: local hardening

1. Add property and fuzz tests for Windows path normalization, reparse points,
   size limits, registry corruption, and manifest argv validation.
2. Add an operator-reviewed reconciliation workflow for jobs in
   `recovery_required`, including workspace/source diagnostics.
3. Implement and separately threat-model an OS/container backend with bounded
   CPU, memory, filesystem, process, user, and network capabilities.
4. Define evidence retention, encryption-at-rest options, audit export, and
   external-key signed attestations with rotation, revocation, and trusted-time
   semantics; do not store signing keys in the repository or evidence bundle.
5. Version the remaining service/MCP request and response envelopes and add
   cross-version compatibility tests beyond adapter discovery.
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
