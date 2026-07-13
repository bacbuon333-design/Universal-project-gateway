"""Constrained adapter for Node's built-in checks and declared npm scripts."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from ..models import CommandSpec
from .base import RuntimeAdapter, RuntimeAdapterError, safe_relative_argument

_SCRIPT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9:._-]{0,127}$")


class NodeAdapter(RuntimeAdapter):
    adapter_name = "node"

    def inspect_environment(self) -> dict[str, Any]:
        executable = shutil.which("node")
        if not executable:
            return {
                "adapter": self.adapter_name,
                "available": False,
                "executable": None,
                "version": None,
                "workspace": str(self.workspace_root),
                "dependency_install_default": "disabled",
                "sandbox_backend": self.sandbox_backend.backend_id,
                "sandbox_safety_level": self.sandbox_backend.safety_level,
            }
        result = self._inspect_runtime((str(Path(executable).resolve()), "--version"))
        return {
            "adapter": self.adapter_name,
            "available": result.passed,
            "executable": executable,
            "version": (result.stdout or result.stderr).strip() or None,
            "workspace": str(self.workspace_root),
            "dependency_install_default": "disabled",
            "sandbox_backend": self.sandbox_backend.backend_id,
            "sandbox_safety_level": self.sandbox_backend.safety_level,
            "inspection": result.to_dict(),
        }

    def _validated_argv(self, action: str, spec: CommandSpec) -> tuple[str, ...]:
        executable = spec.argv[0].casefold()
        if executable == "node":
            return self._validate_node(action, spec.argv)
        if executable in {"npm", "npm.cmd"}:
            return self._validate_npm(action, spec.argv)
        raise RuntimeAdapterError(
            "Node actions must use node or npm",
            code="EXECUTABLE_NOT_ALLOWLISTED",
            details={"action": action, "executable": spec.argv[0]},
        )

    def _validate_node(self, action: str, argv: tuple[str, ...]) -> tuple[str, ...]:
        executable = shutil.which("node")
        if not executable:
            raise RuntimeAdapterError("node executable was not found", code="EXECUTABLE_NOT_FOUND")
        if len(argv) < 2 or argv[1] not in {"--test", "--check"}:
            raise RuntimeAdapterError(
                "direct Node actions are limited to --test and --check",
                code="ARBITRARY_NODE_FORBIDDEN",
                details={"action": action},
            )
        mode = argv[1]
        arguments = argv[2:]
        if mode == "--check":
            if len(arguments) != 1:
                raise RuntimeAdapterError(
                    "node --check requires exactly one relative source file",
                    code="INVALID_NODE_COMMAND",
                )
            relative = safe_relative_argument(arguments[0])
            if not relative.casefold().endswith((".js", ".cjs", ".mjs")):
                raise RuntimeAdapterError(
                    "node --check is limited to JavaScript source files",
                    code="INVALID_NODE_COMMAND",
                )
            arguments = (relative,)
        else:
            checked: list[str] = []
            for argument in arguments:
                if argument.startswith("-"):
                    raise RuntimeAdapterError(
                        "Node test flags are not allowlisted in this MVP",
                        code="COMMAND_FLAG_FORBIDDEN",
                        details={"argument": argument},
                    )
                checked.append(safe_relative_argument(argument, allow_glob=True))
            arguments = tuple(checked)
        return (str(Path(executable).resolve()), mode, *arguments)

    def _validate_npm(self, action: str, argv: tuple[str, ...]) -> tuple[str, ...]:
        executable = shutil.which("npm.cmd") or shutil.which("npm")
        if not executable:
            raise RuntimeAdapterError("npm executable was not found", code="EXECUTABLE_NOT_FOUND")
        arguments = tuple(argument.casefold() for argument in argv[1:])
        if action == "install":
            if arguments != ("ci",):
                raise RuntimeAdapterError(
                    "Node installation is limited to npm ci",
                    code="INVALID_NODE_INSTALL",
                )
            return (executable, "ci")

        if len(argv) == 2 and arguments[0] == "test":
            script = "test"
            resolved = (executable, "test")
        elif len(argv) == 3 and arguments[0] == "run":
            script = argv[2]
            if not _SCRIPT_NAME.fullmatch(script):
                raise RuntimeAdapterError(
                    "npm script name is not filesystem-safe",
                    code="INVALID_NPM_SCRIPT",
                    details={"script": script},
                )
            resolved = (executable, "run", script)
        else:
            raise RuntimeAdapterError(
                "npm validation must select one fixed package script",
                code="INVALID_NODE_COMMAND",
                details={"action": action},
            )
        scripts = self._package_scripts()
        if script not in scripts:
            raise RuntimeAdapterError(
                "npm script is not declared in package.json",
                code="NPM_SCRIPT_NOT_DECLARED",
                details={"script": script},
            )
        return resolved

    def _package_scripts(self) -> dict[str, str]:
        package_path = self.workspace_root / "package.json"
        if not package_path.is_file() or package_path.stat().st_size > 1_000_000:
            raise RuntimeAdapterError(
                "a bounded package.json is required for npm script actions",
                code="PACKAGE_JSON_INVALID",
            )
        try:
            data = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeAdapterError(
                "package.json is not valid UTF-8 JSON",
                code="PACKAGE_JSON_INVALID",
            ) from exc
        scripts = data.get("scripts") if isinstance(data, dict) else None
        if not isinstance(scripts, dict) or any(
            not isinstance(name, str) or not isinstance(value, str)
            for name, value in scripts.items()
        ):
            raise RuntimeAdapterError(
                "package.json scripts must be a string mapping",
                code="PACKAGE_JSON_INVALID",
            )
        return scripts

    def _fixed_environment(self) -> dict[str, str]:
        return {
            **super()._fixed_environment(),
            "npm_config_audit": "false",
            "npm_config_fund": "false",
            "npm_config_ignore_scripts": "true",
            "npm_config_update_notifier": "false",
        }


__all__ = ["NodeAdapter"]
