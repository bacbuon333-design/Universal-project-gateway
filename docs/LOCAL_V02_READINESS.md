# Local v0.2 readiness audit

## Verdict

Universal Project Gateway is **ready for controlled local Windows use with
trusted projects** at the `v0.2.0-local` capability boundary. It is not a
production security boundary and is not ready for remote, public, multi-user,
or untrusted-project operation.

Release bookkeeping is conditional. The audited `main` commit is `9d1414e`
(`Add real project integration test`), one commit after `v0.1.8`, but the
expected `v0.1.9` tag is not present locally or on `origin` after fetching
tags. This audit does not create or move tags. Before tagging
`v0.2.0-local`, a maintainer must either tag `9d1414e` as `v0.1.9` or record an
explicit decision that the intermediate tag was skipped.

## Audit scope and evidence

The audit reviewed the manifest and registry contracts, Control Plane/Runner
boundary, scoped filesystem and workspace copying, SQLite job ownership,
sandbox backends, evidence chain and verifier, adapter registry, intelligence
cache, external-project harness, CLI/MCP surfaces, Git controller, Windows
scripts, tests, and operator documentation.

The following were exercised on Windows from an isolated audit worktree:

- complete `VERIFY_GATEWAY.bat` verification, including Ruff, compileall,
  three manifest checks, unit/integration and security suites, two demos,
  evidence verification, and `git diff --check`;
- `DOCTOR_GATEWAY.bat` with zero failing checks;
- human and JSON status reports plus conservative cleanup dry-run;
- UPG intelligence generation and read-only retrieval from Gateway-owned
  cache state;
- read-only adapter capability listing;
- latest 14-file evidence checksum, event-chain, payload, and attestation
  verification;
- MCP stdio startup followed by a clean exit on end-of-input.

The audit found and fixed three bounded operator-readiness issues:

1. An untagged HEAD was previously reported as a passing checkpoint merely
   because an older tag was reachable. Doctor now warns and status identifies
   the nearest tag plus commit distance.
2. `VERIFY_GATEWAY.bat` reused an existing virtual environment without first
   enforcing Python 3.11 or newer. It now fails before installation or tests
   when the selected interpreter is too old.
3. `PULL_AND_VERIFY.bat` could not distinguish a failed Git status/branch
   query from an empty result, and its branch variable was not explicitly
   cleared. It now fails closed in both cases.

No architecture, authority, endpoint, runtime action vocabulary, or evidence
contract was expanded.

## What is ready

| Area | Local readiness |
| --- | --- |
| Architecture | `GatewayService` remains a compatibility facade over a distinct `ControlPlane` and bounded `LocalRunner`. |
| Project trust | Only validated, registered manifests resolve; arbitrary source paths remain untrusted. |
| Filesystem | Work occurs in per-job copies with canonical containment, protected-path checks, and link/reparse refusal where detectable. |
| Jobs | SQLite schema v2 provides leases, heartbeat events, phase-sensitive recovery, cooperative cancellation, and idempotent prepare/validate/publish foundations. |
| Execution | Named manifest actions resolve through reviewed Python/Node adapters and always use `shell=False` through an explicit sandbox backend. |
| Evidence | Compatibility files, SHA-256 coverage, canonical event-chain continuity, payload hashes, and unsigned attestation binding verify locally. |
| Intelligence | Bounded, deterministic, protected-path-aware metadata is cached under Gateway-controlled runtime state and is advisory only. |
| External project | The controlled Python fixture proves registration, isolated mutation, validation, evidence, and one idempotent local review-branch commit outside UPG. |
| Operations | Doctor, status, cleanup dry-run, full verification, clean-main pull helper, and stdio MCP startup are usable on Windows. |
| Git safety | Normal publication never commits to the detected default branch, stages only intended paths, and does not push or merge. |

## What is explicitly not ready

- Validation of untrusted or malicious projects. The default
  `unsafe-local-subprocess` backend runs with the operator's host identity.
- Kernel-enforced filesystem, user, process, resource, or network isolation.
- Reliable mid-process cancellation or guaranteed descendant process cleanup.
- Remote workers, distributed queues, multi-host leases, or tenant isolation.
- Public HTTPS/MCP exposure, ChatGPT Web connectivity, authentication,
  per-user authorization, anti-replay controls, or rate limits.
- Cryptographic signing, trusted timestamps, immutable evidence storage, or
  independently protected signing keys.
- Dynamic plugins or domain adapters for Auto Call, video, Animation,
  VietSub, Revit, trading, or production systems.
