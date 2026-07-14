# Universal Project Gateway v0.2.0-local release candidate

Package version: `0.2.0+local`

Reserved Git tag name: `v0.2.0-local`

Release class: controlled local Windows release candidate

This release candidate closes the verified local-core stage of Universal
Project Gateway. This task does not create, move, or delete a Git tag, publish
a package, merge a branch, push a commit, deploy a service, or expand runtime
authority.

## Release history

- `v0.1.9` resolves to
  `9d1414ef3056888ff5c651466ea688f53317fb65`, the commit named
  `Add real project integration test` and the intended `UPG-REAL-001`
  checkpoint.
- During candidate preparation, `v0.2.0-local` appeared both locally and on
  `origin` as a lightweight tag targeting the earlier audit commit
  `dc4e01b2bc1f2595f2fbb3628b1f7ef024bf1557`. It did not exist at the first
  release gate in this task and was not created by this task.
- That pre-existing target cannot identify the later release-candidate commit.
  This task leaves it untouched; a maintainer must reconcile release
  bookkeeping separately after reviewing and merging the candidate.
- This candidate neither creates nor changes either tag.

## What is ready

- Validated project manifests and a persistent, path-bound project registry.
- UPG self-registration and isolated self-management validation.
- A Control Plane/Runner responsibility boundary with durable SQLite jobs,
  local leases, heartbeat, recovery foundations, cancellation, and
  idempotency.
- Canonically contained per-job workspaces and bounded UTF-8 file operations.
- Reviewed Python and Node adapter capabilities and named validation actions.
- Explicit local sandbox backend metadata, timeouts, filtered environments,
  and `shell=False` process invocation.
- Checksum-covered evidence, a deterministic event hash chain, and structured
  unsigned attestation metadata.
- Deterministic project-intelligence caches stored under Gateway-controlled
  runtime state.
- Windows doctor, status, conservative cleanup, verification, and pull helper
  workflows.
- A controlled external-project proof covering registration, intelligence,
  workspace mutation, validation, evidence, and idempotent local branch
  publication.

## Trusted local Windows boundary

This candidate is ready only for **trusted local projects** on a Windows host
where the operator reviews warnings, patches, validation output, evidence, and
local publication. Normal edits occur in copied UPG job workspaces; registered
source roots are read-only inputs until an explicitly authorized local branch
publication step.

Deep agent permissions are not part of this release. A workspace directory is
an application-level containment boundary, not a host security boundary.
Future arbitrary commands or production tools must run inside a separately
threat-modeled Agent VM or equivalent hard sandbox rather than under the host
identity.

## What is not ready

- There is **no public or remote MCP endpoint** and no tested ChatGPT Web
  connection, remote authentication, multi-user authorization, or tenant
  isolation.
- This release is **not approved for untrusted project execution**. Allowlisted
  project tests still execute with the local user's host capabilities.
- There is no OS-level filesystem/user/network/resource isolation.
- There is no unrestricted terminal, arbitrary command tool, remote worker,
  distributed queue, dashboard, secret broker, automatic dependency install,
  automatic push/merge, or deployment path.
- Evidence is unsigned and local; it does not establish authorship,
  non-repudiation, immutable storage, or a trusted timestamp.
- No Voip24h Auto, media, animation, Revit, trading, Auto Call, or other
  production/domain integration is included.

## Sandbox status

`UnsafeLocalSandboxBackend` remains the compatibility default and accurately
reports safety level `unsafe-local`. `LocalProcessSandboxBackend` adds cwd
containment, independent environment filtering, timeouts, process-group
foundations, and best-effort cleanup, but remains `process-restricted` rather
than an OS security boundary. Network-deny requests are evidence metadata only
and are not enforced by either local backend.

## Evidence status

Current evidence schema `2.0` preserves the original 12 compatibility files
and adds `evidence_events.jsonl` plus `attestation.json`. The SHA-256 manifest,
event sequence, previous-event hashes, payload hashes, final-event binding,
and unsigned attestation can be verified independently. A writer with access
to the whole bundle can still recompute an internally consistent unsigned
bundle.

## Project intelligence status

`upg.project_intelligence/v1` provides deterministic, bounded, relative-path
metadata for registered Python, Node, and generic projects. Protected,
sensitive, excluded, linked, and over-limit content is omitted. Cache freshness
is operator-controlled and advisory; it is not continuous source monitoring or
semantic code understanding.

## External-project integration status

The controlled external Python WSGI fixture proves that UPG can manage a
separate local Git project outside UPG source/workspace/artifact roots. Source
remains unchanged before publication, `main` remains unchanged afterward, one
review branch contains only intended files, replay creates no duplicate
commit, and no remote or push is configured. This trusted fixture is not proof
that arbitrary third-party project code is safe under a local backend.

## Verification gate

The release candidate is acceptable only when all of the following pass on
the release branch and again after human merge before treating any tag as the
release identifier:

- `cmd /c VERIFY_GATEWAY.bat`;
- `cmd /c DOCTOR_GATEWAY.bat` with zero `FAIL` checks;
- `upg status` and `upg cleanup --dry-run`;
- refreshed and verified UPG project intelligence;
- local MCP stdio startup followed by clean EOF shutdown;
- a UPG self-management job running both mandatory manifest actions;
- independent verification of the resulting evidence checksum and hash chain;
- clean `git diff --check` and working tree.

## Recommended next phases

1. Reconcile the pre-existing `v0.2.0-local` tag through a separately
   authorized post-merge release procedure; do not treat its audit-commit
   target as this release candidate.
2. Onboard `Z:\Voip24h Auto` in read-only mode without modifying its source.
3. Build a long-lived local MCP runtime for Codex and other local clients.
4. Add session authentication, permission profiles, tool scopes, replay
   protection, and durable audit records before any remote exposure.
5. Expose only scoped workspace tools, keeping arbitrary terminal access
   unavailable on local backends.
6. Design and adversarially test an Agent VM/hard sandbox before raw tools,
   scoped secrets, untrusted project execution, or media production jobs.

The long-term direction is a self-owned AI Dev/Media Operating Layer where
models gain deep operational power only inside UPG-controlled workspaces and,
for high-power operations, hardened disposable Agent VM environments. The
trusted host and registered source roots remain outside that authority.
