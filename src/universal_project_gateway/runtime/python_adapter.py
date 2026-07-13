"""Constrained adapter for allowlisted Python module actions."""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Any

from ..contracts import ADAPTER_CONTRACT_VERSION, AdapterCapability
from ..models import CommandSpec
from .base import RuntimeAdapter, RuntimeAdapterError, safe_relative_argument

_PYTHON_ALIASES = {"python", "python3", "py"}
_MODULES = {"compileall", "pip", "pytest", "unittest"}

PYTHON_ADAPTER_CAPABILITY = AdapterCapability(
    adapter_id="python",
    adapter_version="1.0.0",
    contract_version=ADAPTER_CONTRACT_VERSION,
    supported_project_types=("python",),
    supported_platforms=("linux", "macos", "windows"),
    capabilities=("inspect", "install", "lint", "test", "build", "smoke"),
    required_tools=("python>=3.11",),
    safety_notes=(
        "Only allowlisted Python modules and bounded arguments are accepted.",
        "Execution safety is limited by the selected sandbox backend.",
    ),
)


class PythonAdapter(RuntimeAdapter):
    adapter_name = "python"
    capability = PYTHON_ADAPTER_CAPABILITY

    def inspect_environment(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter_name,
            "available": True,
            "executable": sys.executable,
            "version": f"Python {platform.python_version()}",
            "workspace": str(self.workspace_root),
            "dependency_install_default": "disabled",
            "sandbox_backend": self.sandbox_backend.backend_id,
            "sandbox_safety_level": self.sandbox_backend.safety_level,
        }

    def _validated_argv(self, action: str, spec: CommandSpec) -> tuple[str, ...]:
        argv = spec.argv
        if argv[0].casefold() not in _PYTHON_ALIASES:
            raise RuntimeAdapterError(
                "Python actions must use an allowlisted interpreter alias",
                code="EXECUTABLE_NOT_ALLOWLISTED",
                details={"action": action, "executable": argv[0]},
            )
        if len(argv) < 3 or argv[1] != "-m":
            raise RuntimeAdapterError(
                "Python actions must invoke a module with -m",
                code="ARBITRARY_PYTHON_FORBIDDEN",
                details={"action": action},
            )
        module = argv[2].casefold()
        if module not in _MODULES:
            raise RuntimeAdapterError(
                "Python module is not allowlisted",
                code="PYTHON_MODULE_NOT_ALLOWLISTED",
                details={"action": action, "module": module},
            )
        if action == "install" and module != "pip":
            raise RuntimeAdapterError(
                "Python dependency installation must use pip",
                code="INSTALL_ACTION_MISMATCH",
            )
        if action != "install" and module == "pip":
            raise RuntimeAdapterError(
                "pip is permitted only for the install action",
                code="INSTALL_ACTION_MISMATCH",
            )

        arguments = argv[3:]
        if module == "pytest":
            self._validate_pytest(arguments)
        elif module == "unittest":
            self._validate_unittest(arguments)
        elif module == "compileall":
            self._validate_compileall(arguments)
        else:
            self._validate_pip(arguments)
        return (str(Path(sys.executable).resolve()), "-m", module, *arguments)

    @staticmethod
    def _validate_pytest(arguments: tuple[str, ...]) -> None:
        fixed_flags = {
            "-q",
            "--quiet",
            "-v",
            "--verbose",
            "-x",
            "--exitfirst",
            "--disable-warnings",
            "--strict-markers",
            "--strict-config",
        }
        for argument in arguments:
            if argument in fixed_flags or argument.startswith("--maxfail=") and argument[10:].isdigit():
                continue
            if argument.startswith("-"):
                raise RuntimeAdapterError(
                    "pytest flag is not allowlisted",
                    code="COMMAND_FLAG_FORBIDDEN",
                    details={"argument": argument},
                )
            safe_relative_argument(argument)

    @staticmethod
    def _validate_unittest(arguments: tuple[str, ...]) -> None:
        if not arguments:
            return
        index = 0
        if arguments[0] == "discover":
            index = 1
        simple_flags = {"-v", "--verbose", "-q", "--quiet", "-f", "--failfast", "-c", "--catch", "-b", "--buffer"}
        value_flags = {"-s", "--start-directory", "-t", "--top-level-directory", "-p", "--pattern"}
        while index < len(arguments):
            argument = arguments[index]
            if argument in simple_flags:
                index += 1
                continue
            if argument in value_flags:
                if index + 1 >= len(arguments):
                    raise RuntimeAdapterError(
                        "unittest option is missing its value",
                        code="INVALID_COMMAND_ARGV",
                        details={"argument": argument},
                    )
                safe_relative_argument(arguments[index + 1], allow_glob=argument in {"-p", "--pattern"})
                index += 2
                continue
            if argument.startswith("-"):
                raise RuntimeAdapterError(
                    "unittest flag is not allowlisted",
                    code="COMMAND_FLAG_FORBIDDEN",
                    details={"argument": argument},
                )
            # Dotted test names are safe identifiers, and relative test paths
            # remain contained by the same validator.
            if not all(part.isidentifier() for part in argument.split(".")):
                safe_relative_argument(argument)
            index += 1

    @staticmethod
    def _validate_compileall(arguments: tuple[str, ...]) -> None:
        flags = {"-q", "--quiet", "-f", "--force", "-b", "-d", "-s", "-p"}
        # Keep compileall deliberately small: common boolean flags and relative
        # source directories only.  Options that redirect output are refused.
        for argument in arguments:
            if argument in flags:
                if argument in {"-d", "-s", "-p"}:
                    raise RuntimeAdapterError(
                        "compileall path-rewriting flags are not permitted",
                        code="COMMAND_FLAG_FORBIDDEN",
                        details={"argument": argument},
                    )
                continue
            if argument.startswith("-"):
                raise RuntimeAdapterError(
                    "compileall flag is not allowlisted",
                    code="COMMAND_FLAG_FORBIDDEN",
                    details={"argument": argument},
                )
            safe_relative_argument(argument)

    @staticmethod
    def _validate_pip(arguments: tuple[str, ...]) -> None:
        if not arguments or arguments[0] != "install":
            raise RuntimeAdapterError(
                "pip action is limited to install",
                code="INVALID_PYTHON_INSTALL",
            )
        flags = {
            "--disable-pip-version-check",
            "--no-input",
            "--no-deps",
            "--require-hashes",
        }
        index = 1
        saw_requirement = False
        while index < len(arguments):
            argument = arguments[index]
            if argument in flags:
                index += 1
                continue
            if argument in {"-r", "--requirement"}:
                if index + 1 >= len(arguments):
                    raise RuntimeAdapterError(
                        "pip requirement option is missing a path",
                        code="INVALID_PYTHON_INSTALL",
                    )
                requirement = safe_relative_argument(arguments[index + 1])
                if not requirement.casefold().endswith((".txt", ".lock")):
                    raise RuntimeAdapterError(
                        "pip requirement path must be a text or lock file",
                        code="INVALID_PYTHON_INSTALL",
                    )
                saw_requirement = True
                index += 2
                continue
            raise RuntimeAdapterError(
                "pip argument is not allowlisted",
                code="COMMAND_FLAG_FORBIDDEN",
                details={"argument": argument},
            )
        if not saw_requirement:
            raise RuntimeAdapterError(
                "pip install requires an explicit workspace-relative requirements file",
                code="INVALID_PYTHON_INSTALL",
            )

    def _fixed_environment(self) -> dict[str, str]:
        return {
            **super()._fixed_environment(),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
        }


__all__ = ["PYTHON_ADAPTER_CAPABILITY", "PythonAdapter"]
