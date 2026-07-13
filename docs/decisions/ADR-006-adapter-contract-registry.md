# ADR-006: Versioned adapter contract registry

- Status: accepted
- Date: 2026-07-14
- Checkpoint: UPG-CONTRACT-002

## Context

UPG previously selected Python or Node with conditionals in `runtime.__init__`
and manifest validation recognized those two identifiers directly. That was
adequate for the vertical slice, but it gave the runner no versioned capability
contract and would encourage each future runtime family to add more selection
logic to Gateway core. Validation/evidence also identified argv and sandbox
metadata without identifying the adapter contract that authorized the action.

The extension seam must remain narrower than a plugin system. Runtime code is
trusted project code, and dynamically loading an adapter from a manifest would
turn untrusted configuration into code-loading authority.

## Decision

UPG defines four additive compatibility identifiers with descriptive schemas:

- `upg.manifest/v1`
- `upg.adapter/v1`
- `upg.execution/v1`
- `upg.evidence/v1`

Manifest schema `1.0` and evidence schema `2.0` remain their existing concrete
formats. A contract identifier describes a compatibility family; it does not
renumber or replace those schema versions.

Each reviewed adapter class declares immutable `AdapterCapability` metadata:
ID, semantic adapter version, contract version, supported project types and
platforms, named capabilities, required tools, and safety notes. A fresh
`AdapterRegistry` registers the Python and Node built-ins. `LocalRunner`
resolves every mandatory manifest action through that registry before creating
the adapter and submits only adapter-validated requests to the existing sandbox
backend.

Resolution considers:

1. the manifest's declared `runtime_adapters`;
2. an optional `commands.<action>.adapter` selection;
3. project type and current platform;
4. the named action-to-capability mapping; and
5. optional manifest `adapter_requirements` for contract, exact version, and
   additional capabilities.

Unknown, incompatible, unsupported, or ambiguous resolution is refused with a
structured error. The CLI `adapter list` command and MCP
`gateway_list_adapters` tool return copied metadata only; they do not check tool
availability or execute code.

Validation results add `upg.execution/v1` plus resolved adapter metadata.
Environment evidence and evidence-chain phase payloads record the same stable
resolution. Sandbox fields remain unchanged. New attestations add
`upg.evidence/v1`; both verifiers accept the previous evidence-schema-v2 form
without that additive field.

## Compatibility

Existing schema-`1.0` manifests omit `contract_version` and
`adapter_requirements`; the loader defaults them to `upg.manifest/v1` and no
extra expectations. The unchanged Python and Node fixture manifests exercise
this path. UPG's root manifest declares its Python `lint` and `test`
expectations explicitly, and its portable seed-registry checksum is updated.

The existing `create_runtime_adapter` function remains as a compatibility
wrapper and preserves its historical unknown-project-type error code. Existing
CLI/MCP tools and validation fields are retained; all contract and adapter
metadata is additive.

## Security consequences

- Registry declarations do not grant new manifest permissions or process
  authority.
- Manifest/user text still cannot provide a class, module, executable, argv,
  or shell command.
- Adapters continue to validate argv before the sandbox receives a typed
  execution request.
- Capability listing is not evidence that a required executable is installed.
- Adapter safety notes do not upgrade either local sandbox into an OS security
  boundary.

## Rejected alternatives

- Dynamic entry-point/module loading from manifests: rejected because it adds
  an unreviewed code-loading boundary and plugin lifecycle/versioning.
- One generic adapter accepting arbitrary argv: rejected because it destroys
  the named-action allowlist.
- Encoding video, Revit, trading, or other domain branches in Gateway core:
  rejected because domains belong in separately reviewed adapters/projects.
- Requiring all existing manifests to add contract fields: rejected because
  the change is additive and has a safe deterministic default.

## Deferred work

Dynamic adapter packaging, signature/trust policy, dependency acquisition,
remote distribution, domain adapters, and adapter upgrade negotiation are
separate checkpoints. Any such work requires a new threat model and must not
bypass registry, manifest, sandbox, or evidence boundaries.
