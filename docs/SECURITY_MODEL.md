# Security model

## Status and objective

This MVP demonstrates enforceable application-level boundaries around local
AI-assisted project work. It is **not yet a production security boundary** and
does not replace an operating-system sandbox, container, hardened remote
service, or human review.

The safety objective is narrow: a caller may act only on a registered project,
only within a fresh per-job copy, only through scoped file operations and named
validation actions, with a reviewable patch and evidence trail.

## Local v0.2 readiness boundary

The local audit accepts UPG for controlled Windows operation only when projects
and their validation code are trusted, the operator reviews warnings and
patches, and publication stops at a non-default local branch/commit. A passing
doctor or evidence checksum does not promote the default `unsafe-local`
backend into an OS security boundary. An older reachable Git tag is reported
as a warning rather than an exact checkpoint; tag presence has no effect on
runtime authority.

The accepted local flow and release checklist are recorded in
[`LOCAL_V02_READINESS.md`](LOCAL_V02_READINESS.md). Remote/public use remains
refused until kernel isolation, authenticated authorization, tenant isolation,
encrypted and signed evidence, supervised recovery, and a separate production
threat model exist.

## Trust boundaries

- **Untrusted request:** natural language, target paths, MCP arguments, and
  publication preferences are data, never code.
- **Validated project contract:** the manifest is trusted only after schema,
  path, secret-pattern, command, and policy validation.
- **Registered source:** source is read-only input to normal job execution. An
  arbitrary local path is not accepted as a project.
- **Job workspace:** mutation authority is limited to one canonical workspace
  root. A workspace is not allowed to confer access back to its source.
- **Worker lease:** an unpredictable token grants temporary ownership of one
  local job phase. It is stored only in SQLite and typed in-process state, and
  is omitted from protocol responses, events, logs, and evidence.
- **Sandbox backend:** an adapter submits only a fixed action and reviewed argv
  to a prepared workspace handle. The backend owns child-process creation,
  timeout, capture, cleanup, and its accurately bounded safety metadata.
- **Child process:** receives an explicit environment, `shell=False`, a bounded
  timeout, and a contained workspace working directory. Local backends still
  run it under the current host identity.
- **Evidence:** compatibility files are checksum-covered; ordered phase events
  are hash-linked and referenced by an unsigned attestation. Output must still
  be treated as potentially sensitive until redaction and review have succeeded.
- **Publication:** local Git branch creation is a distinct, higher-risk gate.

## Canonical risk model

| Level | Meaning | MVP policy |
| --- | --- | --- |
| R0 | Read-only, scoped inspection | May be allowed by manifest |
| R1 | Create or modify text in an isolated workspace | May be allowed by manifest |
| R2 | Execute a named, allowlisted validation action | May be allowed by manifest |
| R3 | Create a non-default local Git branch and commit | Requires manifest permission and explicit method input |
| R4 | Destructive, deployment, credential, merge, production, or unrestricted execution action | Prohibited |

Policy decisions are structured and include `allowed`, `risk_level`,
`reason_code`, and a human-readable `message`. Refusal is a normal result, not
an exception to conceal.

## Filesystem controls

Every file operation is tied to a job and a workspace-relative path. The
Gateway rejects:

- absolute paths and drive-qualified paths;
- `..` traversal after normalization;
- canonical destinations outside the active workspace;
- symlinks or junctions that resolve outside the workspace, where detectable;
- declared protected paths;
- oversized text reads or writes;
- binary mutation;
- direct source mutation.

Copy and context walks skip `.git`, dependency directories, caches, build
outputs, generated artifacts, and protected paths. Source file hashes and a
source revision are captured at workspace creation. A later mismatch becomes a
stale-source warning rather than being silently overwritten.

Deletion is not implemented as a mutation. A delete request records an
approval event and moves the job to an approval state where appropriate.

## Execution controls

Commands in a manifest are declarations for runtime adapters, not arbitrary
caller commands. Runtime adapters validate executables, modules/scripts,
optional arguments, timeout, and permitted environment keys, then create an
internal `SandboxExecutionRequest`. Only the sandbox package imports process
launch APIs; service, Control Plane, Runner, and runtime adapters expose no raw
command interface.

