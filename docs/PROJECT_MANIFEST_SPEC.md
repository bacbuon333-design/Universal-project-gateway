# Project manifest specification

## Purpose

`PROJECT_MANIFEST.yaml` is the boundary between the universal Gateway and a
managed project's facts and permissions. Registration must validate the
manifest before any source path, command, or policy is used.

This document describes schema version `1.0`. Unknown required schema versions
must be rejected rather than guessed.

## Complete example

```yaml
schema_version: "1.0"
project_id: sample-project
name: Sample project
description: A short, non-secret description.
project_type: python

sources:
  local_path: "."
  github_repository: null

stack:
  language: Python
  minimum_version: "3.11"
  dependency_manager: none

important_paths:
  - src/
  - tests/

entrypoints:
  library: src/sample.py

memory_files:
  - AGENTS.md

commands:
  install: null
  lint:
    argv: [python, -m, compileall, -q, src, tests]
  test:
    argv: [python, -m, unittest, discover, -s, tests]
  build: null
  smoke_test: null

permissions:
  read: true
  workspace_write: true
  validation: true
  git_publish: false

protected_paths:
  - .env
  - secrets/

validation_requirements:
  - test

publication_policy:
  allow_local_branch: false
  allow_push: false
  allow_merge: false

runtime_adapters:
  - python

state_file: null
```

## Fields

### Identity

- `schema_version` (required string): currently `1.0`.
- `project_id` (required string): stable lowercase identifier using ASCII
  letters, digits, single hyphens, or underscores. It must be filesystem-safe,
  cannot contain separators or `..`, and should not change when a project moves.
- `name` (required string): short display name.
- `description` (required string): concise, non-secret purpose.
- `project_type` (required string): selects a compatible runtime family, such
  as `python` or `node`; it does not add business-domain logic to the Gateway.

### Source

- `sources.local_path` is a local directory. A relative value is resolved
  against the manifest directory and then canonicalized. Registration persists
  its normalized path. The directory must exist and contain the manifest.
- `sources.github_repository` is optional metadata for a future connector. It
  is not cloned or authenticated in the default MVP.

Paths and URLs must not embed usernames, passwords, tokens, credential query
parameters, or private key material.

### Project context

- `stack` is descriptive structured metadata.
- `important_paths` is a list of project-relative files or directories to
  prioritize in bounded context.
- `entrypoints` maps meaningful roles to project-relative files.
- `memory_files` lists project-relative UTF-8 text files the context compiler
  may read.
- `state_file` is either a project-relative state document or `null`.

Context declarations do not override protected-path or size controls. Absolute
paths and escaping traversal are invalid.

### Commands

`commands` declares the fixed action names `install`, `lint`, `test`, `build`,
and `smoke_test`. An unavailable action is `null`. An available action contains
an `argv` list of non-empty strings.

An argv declaration is not a generic subprocess API. Validation ensures the
executable and arguments fit the selected adapter's allowlist. At execution,
the service accepts only an action name; callers cannot replace the executable
or append arbitrary flags. The adapter uses `shell=False`, the workspace as
`cwd`, timeout and output limits, and a bounded environment.

For Node.js, a manifest action must be consistent with a declared, safe script
or direct built-in Node invocation. The fixtures require no package download.
For Python, interpreter aliases are resolved to the active allowed Python
runtime rather than interpolated into a shell string.

`install` is separately gated and disabled by default because installation can
execute project code and access a package network.

### Permissions and validation

- `permissions.read`: permit scoped workspace inspection (R0).
- `permissions.workspace_write`: permit scoped isolated mutation (R1).
- `permissions.validation`: permit allowlisted validation (R2).
- `permissions.git_publish`: make R3 eligible; explicit call permission is
  still required.
- `validation_requirements`: action names that must pass before job success.
- `runtime_adapters`: permitted adapter identifiers. They must be compatible
  with `project_type` and each executable declaration.

Permission is conjunctive: a manifest can reduce Gateway authority but cannot
enable an operation the Gateway globally prohibits.

### Protected paths and publication

`protected_paths` contains project-relative files or directory prefixes that
cannot be read, changed, followed, or copied as raw evidence. Common entries
include `.env`, key directories, and generated credentials.

`publication_policy` records project policy. In the MVP, local branch creation
may be allowed only when both it and `permissions.git_publish` are true. Push
is not part of the default demo. Merge, force-push, default-branch commits, and
deployment remain globally prohibited regardless of manifest values.

## Validation and errors

Invalid manifests produce a structured result rather than a traceback. A
validation error contains a stable code, a field path, and a useful message,
for example:

```json
{
  "valid": false,
  "errors": [
    {
      "code": "INVALID_PROJECT_ID",
      "field": "project_id",
      "message": "project_id must be a filesystem-safe stable identifier"
    }
  ]
}
```

Registration rejects at least:

- missing required concepts or wrong value types;
- unsupported schema versions;
- unsafe, empty, or duplicate project IDs;
- nonexistent, non-directory, or unregistered source paths;
- absolute or escaping project-relative paths;
- protected paths that conflict with required mutable/validation targets;
- credential-looking source metadata or manifest values;
- arbitrary executables, shell operators, command strings, or disallowed argv;
- missing mandatory validation actions;
- incompatible project type and runtime adapter;
- publication settings that request globally prohibited authority.

Registration should report all independently detectable schema errors in one
response when it is safe to continue validation.

## Compatibility

Adding optional descriptive fields is backward-compatible. Changing command,
permission, path, or publication semantics requires a new schema version and a
documented migration. The Gateway must preserve the original manifest hash in
job evidence so reviewers can identify the contract used for a run.
