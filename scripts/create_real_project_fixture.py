"""Create one dependency-free external Python project for controlled UPG testing."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

PROJECT_ID = "hello-web-app"
INITIAL_GREETING = "Hello from the external web app"
UPDATED_GREETING = "Hello from UPG real integration"
_WINDOWS_REPARSE_POINT = 0x400

PROJECT_FILES = {
    "README.md": """# Hello Web App

This dependency-free Python WSGI application is a controlled external project
used to verify Universal Project Gateway against a real Git repository outside
the Gateway source tree. Run its tests with:

```powershell
python -m unittest discover -s tests -p test_*.py -v
```
""",
    "AGENTS.md": """# Local project instructions

Keep this sample dependency-free. Change source only through an isolated UPG
job workspace, run the manifest's named validation actions, and publish only a
reviewed non-default local branch. Never add credentials or a remote.
""",
    "src/hello_web_app.py": f'''"""Tiny dependency-free WSGI application."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any


def greeting() -> str:
    return "{INITIAL_GREETING}"


def application(
    environ: dict[str, Any],
    start_response: Callable[[str, list[tuple[str, str]]], Any],
) -> Iterable[bytes]:
    del environ
    body = f"<h1>{{greeting()}}</h1>\\n".encode("utf-8")
    start_response(
        "200 OK",
        [("Content-Type", "text/html; charset=utf-8"), ("Content-Length", str(len(body)))],
    )
    return [body]
''',
    "tests/test_app.py": f'''from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hello_web_app import application, greeting  # noqa: E402


class HelloWebAppTests(unittest.TestCase):
    def test_greeting(self) -> None:
        self.assertEqual(greeting(), "{INITIAL_GREETING}")

    def test_wsgi_response(self) -> None:
        response: dict[str, object] = {{}}

        def start_response(status: str, headers: list[tuple[str, str]]) -> None:
            response["status"] = status
            response["headers"] = headers

        body = b"".join(application({{}}, start_response)).decode("utf-8")
        self.assertEqual(response["status"], "200 OK")
        self.assertIn(greeting(), body)


if __name__ == "__main__":
    unittest.main()
''',
    "PROJECT_MANIFEST.yaml": """schema_version: "1.0"
contract_version: upg.manifest/v1
project_id: hello-web-app
name: External Hello Web App
description: Dependency-free Python WSGI app used for controlled UPG integration.
project_type: python

sources:
  local_path: "."
  github_repository: null

stack:
  language: Python
  minimum_version: "3.11"
  dependency_manager: none
  service_interfaces:
    - WSGI
  managed_path_groups:
    source:
      - src/
    tests:
      - tests/
    documentation:
      - README.md

important_paths:
  - src/hello_web_app.py
  - tests/test_app.py
  - README.md

entrypoints:
  wsgi_application: src/hello_web_app.py

memory_files:
  - AGENTS.md

commands:
  install: null
  lint:
    argv: [python, -m, compileall, -q, src, tests]
  test:
    argv: [python, -m, unittest, discover, -s, tests, -p, "test_*.py", -v]
  build:
    argv: [python, -m, compileall, -q, src]
  smoke_test:
    argv: [python, -m, unittest, discover, -s, tests, -p, "test_*.py"]

permissions:
  read: true
  workspace_write: true
  validation: true
  git_publish: true

protected_paths:
  - .env
  - .env.*
  - .git/
  - secrets/
  - credentials/
  - "*.key"
  - "*.pem"

validation_requirements:
  - lint
  - test

publication_policy:
  allow_local_branch: true
  allow_push: false
  allow_merge: false

runtime_adapters:
  - python

adapter_requirements:
  - adapter_id: python
    adapter_version: "1.0.0"
    contract_version: upg.adapter/v1
    capabilities: [lint, test]

state_file: null
""",
}


class FixtureCreationError(RuntimeError):
    """Refuse an unsafe or non-empty external project destination."""


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        return bool(getattr(path.lstat(), "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT)
    except OSError:
        return False


def _validate_destination(project_root: Path, gateway_root: Path) -> None:
    if project_root.exists():
        raise FixtureCreationError(f"external project destination already exists: {project_root}")
    if project_root.name in {"", ".", ".."} or any(
        part.casefold() == ".git" for part in project_root.parts
    ):
        raise FixtureCreationError("external project destination is not safe")
    if _is_within(project_root, gateway_root) or _is_within(gateway_root, project_root):
        raise FixtureCreationError("external project must be separate from the Gateway repository")
    for ancestor in project_root.parents:
        if ancestor.exists() and _is_link_or_reparse(ancestor):
            raise FixtureCreationError("external project parent must not be a link or reparse point")


def _git_environment() -> dict[str, str]:
    environment = {
        name: os.environ[name]
        for name in (
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "WINDIR",
            "COMSPEC",
            "HOME",
            "USERPROFILE",
            "TEMP",
            "TMP",
        )
        if name in os.environ
    }
    environment.update({"GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "Never"})
    return environment


def _git(project_root: Path, *arguments: str) -> str:
    git = shutil.which("git")
    if git is None:
        raise FixtureCreationError("Git is required to create the external test project")
    result = subprocess.run(
        [git, "-c", f"core.hooksPath={os.devnull}", *arguments],
        cwd=project_root,
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        env=_git_environment(),
    )
    if result.returncode != 0:
        raise FixtureCreationError(
            f"Git operation {arguments[0]!r} failed with code {result.returncode}: "
            f"{result.stderr.strip()[:500]}"
        )
    return result.stdout.strip()


def create_real_project_fixture(
    project_root: str | os.PathLike[str],
    *,
    gateway_root: str | os.PathLike[str],
) -> dict[str, Any]:
    """Create and commit a fresh external project without configuring a remote."""

    destination = Path(project_root).expanduser().resolve(strict=False)
    gateway = Path(gateway_root).expanduser().resolve(strict=True)
    _validate_destination(destination, gateway)
    destination.mkdir(parents=True, exist_ok=False)
    for relative, content in PROJECT_FILES.items():
        path = destination.joinpath(*relative.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")

    _git(destination, "init")
    _git(destination, "config", "user.name", "UPG Real Integration")
    _git(destination, "config", "user.email", "upg-real-integration@example.invalid")
    _git(destination, "add", "--", *sorted(PROJECT_FILES))
    _git(destination, "commit", "--no-verify", "-m", "Initial external web app")
    _git(destination, "branch", "-M", "main")
    commit = _git(destination, "rev-parse", "HEAD")
    if _git(destination, "status", "--porcelain"):
        raise FixtureCreationError("new external project did not finish with a clean Git tree")
    if _git(destination, "remote"):
        raise FixtureCreationError("external fixture must not configure a Git remote")
    return {
        "project_id": PROJECT_ID,
        "project_root": str(destination),
        "manifest_path": str(destination / "PROJECT_MANIFEST.yaml"),
        "initial_branch": "main",
        "initial_commit": commit,
        "remote_count": 0,
        "files": sorted(PROJECT_FILES),
    }


def _default_project_root() -> Path:
    if os.name == "nt":
        return Path("Z:/UPG Test Projects/hello-web-app")
    return Path("/tmp/UPG Test Projects/hello-web-app")


def main() -> int:
    repository_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=_default_project_root())
    parser.add_argument("--gateway-root", type=Path, default=repository_root)
    args = parser.parse_args()
    result = create_real_project_fixture(
        args.project_root,
        gateway_root=args.gateway_root,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