- Automatic dependency installation, unrestricted execution, automatic push,
  merge, deployment, or rollback.

## Safe local usage flow

1. Use a clean checkout and run `PULL_AND_VERIFY.bat` only while on `main`, or
   fetch and create a non-default task branch/worktree manually.
2. Run `DOCTOR_GATEWAY.bat`. Stop on every `FAIL`; review every `WARN`,
   especially an untagged HEAD, stale intelligence, or missing evidence.
3. Run `VERIFY_GATEWAY.bat` and retain its exact test/evidence output.
4. Register only a trusted project's validated `PROJECT_MANIFEST.yaml`. Keep
   its source outside Gateway workspaces, artifacts, and `.git` internals.
5. Generate project intelligence explicitly and inspect its relative paths,
   omissions, adapter requirements, and cache location.
6. Prepare a task with explicit relative targets and a bounded idempotency
   key. Confirm the workspace is under `workspaces/jobs/<job-id>/workspace`.
7. Modify only through scoped workspace methods. Review `patch.diff` before
   running manifest-declared validation.
8. Verify validation argv, sandbox safety metadata, evidence checksums, event
   continuity, and unsigned attestation. Do not interpret checksum integrity
   as confidentiality or authorship.
9. If publication is authorized, create only the generated non-default local
   branch/commit and review it manually. Do not push or merge automatically.
10. Preview cleanup with `upg cleanup --dry-run`; use `--execute` only after
    reviewing every candidate and closing related processes.

## Operator checklist before `v0.2.0-local`

- [ ] Resolve or explicitly waive the missing `v0.1.9` tag on `9d1414e`.
- [ ] Confirm the release commit is on a non-default review branch and the
      working tree is clean.
- [ ] Run `VERIFY_GATEWAY.bat` with zero failures.
- [ ] Refresh UPG intelligence, then run `DOCTOR_GATEWAY.bat` with zero
      `FAIL` checks and review all `WARN` checks.
- [ ] Inspect `upg status --json` for registry, database, jobs, adapters,
      default `unsafe-local` sandbox, evidence schema, and exact/nearest tag.
- [ ] Run `upg cleanup --dry-run` and confirm no registered source appears in
      candidates or deleted results.
- [ ] Verify the latest evidence bundle independently and record its path.
- [ ] Start MCP stdio with closed input and require a clean exit; do not bind a
      public transport.
- [ ] Review the release diff and confirm no credential, runtime artifact,
      workspace, evidence bundle, or external test project is staged.
- [ ] Tag only after review; do not merge, push, deploy, or publish from an
      automated UPG job.

## Known limitations and residual risk

Windows symlink escape coverage may skip when the process lacks symlink
privilege. Runtime checks still reject detectable symlinks and reparse points,
but this is not a substitute for an OS sandbox or privileged platform test.
Path and deletion checks reduce application-level risk but remain exposed to
host filesystem races. Cancellation is phase-cooperative. SQLite and local
evidence are writable by the same host user. Intelligence freshness is based
on cache age and an explicit refresh, not continuous source monitoring.

The controlled external fixture is dependency-free and trusted. Its passing
result demonstrates workflow correctness, not safety against arbitrary
project code.

## Required milestones before remote or public use

1. Implement and threat-model an OS/container backend with enforceable
   filesystem, identity, process, resource, and network boundaries.
2. Add authenticated per-user/per-project authorization, tenant isolation,
   anti-replay controls, request limits, encrypted storage, and an explicit
   remote-worker trust model.
3. Protect signing keys outside UPG and add signed, immutable, externally
   timestamped evidence with rotation and revocation.
4. Add operator-reviewed recovery/reconciliation for partially effectful jobs
   and supervised process termination.
5. Complete Windows path/reparse fuzzing under a host able to create links,
   plus adversarial untrusted-project testing inside the future OS sandbox.
6. Version and compatibility-test the remaining service and MCP envelopes,
   then perform a separate remote/public security review.

## Recommended first real project onboarding

Start with a trusted, dependency-light Python or Node repository that has no
production credentials and can validate offline. Give it a manifest with the
smallest source/docs/test paths, explicit protected paths, named lint/test
actions, exact built-in adapter requirements, and local-branch-only
publication. Register it, generate and inspect intelligence, prepare a
read-only task first, then perform one tiny two-file behavior change in an
isolated workspace. Require validation and evidence verification before an
explicit local review-branch commit. Do not configure UPG to push, merge,
deploy, install dependencies, or operate on a production checkout.
