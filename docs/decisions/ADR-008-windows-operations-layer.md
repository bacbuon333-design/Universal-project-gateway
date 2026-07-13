# ADR-008: Windows local operations layer

- Status: accepted
- Date: 2026-07-14
- Checkpoint: UPG-OPS-001

## Context

UPG had verified setup and launch scripts but no single read-only diagnostic,
runtime summary, or policy-aware retention command. Manual cleanup and update
steps were easy to mistype on Windows, while constructing the normal service
for diagnostics could create directories or migrate SQLite.

## Decision

Add a separate local operations module used by `upg doctor`, `upg status`, and
`upg cleanup`. Doctor and status read existing state without initializing it.
SQLite is opened in read-only URI mode; intelligence caches are hash-verified
but never regenerated; MCP startup smoke is limited to importing its factory.

Cleanup defaults to dry-run and considers only immediate safe-named runtime
directories attached to terminal SQLite jobs outside the `keep-last` window.
Before any deletion, canonical paths are checked against every registered
source plus durable Gateway paths. Unknown, active, linked, malformed, or
escaped entries are not candidates.

Add `DOCTOR_GATEWAY.bat` and a `PULL_AND_VERIFY.bat` helper that refuses dirty
or non-`main` checkouts and permits only a fast-forward pull from `origin/main`
before full verification. Existing batch files receive consistent labels and
failure propagation.

## Consequences

Operators gain repeatable local diagnostics, machine-readable status, and a
reviewable retention workflow. Cache age remains advisory rather than a source
freshness claim. The default sandbox remains explicitly unsafe-local, cleanup
cannot terminate live processes, and no service installer, dashboard, remote
worker, public endpoint, or OS isolation is introduced.
