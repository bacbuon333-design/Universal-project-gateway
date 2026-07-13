# Python fixture memory

This is a deterministic managed-project fixture, not Gateway core code.

- The only demo edit is in `src/greeting.py`.
- Preserve the public function name `greeting`.
- The intended post-demo result is exactly `Hello from UPG`.
- Run the manifest's `test` action after the edit.
- Do not add dependencies or modify this source project directly; the Gateway
  must make the change in a per-job workspace.
