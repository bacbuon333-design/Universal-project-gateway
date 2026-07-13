# ADR-005: Append-only evidence hash chain

- Status: accepted
- Date: 2026-07-14
- Checkpoint: UPG-EVD-002

## Context

UPG evidence previously consisted of 12 redacted files covered by
`manifest.sha256.json`. That detects changed files when the manifest is trusted,
but it does not model event order, bind phase payloads together, or provide a
structured final attestation for future signing.

The upgrade must preserve old consumers and verify pre-v2 bundles. It must not
introduce signing keys, a remote signer, immutable storage, or claims that a
locally writable file is a tamper-proof audit service.

## Decision

Keep the original 12 evidence files unchanged and add:

- `evidence_events.jsonl`, written one canonical JSON event per durable append;
- `attestation.json`, an unsigned final metadata document.

Each event has schema/hash algorithm, sequence, type, UTC timestamp, job and
project IDs, component actor, previous hash, canonical redacted payload,
payload hash, and event hash. Event hashes cover every event field except the
event hash itself. The genesis previous hash is 64 zeroes. Absolute host paths
are refused in event payloads; stable relative paths and normalized summaries
are used instead.

Runner and Control Plane boundaries record workspace/job preparation, applied
file mutations, validation start/completion, sandbox collection, patch
generation, terminal job state, and evidence finalization. Sandbox event
payloads include action outcomes and safety flags without host executable or
cwd paths.

The attestation records evidence schema, gateway version, job/project, source
commit when available, sandbox backend and safety level, compact validation
summary, final event hash, generated time, and local-development signer.
`signature_algorithm` is `none`; no signature bytes are fabricated.

## Digest layering

Attestation and checksum manifest cannot directly hash one another without a
circular dependency. Therefore:

1. Compute SHA-256 for the 12 compatibility files.
2. Canonically hash that sorted digest map into attestation
   `manifest_checksum` with scope `compatibility_evidence_file_digests`.
3. Write the attestation.
4. Write `manifest.sha256.json` covering all 14 evidence files.

The standalone verifier independently recomputes both layers plus all event
hashes and continuity. A bundle with neither chain nor attestation is treated
as legacy checksum-only evidence. A bundle containing only one is invalid.

## Consequences

- Ordinary payload mutation, deletion, insertion, and reordering are detected,
  even if an attacker refreshes only the outer checksum for the JSONL file.
- Existing evidence filenames and legacy checksum verification remain valid.
- Publication can append later events; attestation and checksum are derived
  snapshots and may be regenerated, while existing JSONL bytes are not edited.
- Canonical event payloads are checkout-location independent and redacted.
- A writer able to replace the full JSONL, attestation, and manifest can create
  a new internally consistent unsigned bundle. This design does not establish
  authorship, non-repudiation, immutable retention, or trusted time.

## Rejected alternatives

### Put the checksum-manifest file digest inside attestation

Rejected because the manifest must also checksum attestation, producing an
unresolvable circular digest.

### Generate a local self-signed key automatically

Rejected because key generation, protection, rotation, revocation, identity,
and trust distribution require a separate security design. Storing such a key
beside evidence would add little assurance.

### Replace the 12-file bundle

Rejected because CLI, MCP, demos, tests, and external tooling rely on those
files. Schema v2 is additive and legacy-aware.
