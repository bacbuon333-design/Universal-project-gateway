# V3.13.1 — CHECKPOINT HASH CANONICALIZATION REPAIR

## Purpose

Repair one provenance-only defect discovered after V3.13 genesis checkpoint publication: the checkpoint SHA published by the Windows executor was calculated over local worktree bytes before Git line-ending normalization. The committed GitHub checkpoint bytes are LF-normalized and therefore have a different SHA-256.

This is an operational provenance repair only.

NO market research.
NO outcome metrics.
NO strategy execution.
NO H227.
NO H226 descendant.

## Scientific parent

V3.13 final report commit:

`e2c4d64d93545be12ddf6d40ad8fc4dc5644bd7c`

## Frozen genesis checkpoint

Path:

`AlphaLab_Antigravity/reports/v3_13/checkpoints/000001_20260816T111146Z.json`

Historical report-published local-worktree SHA-256:

`f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b`

Authoritative SHA-256 of committed repository bytes, independently recomputed from the GitHub blob:

`b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876`

The checkpoint payload itself is scientifically unchanged. Only hash representation/provenance was wrong.

## Root cause

V3.13 used Python text-mode `Path.write_text()` and then hashed the local file. On Windows, text-mode newline translation may serialize `\n` as CRLF. Git may subsequently normalize text files to LF when creating the repository blob. Therefore:

local-worktree byte SHA != committed-repository byte SHA.

A hash chain must not depend on operating-system line-ending behavior.

## Frozen repair contract

V3.13.1 introduces checkpoint hash scheme:

`SHA256_UTF8_LF_NORMALIZED_V1`

Definition:

1. read checkpoint file bytes;
2. reject invalid UTF-8;
3. normalize CRLF to LF;
4. reject remaining bare CR characters;
5. hash exact UTF-8 LF-normalized bytes with SHA-256.

Under this scheme the existing genesis checkpoint authoritative chain hash MUST equal:

`b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876`

The historical `f8f97...` value is retained only as a superseded local-worktree hash recorded for audit history.

## Future checkpoint rules

- Existing checkpoint 000001 MUST NOT be edited, deleted, renamed, or regenerated.
- Existing V3.13 report MUST NOT be rewritten.
- Checkpoint #2 and later MUST point to the canonical LF-normalized hash of the previous checkpoint.
- New checkpoint payloads MUST record:
  - `checkpoint_hash_scheme = SHA256_UTF8_LF_NORMALIZED_V1`
- Chain validator MUST compute parent hashes with this canonical scheme.
- Genesis is accepted as a legacy checkpoint without an embedded scheme only because its exact filename/content and authoritative repair hash are frozen here.

## Git normalization

Add repository attributes narrowly for future ledger artifacts:

`AlphaLab_Antigravity/reports/v3_13/checkpoints/*.json text eol=lf`
`V3_13_BLIND_OOS_CHECKPOINT_REPORT_*.md text eol=lf`

This does not authorize rewriting historical artifacts.

## No-peeking invariants

All V3.12/V3.13 governance remains unchanged:

- canonical cutoff inclusive: `2026-08-14T23:30:00Z`
- bridge quarter: `2026Q3` quarantined
- first complete OOS decision quarter: `2026Q4`
- minimum complete quarters: 8
- C1 total >=160
- C4 total >=100
- each complete quarter C1 >=10
- each complete quarter C4 >=5
- outcome metrics computed = false
- trading engine called = false
- strategy executed = false
- future OOS evaluator authorized = false
- same-sample H226 research closed = true
- historical H226 strategies = REJECTED

## Repair acceptance

V3.13.1 PASS requires all of the following:

1. frozen checkpoint 000001 remains byte/content unchanged in Git;
2. canonical LF-normalized SHA recomputes to `b45ac406...`;
3. historical local SHA `f8f97...` is explicitly marked superseded, not silently erased;
4. validator uses canonical hash scheme for chain pointers;
5. new writer emits LF deterministically without platform translation;
6. new checkpoint payloads declare the hash scheme;
7. synthetic checkpoint #2 test points to canonical genesis hash;
8. no OOS acquisition, outcome calculation, strategy execution, or strategy design occurs in this repair chapter.

## Stop rule

After technical repair audit/report, STOP.

Do not create checkpoint #2 as part of V3.13.1.
Do not run the MT5 exporter.
Do not calculate OOS outcomes.
Do not create H227.
