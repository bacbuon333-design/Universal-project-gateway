# ADR-007: Deterministic project intelligence cache

- Status: accepted
- Date: 2026-07-14
- Checkpoint: UPG-INTEL-001

## Context

Each task context previously rebuilt a bounded repository tree directly from
the registered source. Manifests provided authoritative paths and commands but
did not expose a reusable structural synopsis for clients or evidence. Repeated
full-context scans are wasteful, while model-generated summaries, whole-repo
ingestion, and dynamic code inspection would add nondeterminism, data exposure,
network, and execution boundaries that this local checkpoint must not grant.

## Decision

UPG defines `upg.project_intelligence/v1` and a Gateway-owned JSON cache per
registered project. A deterministic scanner combines the validated manifest,
reviewed built-in adapter declarations, and a sorted bounded file fingerprint.
The document records project identity/type, relative manifest/source roots,
important and protected paths, entrypoints, test/build/validation argv,
adapters/capabilities, dependency filenames, module/test/docs summaries, risk
notes, generation time, source fingerprint, and semantic cache hash.

The scanner follows these trust rules:

1. Never import or execute project code and never invoke an adapter.
2. Skip manifest-protected, common sensitive, generated, dependency, VCS, and
   runtime paths before file content is opened.
3. Refuse symlinks and Windows reparse points.
4. Enforce file-count, per-file, and total hash-byte limits.
5. Store no file content and use only project-relative paths in hash material.
6. Treat dependency metadata as filename/manifest hints, not installation
   authority.

Canonical UTF-8 JSON with sorted keys and SHA-256 produces the source and cache
hashes. `generated_at` and `cache_hash` are excluded from semantic cache-hash
material, so unchanged semantic content retains the same hash. The document is
stored under ignored Gateway runtime state, verified on read, and never written
into a managed project source.

CLI `intelligence generate` is the explicit refresh operation. CLI
`intelligence list/show` and MCP `gateway_get_project_intelligence` only read
and verify existing cache state. Task preparation generates a missing cache
once, reuses an existing cache without rescanning, and passes a compact subset
to the context compiler. Manifest/policy evaluation remains authoritative.

## Compatibility and evidence

The new contract and service methods are additive. Existing manifest, adapter,
execution, evidence, CLI, and MCP operations retain their shapes. Context,
validation, environment, phase-event, and attestation records add the
intelligence schema/cache hash without adding an evidence file or changing the
12-file compatibility set. Existing evidence-chain verification continues to
apply.

## Security consequences

- A cache can become stale until explicit refresh; it is advisory and cannot
  authorize actions or override the manifest.
- File fingerprinting reads safe file bytes within bounds but retains only
  digests and structural summaries.
- Files larger than limits receive metadata-only fingerprints, so same-size
  content changes beyond the hashing bound may require other source-integrity
  checks.
- Cache state is mutable local state and is not signed or an immutable audit
  record.
- Read-only protocol retrieval does not silently trigger a source rescan.

## Rejected alternatives

- LLM or API summaries: rejected as nondeterministic and an unnecessary data
  egress boundary.
- Vector database or whole-repository ingestion: rejected as excessive state
  and protected-content risk.
- Importing modules or running framework discovery: rejected because metadata
  generation must not execute project code.
- Storing absolute paths in cache hash material: rejected because hashes must
  survive checkout relocation.
- Treating cache data as policy authority: rejected because only the validated
  manifest and current job state grant authority.

## Deferred work

Incremental filesystem watchers, cache retention policy, signed cache
attestations, richer language parsers, semantic indexing, remote cache sharing,
and model-assisted summaries require separate threat models and checkpoints.
