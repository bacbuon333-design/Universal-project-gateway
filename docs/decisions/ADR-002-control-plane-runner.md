# ADR-002: Separate Control Plane from local execution

- Status: Accepted
- Date: 2026-07-14
- Checkpoint: UPG-ARCH-002

## Context

At v0.1.1, `GatewayService` owned project registration, intent and policy,
durable jobs, workspace files, validation processes, evidence, and Git
publication in one class. The underlying components were already constrained,
but the application layer did not expose a clear seam between deciding what a
job may do and performing approved work.

The next hardening steps need an execution boundary that can later be reviewed
or replaced without moving project lookup, policy, or job authority into a
worker. The change must preserve the existing CLI, MCP, demo, evidence schema,
runtime adapters, and Git behavior.

## Decision

Introduce three explicit application roles:

| Role | Responsibility |
| --- | --- |
| `ControlPlane` | Project and manifest lookup, intent compilation, policy decisions, job state and events, context compilation, orchestration, and R3 publication gating |
| `Runner` | A bounded interface for workspace preparation, scoped file operations, named validation, patch generation, and evidence production |
| `LocalRunner` | The current synchronous implementation using `WorkspaceManager`, `ScopedWorkspace`, runtime adapters, and `EvidenceLedger` |

Keep `GatewayService` as a compatibility facade that delegates every supported
operation to `ControlPlane`. Existing public method names and response shapes
remain unchanged.

The Control Plane injects a `Runner`; it does not construct workspace file
objects or runtime adapters. The Runner receives validated manifests,
persisted jobs, workspace-relative paths, and fixed action names. It does not
own registry resolution, natural-language intent, policy, or the job state
machine, and it never accepts arbitrary argv or shell text.

Git publication remains in the Control Plane because it is a separately gated
R3 decision that mutates the registered source only after successful runner
validation. The Runner supplies the deterministic patch and workspace output
used by that gate.

## Consequences

- CLI, MCP, demo, fixtures, self-registration, evidence, and Git tests continue
  to exercise the same `GatewayService` surface.
- Runner behavior can be tested independently and replaced through dependency
  injection without changing protocol code.
- Policy and project authority remain centralized rather than being copied into
  an execution backend.
- The evidence bundle stays backward compatible; no new schema or signature is
  introduced.
- Some orchestration requires explicit data exchange between the planes,
  including terminal job metadata and ordered events used during evidence
  finalization. This is intentional and visible rather than hidden shared
  authority.

## Security interpretation

This decision does not create a process, privilege, machine, or network trust
boundary. `LocalRunner` executes in the Gateway process with the host user's
permissions. It must continue to be labeled local and application-isolated.

An OS sandbox, signed execution envelope, remote worker, lease/recovery model,
signed evidence chain, adapter plugin contract, and public endpoint all require
separate decisions and are not implied by this ADR.

## Alternatives considered

### Rename `GatewayService` without adding a runner contract

Rejected because it would move code without establishing an injectable,
testable execution seam.

### Put registry, policy, and job transitions inside LocalRunner

Rejected because a future worker would then receive excessive authority and
the Control Plane would no longer be the single authorization point.

### Introduce a remote or sandboxed runner now

Rejected for this checkpoint. Transport authentication, capability envelopes,
resource limits, cancellation, recovery, and sandbox policy need their own
threat model and tests.
