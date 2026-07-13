# Instructions for coding agents

The Universal Project Gateway (UPG) is a project-agnostic local orchestration
layer. Before changing it, read `docs/ARCHITECTURE.md`,
`docs/SECURITY_MODEL.md`, `state/CURRENT_STATE.json`, and the active project's
`PROJECT_MANIFEST.yaml` and memory files.

## Required working rules

1. Establish the active project, job ID, isolated workspace, target paths, and
   required validation before editing.
2. Inspect source projects read-only. Modify only the job workspace unless a
   separately authorized publication operation is explicitly requested.
3. Keep changes within the requested scope and avoid unrelated refactors.
4. Treat manifest commands as named, allowlisted adapter actions. Never turn
   model or user text into a shell command.
5. Respect protected paths and canonical path checks. Never bypass policy,
   follow an escaping link, or copy protected content into evidence.
6. Never store credentials, tokens, private keys, or environment secrets in
   source, manifests, logs, context packs, or evidence.
7. Record the exact validation action, argv, outcome, and relevant output.
   Never claim a command or test was run when it was not.
8. A file edit is not success by itself: all mandatory validation requirements
   must pass and the evidence checksum manifest must verify.
9. Never commit directly to `main`, `master`, or the detected default branch.
   Never merge automatically, force-push, or deploy.
10. Stop and return a structured refusal for R4 actions, path escape attempts,
    arbitrary execution, or requests outside the active job and project scope.

Runtime output belongs only under ignored `var/`, `workspaces/`, and
`artifacts/` directories. Preserve durable documentation when behavior or a
trust boundary changes.
