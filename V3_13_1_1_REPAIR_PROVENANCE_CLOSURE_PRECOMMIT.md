# V3.13.1.1 — REPAIR PROVENANCE CLOSURE PRECOMMIT

Scientific parent: `af7ee188f46a658aa8134282721c4bbf3a3e0f32`

## Purpose

V3.13.1 scientifically repaired checkpoint hash portability, but its raw audit commit also contained a technical source edit. Because the audit records `git rev-parse HEAD`, its machine artifact reported the pre-repair frozen HEAD even though the executed working-tree source already contained the technical edit.

This chapter repairs only that audit provenance ambiguity.

## Frozen conclusions

- V3.13.1 hash scheme remains `SHA256_UTF8_LF_NORMALIZED_V1`.
- Authoritative genesis chain SHA remains `b45ac406bfa7da1436f23f0add600a6354485b5a4d5d25c064b3470e23300876`.
- Historical local SHA `f8f97c2a7aa47e79784f37dc83072896971d52a34fef8ba28248351447ac000b` remains `SUPERSEDED_FOR_LEDGER_CHAIN_AUTHORITY`.
- Genesis payload and historical V3.13 report remain immutable.
- Exactly one checkpoint must exist.
- No OOS acquisition, checkpoint #2, outcome calculation, engine call, or strategy research is permitted.

## Provenance rule

The execution audit must run from a clean working tree. Its `artifact_generation_parent_sha` must equal the exact clean Git HEAD containing all code used by the audit.

If any technical repair is needed, it must be committed first as a separate technical-repair commit. The audit may run only after that commit exists and the working tree is clean. Raw evidence must then be committed separately after execution.

## Stop

This chapter does not alter V3.13.1 scientific semantics. It only closes execution-code provenance.