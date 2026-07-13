# ADR-001: Universal manifest-driven project gateway

- Status: Accepted for MVP
- Date: 2026-07-13
- Decision owners: Universal Project Gateway maintainers

## Context

AI coding clients are useful across unrelated software projects, but direct
terminal and source-tree access combines discovery, interpretation, mutation,
execution, and publication into one broad authority. Project-specific agents
also tend to duplicate safety controls or leak domain assumptions into shared
infrastructure. A local proof is needed that supports more than one stack while
leaving a deterministic, reviewable record.

## Decision

Build a project-agnostic Gateway whose authority is driven by a validated
`PROJECT_MANIFEST.yaml`. Register source projects explicitly. For each task,
compile deterministic intent, make a structured risk decision, persist a job,
copy the source into a per-job workspace, expose only scoped text operations,
run only named allowlisted validation actions, and produce a deterministic diff
and checksummed evidence ledger.

Use one service behind both CLI and local stdio MCP surfaces. Use SQLite for
local job/event durability and standard-library mechanisms where practical.
Treat R3 local branch/commit publication as a separate explicit gate. Prohibit
R4 actions in the MVP.

## Rationale

- A manifest keeps stack and project facts outside Gateway core.
- Explicit registration prevents arbitrary host paths from becoming authority.
- Workspace copies preserve source and make diff/evidence generation clear.
- Named adapter actions avoid turning natural language into shell execution.
- A shared service prevents CLI and MCP policy drift.
- SQLite is sufficient for synchronous local durability without introducing a
  distributed worker or external database.
- Cross-stack fixtures expose accidental Python-only assumptions early.
- Evidence makes validation claims inspectable and tampering detectable.

## Consequences

Positive:

- The default workflow is reversible and source-preserving.
- Project onboarding is data plus a compatible adapter, not domain branching.
- Tests can assert policy, path isolation, validation, and evidence integrity.
- An AI client receives useful high-level operations without unrestricted host
  control.

Costs and limitations:

- Copying large projects is slower than in-place work and requires strict
  exclusions and bounds.
- Application-level containment does not stop malicious validation code from
  using ambient host authority.
- Manifest validation and adapter allowlists require careful maintenance.
- Local checksums are integrity metadata, not confidentiality or identity.
- Remote MCP requires a new deployment and security design.

## Rejected alternatives

### Give the model a terminal in the source repository

Rejected because it permits arbitrary execution and direct mutation, weakens
project/path registration, and makes publication and evidence boundaries
ambiguous.

### Edit registered source directly and rely on Git rollback

Rejected because uncommitted state, ignored files, non-Git projects, and failed
commands can leave destructive side effects. Git history is not a substitute
for an isolated working boundary.

### Implement one agent per business domain

Rejected for the Gateway core because it duplicates common safety machinery
and couples authority to project-specific behavior. Domain instructions belong
in registered project manifests and memory.

### Use containers as the only boundary

Deferred, not rejected as defense in depth. The MVP must run on ordinary
Windows without Docker. A hardened runner should add OS isolation later while
retaining registration, policy, workspace, and evidence contracts.

### Expose a public MCP tunnel from the local machine

Rejected because transport reachability is not authentication, authorization,
tenant isolation, sandboxing, or audit. A remote endpoint is a later system
with separate controls.

## Follow-up criteria

Revisit this decision if the system needs hostile-code execution, distributed
workers, remote multi-user access, large monorepo optimization, or automated
remote publication. Any change must preserve explicit project identity,
least-authority operations, structured policy, source protection, and evidence.
