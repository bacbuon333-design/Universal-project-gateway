# ADR-004: Sandbox backend foundation

- Status: accepted
- Date: 2026-07-14
- Checkpoint: UPG-SBX-001

## Context

Runtime adapters previously validated manifest-declared argv and launched child
processes directly. That kept the public surface constrained, but combined
action validation with host-specific process mechanics and left no reviewed
seam for safer Windows or Linux execution.

This checkpoint must preserve local synchronous behavior, evidence shape, CLI,
MCP, demos, leases, self-registration, and Git publication. It must not claim a
security boundary that cannot be delivered without OS/container facilities.

## Decision

Introduce internal `SandboxBackend`, `SandboxHandle`,
`SandboxExecutionRequest`, and `SandboxExecutionResult` contracts. Runtime
adapters remain the sole translators from manifest actions to reviewed argv;
they submit typed requests and no longer import subprocess APIs. `LocalRunner`
owns one prepare/collect/destroy lifecycle per validation phase.

Keep `UnsafeLocalSandboxBackend` as the default. It preserves the former
`subprocess.run` behavior with explicit cwd, environment, timeout, capture, and
`shell=False`. Its backend ID, `unsafe-local` safety level, and limitations are
recorded in every execution result.

Add opt-in `LocalProcessSandboxBackend`. It independently filters the supplied
environment, validates canonical cwd containment, starts without a shell,
creates a process group/session, enforces timeout, and attempts group cleanup.
It records `process-restricted`, not `secure` or `isolated`.

Network policy is a typed request/evidence field. A deny request is explicitly
recorded as unenforced because portable Python process APIs cannot provide a
network boundary. Environment names may be recorded; values are not added to
evidence.

The existing command-result and 12-file evidence bundle shapes remain valid.
Sandbox metadata is additive within validation checks and `environment.json`.

## Consequences

- Process-launch code is localized to sandbox backends and can be replaced
  without changing Control Plane or protocol APIs.
- Default development behavior remains compatible and accurately labeled.
- The restricted backend reduces ambient secret exposure and tightens cwd,
  timeout, and cleanup behavior without external dependencies.
- Cancellation can prevent process start and is checked between phases, but it
  does not interrupt an already running action.
- Neither backend prevents validation code from using the current user's host
  filesystem or network authority. Timeout cleanup of descendants is best
  effort, especially on Windows without Job Objects.

## Rejected alternatives

### Rename the old behavior as a secure sandbox

Rejected because application checks and `shell=False` are not kernel isolation.

### Make an external platform mandatory now

Rejected for this checkpoint because Docker, Hyper-V, Windows Sandbox, Podman,
WSL, admin privileges, remote workers, and automatic dependency installation
are explicitly outside scope.

### Expose a generic sandbox execute API

Rejected because caller-supplied commands would bypass manifest action and
runtime-adapter policy, creating prohibited unrestricted execution authority.
