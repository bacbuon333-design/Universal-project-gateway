# Security model

## Status and objective

This MVP demonstrates enforceable application-level boundaries around local
AI-assisted project work. It is **not yet a production security boundary** and
does not replace an operating-system sandbox, container, hardened remote
service, or human review.

The safety objective is narrow: a caller may act only on a registered project,
only within a fresh per-job copy, only through scoped file operations and named
validation actions, with a reviewable patch and evidence trail.

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
- **Child process:** an adapter receives a fixed action and reviewed argv, a
  bounded environment, a timeout, and the workspace as its working directory.
- **Evidence:** output is integrity-checked but must still be treated as
  potentially sensitive until redaction and human review have succeeded.
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
caller commands. Execution uses argv arrays and `shell=False`. The working
directory is the active workspace. Executables, modules/scripts, optional
arguments, timeout, and permitted environment keys are bounded by adapter and
manifest policy.

Lease ownership prevents two local workers from advancing the same effectful
phase concurrently. It does not constrain the process capabilities of the
lease holder. Heartbeat and cancellation checks occur between named actions;
UPG does not yet kill an adapter subprocess or its descendants mid-action.

The public service, CLI, and MCP server intentionally do not expose
`run_any_command`, shell evaluation, Python evaluation, machine browsing,
deployment, merge, force-push, or credential access. Dependency installation
is optional and disabled by default in the demo.

Allowlisted project tests are still project code and can be malicious. This
MVP limits invocation but does not provide kernel-level containment. Run only
trusted local fixtures or add a separately reviewed OS sandbox before handling
hostile repositories.

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
context and raw evidence. Structured data and process output pass through
secret redaction before persistence. Evidence checksums detect modification;
they do not encrypt data or authenticate an author. Runtime artifacts are local
and ignored by Git.

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
- Trusted validation code can access capabilities of the host process.
- Redaction is pattern-based and cannot guarantee detection of every secret.
- SQLite is local durability, not a distributed queue or tamper-proof audit log.
- Lease tokens prevent accidental concurrent ownership but are not remote
  authentication credentials and are not suitable for a multi-host queue.
- Cooperative cancellation may be observed only after the current validation
  process returns or times out; an OS sandbox/process supervisor is still required.
- A local Git commit remains unreviewed until a human examines the patch.
