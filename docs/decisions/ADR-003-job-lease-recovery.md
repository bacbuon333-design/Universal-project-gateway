# ADR-003: Durable local job leases and recovery

- Status: Accepted
- Date: 2026-07-14
- Checkpoint: UPG-JOB-002

## Context

UPG already persisted jobs and events in SQLite, but the synchronous state
machine had no durable owner. A retry, second process, or crash could repeat
workspace creation, validation, or Git publication without a claim, heartbeat,
or replay record. Cancellation also had no durable request flag.

The current deployment remains a trusted, local, in-process `LocalRunner`.
Remote workers, distributed coordination, and OS sandboxing are separate trust
boundaries and are not implied by this decision.

## Decision

SQLite schema version 2 adds worker ID, unpredictable lease token, expiry,
heartbeat, attempt, prepare idempotency key, cancellation flag, recovery reason,
last error, and claim-origin metadata. Existing schema-v1 databases are rebuilt
transactionally so their jobs and event history remain readable.

The state machine formalizes `claimed`, `preparing`, `validating`, `publishing`,
and `recovery_required`, while retaining `prepared` as the compatibility state
for an isolated workspace awaiting validation or approval.

Claim, heartbeat, and phase transition updates use SQLite `BEGIN IMMEDIATE`
transactions. Only the matching worker and bearer token may advance a leased
phase, and an expired token is rejected. The token is generated with
`secrets.token_urlsafe`, compared without ordinary string equality, and omitted
from public serialization, events, and evidence.

Recovery is phase-sensitive:

| Expired phase | Recovery result | Reason |
| --- | --- | --- |
| `claimed` before a phase starts | Stable claim-origin state | No phase effect was started |
| `preparing`, `running`, `validating`, `publishing` | `recovery_required` | Partial effects cannot be assumed replay-safe |

Prepare keys are unique per project. Validation and publication use a separate
per-job operation ledger with `started`, `completed`, and `failed` results.
Completed duplicates return the recorded result; in-progress or failed
duplicates produce a structured reason.

Cancellation is cooperative. A stable queued/prepared/waiting job can become
`cancelled` immediately. An active worker observes the durable flag between
major phases and validation actions, then records a terminal state and evidence.

## Consequences

- Duplicate local claims and unsafe keyed replays are rejected atomically.
- Stale ownership and recovery intent survive process restart.
- Job events now show claim, heartbeat, cancellation, recovery, and idempotency
  decisions without exposing the lease token.
- A process already running is not forcibly terminated. Cancellation latency is
  bounded by the current adapter action or timeout.
- SQLite remains single-host coordination. The schema is not a distributed
  queue, leader election system, or remote authentication protocol.
- `recovery_required` intentionally needs later operator/reconciliation design;
  this checkpoint does not guess how to roll back a partial external effect.

## Rejected alternatives

- Treating timestamps without ownership as a lease: it cannot reject a second
  worker safely.
- Automatically replaying every expired phase: validation and publication may
  have non-idempotent partial effects.
- Killing process trees as cancellation: this requires a separately reviewed OS
  supervisor/sandbox and platform-specific containment.
- Adding a remote queue now: it would expand authentication, transport, and
  isolation scope before local semantics are proven.