The development-compatible `UnsafeLocalSandboxBackend` remains the default. It
uses an explicit workspace cwd, exact adapter environment, timeout, captured
output, and `shell=False`, but it is intentionally labeled `unsafe-local`
because it adds no OS isolation and cannot reliably clean descendant trees.

The opt-in `LocalProcessSandboxBackend` adds an independent environment
allowlist, canonical cwd containment, no inherited environment by default, a
new process group/session, timeout enforcement, and best-effort termination.
Its `process-restricted` safety level is still not a kernel security boundary.
The request can record `unrestricted` or `deny_requested` network policy, but
network denial is advisory and recorded as unenforced until a container or
platform sandbox implements it.

Lease ownership prevents two local workers from advancing the same effectful
phase concurrently. It does not constrain the process capabilities of the
lease holder. Heartbeat and cancellation checks occur between named actions;
backends also refuse to start when cancellation is already observable. UPG
does not yet interrupt a process mid-action; timeout cleanup is best effort.

The public service, CLI, and MCP server intentionally do not expose
`run_any_command`, shell evaluation, Python evaluation, machine browsing,
deployment, merge, force-push, or credential access. Dependency installation
is optional and disabled by default in the demo.

Allowlisted project tests are still project code and can be malicious. Both
local backends limit invocation but do not provide kernel-level containment.
Run only trusted local projects until a separately reviewed OS/container
backend is implemented.

## Git controls

- Direct commits to `main`, `master`, or the detected default branch are
  refused.
- Branch names are generated under `agent/` from bounded job data.
- Only intended changed paths may be staged.
- A dirty source is refused unless unrelatedness can be safely established.
- Merge, force-push, global Git configuration changes, and automatic remote
  publication are prohibited.
- Push, if added later, requires a configured remote plus explicit project and
  call permission; credentials remain outside Gateway storage.

## Secrets and evidence

Manifests must not contain credentials. Protected files are excluded from
context and raw evidence. Structured data, event payloads, and process output
pass through secret redaction before persistence. Event payloads also reject
absolute host paths so their hashes do not depend on checkout location.

The evidence chain detects missing, reordered, or changed events by recomputing
canonical payload/event hashes and continuity. The final unsigned attestation
binds the last event, compatibility-manifest digest, source commit when known,
sandbox safety metadata, and validation summary. The outer checksum manifest
covers all evidence files but not itself.

These mechanisms detect accidental or partial tampering; they do not encrypt
data, provide a trusted timestamp, authenticate an author, or stop a writer
from recomputing the entire unsigned bundle. Runtime artifacts remain local and
ignored by Git. A real signing key must later live outside source, manifests,
logs, context, and evidence.

Never put tokens, passwords, private keys, connection strings, or entire
environment dumps in a task request. If protected data is encountered, stop,
record a redacted error, and rotate any credential that may have leaked.

## Remote MCP and ChatGPT Web

Only local stdio transport is in the accepted MVP path. No remote ChatGPT
connectivity has been tested. A future endpoint requires, at minimum, HTTPS,
strong user authentication, per-project authorization, tenant isolation,
anti-replay controls, rate and size limits, auditable approvals, encrypted
storage, network egress policy, sandboxed validation, and a production threat
model. An ad-hoc public tunnel is not an acceptable security design.

## Residual risks

- Application path checks are not equivalent to OS isolation.
- Filesystem race conditions and platform-specific reparse points require
  defense in depth.
- Validation code can access host capabilities permitted to the current user;
  the restricted local backend reduces ambient environment exposure but cannot
  stop filesystem or network access.
- Redaction is pattern-based and cannot guarantee detection of every secret.
- The evidence chain and local attestation are unsigned and stored beside the
  files they describe; a full-bundle rewrite by an authorized filesystem writer
  cannot be distinguished from legitimate generation.
- SQLite is local durability, not a distributed queue or tamper-proof audit log.
- Lease tokens prevent accidental concurrent ownership but are not remote
  authentication credentials and are not suitable for a multi-host queue.
- Cooperative cancellation may be observed only after the current validation
  process returns or times out; process-group cleanup on timeout is best effort
  and an OS sandbox/process supervisor is still required.
- A local Git commit remains unreviewed until a human examines the patch.
