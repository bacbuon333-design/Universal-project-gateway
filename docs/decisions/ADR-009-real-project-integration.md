# ADR-009: Controlled external-project integration proof

- Status: accepted
- Date: 2026-07-14
- Checkpoint: UPG-REAL-001

## Context

UPG's fixture, self-registration, sandbox, evidence, intelligence, operations,
and Git tests established individual boundaries. A remaining proof gap was a
single end-to-end run against a genuine Git repository located outside the UPG
source and runtime trees.

## Decision

Add a dependency-free Python WSGI sample creator and integration validator.
The creator accepts only an absent, non-linked destination disjoint from UPG
and `.git`, writes a fixed reviewed project, initializes clean `main`, and
configures no remote. It never overwrites or cleans an existing project.

The validator uses only existing public Gateway APIs. It registers the exact
external manifest, stores intelligence in Gateway-controlled state, modifies
two declared paths in an isolated workspace, runs fixed manifest actions,
verifies evidence independently, confirms source integrity, and then invokes
the existing explicit R3 publication gate. Publication must create one local
job-scoped branch/commit, preserve the `main` ref, stage only the intended
paths, configure no remote, and replay idempotently. Cleanup remains dry-run.

The automated integration test runs the same sequence in a disposable temp
location; an operator may run it once at a separated Windows path and retain
the project, runtime, workspace, and evidence for inspection.

## Consequences

This closes an integration-proof gap without changing registry, runner,
sandbox, evidence, intelligence, cleanup, or Git-controller authority. The
sample is trusted test code. Validation still runs under the default
`unsafe-local` process backend, evidence remains unsigned, and the result is
not evidence of production isolation, deployment readiness, arbitrary-project
safety, or remote operation.
