"""Loading and structured validation for ``PROJECT_MANIFEST.yaml`` files."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import yaml

from .contracts import (
    ADAPTER_CONTRACT_VERSION,
    MANIFEST_CONTRACT_VERSION,
    AdapterRequirement,
)
from .models import (
    CommandSpec,
    GatewayError,
    ManifestValidationIssue,
    ManifestValidationResult,
    ProjectManifest,
    ProjectPermissions,
    ProjectSources,
)

SUPPORTED_SCHEMA_VERSION = "1.0"
MAX_MANIFEST_BYTES = 1_000_000
COMMAND_NAMES = ("install", "lint", "test", "build", "smoke_test")
REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "project_id",
    "name",
    "description",
    "project_type",
    "sources",
    "stack",
    "important_paths",
    "entrypoints",
    "memory_files",
    "commands",
    "permissions",
    "protected_paths",
    "validation_requirements",
    "publication_policy",
    "runtime_adapters",
    "state_file",
)

_PROJECT_ID_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,62}[a-z0-9])?$")
_ADAPTER_NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")
_WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[/\\]")
_SECRET_KEY_PATTERN = re.compile(
    r"(?:^|_)(?:api_?key|access_?key|password|passwd|secrets?|tokens?|credentials?|private_?key)(?:$|_)",
    re.IGNORECASE,
)
_CREDENTIAL_QUERY_KEYS = {
    "access_token",
    "api_key",
    "apikey",
    "auth",
    "key",
    "password",
    "secret",
    "token",
}
_SHELL_OPERATOR_PATTERN = re.compile(r"(?:&&|\|\||[;|<>`]|\$\(|%COMSPEC%)", re.IGNORECASE)


class ManifestValidationError(GatewayError):
    default_code = "INVALID_MANIFEST"

    def __init__(self, errors: Sequence[ManifestValidationIssue]) -> None:
        self.errors = tuple(errors)
        super().__init__(
            f"Manifest validation failed with {len(self.errors)} error(s)",
            details={"errors": [error.to_dict() for error in self.errors]},
        )


class ManifestLoadError(GatewayError):
    default_code = "MANIFEST_LOAD_ERROR"


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that refuses ambiguous duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate key {key!r}",
                key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


def _issue(errors: list[ManifestValidationIssue], code: str, path: str, message: str) -> None:
    errors.append(ManifestValidationIssue(code=code, path=path, message=message))


def _is_sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


def _normalize_relative_path(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("\\", "/")
    if (
        candidate.startswith("/")
        or candidate.startswith("//")
        or _WINDOWS_ABSOLUTE_PATTERN.match(candidate)
    ):
        return None
    path = PurePosixPath(candidate)
    if any(part in {"", ".", ".."} for part in path.parts):
        return None
    return path.as_posix().rstrip("/")


def _validate_relative_paths(
    value: Any,
    field: str,
    errors: list[ManifestValidationIssue],
) -> tuple[str, ...]:
    if not _is_sequence(value):
        _issue(errors, "INVALID_TYPE", field, f"{field} must be a list of relative paths")
        return ()
    normalized: list[str] = []
    for index, item in enumerate(value):
        path = _normalize_relative_path(item)
        if path is None:
            _issue(
                errors,
                "UNSAFE_RELATIVE_PATH",
                f"{field}[{index}]",
                "path must be non-empty, project-relative, and must not contain '..'",
            )
        else:
            normalized.append(path)
    return tuple(dict.fromkeys(normalized))


def _has_embedded_credentials(value: str) -> bool:
    if "-----BEGIN " in value and "PRIVATE KEY-----" in value:
        return True
    if "://" not in value:
        return False
    parsed = urlsplit(value)
    if parsed.username is not None or parsed.password is not None:
        return True
    return any(key.casefold() in _CREDENTIAL_QUERY_KEYS for key, _ in parse_qsl(parsed.query))


def _scan_for_secret_fields(
    value: Any,
    path: str,
    errors: list[ManifestValidationIssue],
) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if (
                isinstance(key, str)
                and _SECRET_KEY_PATTERN.search(key)
                and item not in (None, "", False, [])
            ):
                _issue(
                    errors,
                    "SECRET_FIELD_FORBIDDEN",
                    child_path,
                    "credentials and secrets must not be stored in project manifests",
                )
            _scan_for_secret_fields(item, child_path, errors)
    elif _is_sequence(value):
        for index, item in enumerate(value):
            _scan_for_secret_fields(item, f"{path}[{index}]", errors)
    elif isinstance(value, str) and _has_embedded_credentials(value):
        _issue(
            errors,
            "EMBEDDED_CREDENTIAL_FORBIDDEN",
            path,
            "URLs and values in manifests must not embed credentials",
        )


def _validate_string(
    data: Mapping[str, Any], field: str, errors: list[ManifestValidationIssue]
) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        _issue(errors, "INVALID_TYPE", field, f"{field} must be a non-empty string")
        return ""
    return value.strip()


def _validate_command_argv(
    name: str,
    argv: tuple[str, ...],
    project_type: str,
    errors: list[ManifestValidationIssue],
) -> None:
    field = f"commands.{name}.argv"
    if any("\x00" in argument or "\r" in argument or "\n" in argument for argument in argv):
        _issue(
            errors,
            "UNSAFE_COMMAND_ARGUMENT",
            field,
            "argv entries may not contain control characters",
        )
    if any(_SHELL_OPERATOR_PATTERN.search(argument) for argument in argv):
        _issue(errors, "SHELL_OPERATOR_FORBIDDEN", field, "shell operators are not allowed in argv")

    executable = argv[0].casefold() if argv else ""
    if project_type == "python":
        if executable not in {"python", "python3", "py"}:
            _issue(
                errors,
                "EXECUTABLE_NOT_ALLOWLISTED",
                f"{field}[0]",
                "Python actions must use an allowlisted Python interpreter alias",
            )
            return
        prohibited = {"-c", "-", "-i"}
        if any(argument.casefold() in prohibited for argument in argv[1:]):
            _issue(
                errors,
                "ARBITRARY_PYTHON_FORBIDDEN",
                field,
                "inline or interactive Python is prohibited",
            )
        if len(argv) < 3 or argv[1] != "-m":
            _issue(
                errors,
                "INVALID_PYTHON_COMMAND",
                field,
                "Python commands must invoke an allowlisted module with -m",
            )
            return
        allowed_modules = {"compileall", "pip", "pytest", "unittest"}
        if argv[2].casefold() not in allowed_modules:
            _issue(
                errors,
                "PYTHON_MODULE_NOT_ALLOWLISTED",
                f"{field}[2]",
                "Python module is not allowlisted",
            )
        if name != "install" and argv[2].casefold() == "pip":
            _issue(
                errors,
                "INSTALL_ACTION_MISMATCH",
                field,
                "pip may only be declared for the install action",
            )
        if name == "install" and argv[2].casefold() != "pip":
            _issue(
                errors,
                "INSTALL_ACTION_MISMATCH",
                field,
                "Python install must use the allowlisted pip module",
            )
        elif name == "install" and (len(argv) < 4 or argv[3].casefold() != "install"):
            _issue(
                errors,
                "INVALID_PYTHON_INSTALL",
                field,
                "Python install is limited to the pip install subcommand",
            )
    elif project_type == "node":
        if executable == "node":
            if name == "install":
                _issue(
                    errors,
                    "INVALID_NODE_INSTALL",
                    field,
                    "Node install is limited to 'npm ci'",
                )
            prohibited = {"-e", "--eval", "-p", "--print", "-i", "--interactive"}
            if any(argument.casefold() in prohibited for argument in argv[1:]):
                _issue(
                    errors,
                    "ARBITRARY_NODE_FORBIDDEN",
                    field,
                    "inline or interactive Node execution is prohibited",
                )
            if len(argv) < 2 or argv[1] not in {"--check", "--test"}:
                _issue(
                    errors,
                    "INVALID_NODE_COMMAND",
                    field,
                    "direct Node actions must use --check or --test",
                )
        elif executable in {"npm", "npm.cmd"}:
            if name == "install":
                if tuple(argument.casefold() for argument in argv[1:]) != ("ci",):
                    _issue(
                        errors, "INVALID_NODE_INSTALL", field, "Node install is limited to 'npm ci'"
                    )
            elif not (
                (
                    name == "test"
                    and tuple(argument.casefold() for argument in argv[1:]) == ("test",)
                )
                or tuple(argument.casefold() for argument in argv[1:]) == ("run", name.casefold())
            ):
                _issue(
                    errors,
                    "INVALID_NODE_COMMAND",
                    field,
                    "npm actions must select the package script matching the manifest action",
                )
        else:
            _issue(
                errors,
                "EXECUTABLE_NOT_ALLOWLISTED",
                f"{field}[0]",
                "Node actions must use node or npm",
            )


def _validate_commands(
    value: Any,
    project_type: str,
    runtime_adapters: tuple[str, ...],
    errors: list[ManifestValidationIssue],
) -> dict[str, CommandSpec | None]:
    if not isinstance(value, Mapping):
        _issue(errors, "INVALID_TYPE", "commands", "commands must be a mapping")
        return {name: None for name in COMMAND_NAMES}

    for name in COMMAND_NAMES:
        if name not in value:
            _issue(
                errors,
                "MISSING_FIELD",
                f"commands.{name}",
                f"commands.{name} is required (use null when unavailable)",
            )
    for name in value:
        if name not in COMMAND_NAMES:
            _issue(
                errors,
                "UNKNOWN_COMMAND",
                f"commands.{name}",
                "command action is not supported by this schema",
            )

    commands: dict[str, CommandSpec | None] = {}
    for name in COMMAND_NAMES:
        raw = value.get(name)
        if raw is None:
            commands[name] = None
            continue
        if not isinstance(raw, Mapping):
            _issue(
                errors,
                "COMMAND_MUST_USE_ARGV",
                f"commands.{name}",
                "command must be null or a mapping containing an argv list; command strings are forbidden",
            )
            commands[name] = None
            continue
        raw_argv = raw.get("argv")
        if not _is_sequence(raw_argv) or not raw_argv:
            _issue(
                errors,
                "INVALID_COMMAND_ARGV",
                f"commands.{name}.argv",
                "argv must be a non-empty list of strings",
            )
            commands[name] = None
            continue
        if any(not isinstance(argument, str) or not argument for argument in raw_argv):
            _issue(
                errors,
                "INVALID_COMMAND_ARGV",
                f"commands.{name}.argv",
                "every argv entry must be a non-empty string",
            )
            commands[name] = None
            continue
        argv = tuple(raw_argv)
        timeout = raw.get("timeout_seconds", 120)
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 600:
            _issue(
                errors,
                "INVALID_TIMEOUT",
                f"commands.{name}.timeout_seconds",
                "timeout must be an integer from 1 to 600 seconds",
            )
            timeout = 120
        adapter = raw.get("adapter")
        if adapter is not None and (
            not isinstance(adapter, str) or adapter not in runtime_adapters
        ):
            _issue(
                errors,
                "INVALID_COMMAND_ADAPTER",
                f"commands.{name}.adapter",
                "adapter must name a declared runtime adapter",
            )
            adapter = None
        environment_raw = raw.get("environment", [])
        if not _is_sequence(environment_raw) or any(
            not isinstance(item, str) or not item for item in environment_raw
        ):
            _issue(
                errors,
                "INVALID_ENVIRONMENT_ALLOWLIST",
                f"commands.{name}.environment",
                "environment must list variable names only",
            )
            environment: tuple[str, ...] = ()
        else:
            environment = tuple(environment_raw)
        unknown_fields = set(raw) - {"argv", "timeout_seconds", "adapter", "environment"}
        for unknown in sorted(unknown_fields):
            _issue(
                errors,
                "UNKNOWN_COMMAND_FIELD",
                f"commands.{name}.{unknown}",
                "unknown command field",
            )
        _validate_command_argv(name, argv, project_type, errors)
        commands[name] = CommandSpec(
            argv=argv,
            timeout_seconds=timeout,
            adapter=adapter,
            environment=environment,
        )
    return commands


def _validate_adapter_requirements(
    value: Any,
    errors: list[ManifestValidationIssue],
) -> tuple[AdapterRequirement, ...]:
    if value is None:
        return ()
    if not _is_sequence(value):
        _issue(
            errors,
            "INVALID_ADAPTER_REQUIREMENTS",
            "adapter_requirements",
            "adapter_requirements must be a list of versioned capability expectations",
        )
        return ()
    requirements: list[AdapterRequirement] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        path = f"adapter_requirements[{index}]"
        if not isinstance(raw, Mapping):
            _issue(errors, "INVALID_ADAPTER_REQUIREMENT", path, "requirement must be a mapping")
            continue
        for field in sorted(
            set(raw) - {"adapter_id", "adapter_version", "contract_version", "capabilities"}
        ):
            _issue(
                errors,
                "UNKNOWN_ADAPTER_REQUIREMENT_FIELD",
                f"{path}.{field}",
                "unknown adapter requirement field",
            )
        adapter_id_raw = raw.get("adapter_id")
        if not isinstance(adapter_id_raw, str) or not _ADAPTER_NAME_PATTERN.fullmatch(
            adapter_id_raw
        ):
            _issue(
                errors,
                "INVALID_ADAPTER_ID",
                f"{path}.adapter_id",
                "adapter_id must be a lowercase stable identifier",
            )
            continue
        adapter_id = adapter_id_raw.casefold()
        if adapter_id in seen:
            _issue(
                errors,
                "DUPLICATE_ADAPTER_REQUIREMENT",
                f"{path}.adapter_id",
                "each adapter may have only one requirement entry",
            )
        seen.add(adapter_id)
        contract_version = raw.get("contract_version")
        if contract_version != ADAPTER_CONTRACT_VERSION:
            _issue(
                errors,
                "ADAPTER_CONTRACT_INCOMPATIBLE",
                f"{path}.contract_version",
                f"contract_version must be {ADAPTER_CONTRACT_VERSION!r}",
            )
            contract_version = str(contract_version or "")
        adapter_version_raw = raw.get("adapter_version")
        if adapter_version_raw is not None and (
            not isinstance(adapter_version_raw, str) or not adapter_version_raw.strip()
        ):
            _issue(
                errors,
                "INVALID_ADAPTER_VERSION",
                f"{path}.adapter_version",
                "adapter_version must be a non-empty string when declared",
            )
            adapter_version: str | None = None
        else:
            adapter_version = adapter_version_raw
        capabilities_raw = raw.get("capabilities")
        if (
            not _is_sequence(capabilities_raw)
            or not capabilities_raw
            or any(
                not isinstance(item, str) or not _ADAPTER_NAME_PATTERN.fullmatch(item)
                for item in capabilities_raw
            )
        ):
            _issue(
                errors,
                "INVALID_ADAPTER_CAPABILITIES",
                f"{path}.capabilities",
                "capabilities must be a non-empty list of lowercase names",
            )
            capabilities: tuple[str, ...] = ()
        else:
            capabilities = tuple(dict.fromkeys(capabilities_raw))
        requirements.append(
            AdapterRequirement(
                adapter_id=adapter_id,
                adapter_version=adapter_version,
                contract_version=contract_version,
                capabilities=capabilities,
            )
        )
    return tuple(requirements)


def validate_manifest_data(
    data: Any,
    *,
    manifest_path: str | Path | None = None,
) -> ManifestValidationResult:
    """Validate already-parsed manifest data and return all useful errors."""

    errors: list[ManifestValidationIssue] = []
    warnings: list[ManifestValidationIssue] = []
    if not isinstance(data, Mapping):
        _issue(errors, "INVALID_DOCUMENT", "$", "manifest root must be a YAML mapping")
        return ManifestValidationResult(errors=tuple(errors))

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in data:
            _issue(errors, "MISSING_FIELD", field, f"required field '{field}' is missing")
    _scan_for_secret_fields(data, "", errors)

    schema_version = str(data.get("schema_version", ""))
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        _issue(
            errors,
            "UNSUPPORTED_SCHEMA_VERSION",
            "schema_version",
            f"schema_version must be {SUPPORTED_SCHEMA_VERSION!r}",
        )
    contract_version_raw = data.get("contract_version", MANIFEST_CONTRACT_VERSION)
    if contract_version_raw != MANIFEST_CONTRACT_VERSION:
        _issue(
            errors,
            "UNSUPPORTED_MANIFEST_CONTRACT",
            "contract_version",
            f"contract_version must be {MANIFEST_CONTRACT_VERSION!r}",
        )
    contract_version = str(contract_version_raw)

    project_id = _validate_string(data, "project_id", errors)
    if project_id and not _PROJECT_ID_PATTERN.fullmatch(project_id):
        _issue(
            errors,
            "INVALID_PROJECT_ID",
            "project_id",
            "project_id must be lowercase, filesystem-safe, and contain only letters, digits, hyphens, or underscores",
        )
    name = _validate_string(data, "name", errors)
    description = _validate_string(data, "description", errors)
    project_type = _validate_string(data, "project_type", errors).casefold()
    if project_type and not _ADAPTER_NAME_PATTERN.fullmatch(project_type):
        _issue(
            errors,
            "INVALID_PROJECT_TYPE",
            "project_type",
            "project_type must be a lowercase stable runtime-family identifier",
        )

    resolved_manifest_path = Path(manifest_path).expanduser().resolve() if manifest_path else None
    sources_raw = data.get("sources")
    local_path = Path.cwd().resolve()
    github_repository: str | None = None
    if not isinstance(sources_raw, Mapping):
        _issue(errors, "INVALID_TYPE", "sources", "sources must be a mapping")
    else:
        local_raw = sources_raw.get("local_path")
        if not isinstance(local_raw, str) or not local_raw.strip() or "\x00" in local_raw:
            _issue(
                errors,
                "INVALID_LOCAL_PATH",
                "sources.local_path",
                "local_path must be a non-empty path string",
            )
        elif "://" in local_raw:
            _issue(
                errors,
                "INVALID_LOCAL_PATH",
                "sources.local_path",
                "local_path must be a filesystem path, not a URL",
            )
        else:
            local_candidate = Path(local_raw).expanduser()
            if not local_candidate.is_absolute():
                base = resolved_manifest_path.parent if resolved_manifest_path else Path.cwd()
                local_candidate = base / local_candidate
            local_path = local_candidate.resolve()
            if resolved_manifest_path is not None:
                if not local_path.exists():
                    _issue(
                        errors,
                        "SOURCE_PATH_NOT_FOUND",
                        "sources.local_path",
                        "registered source directory does not exist",
                    )
                elif not local_path.is_dir():
                    _issue(
                        errors,
                        "SOURCE_PATH_NOT_DIRECTORY",
                        "sources.local_path",
                        "registered source path is not a directory",
                    )
                try:
                    resolved_manifest_path.relative_to(local_path)
                except ValueError:
                    _issue(
                        errors,
                        "MANIFEST_OUTSIDE_SOURCE",
                        "sources.local_path",
                        "source directory must contain the manifest",
                    )
        github_raw = sources_raw.get("github_repository")
        if github_raw is not None and (not isinstance(github_raw, str) or not github_raw.strip()):
            _issue(
                errors,
                "INVALID_GITHUB_REPOSITORY",
                "sources.github_repository",
                "github_repository must be null or a non-empty URL",
            )
        elif isinstance(github_raw, str):
            github_repository = github_raw.strip()

    stack_raw = data.get("stack")
    if not isinstance(stack_raw, Mapping):
        _issue(errors, "INVALID_TYPE", "stack", "stack must be a mapping")
        stack: Mapping[str, Any] = {}
    else:
        stack = dict(stack_raw)

    important_paths = _validate_relative_paths(
        data.get("important_paths"), "important_paths", errors
    )
    memory_files = _validate_relative_paths(data.get("memory_files"), "memory_files", errors)
    protected_paths = _validate_relative_paths(
        data.get("protected_paths"), "protected_paths", errors
    )

    entrypoints_raw = data.get("entrypoints")
    entrypoints: dict[str, str] = {}
    if not isinstance(entrypoints_raw, Mapping):
        _issue(
            errors,
            "INVALID_TYPE",
            "entrypoints",
            "entrypoints must be a mapping of roles to relative paths",
        )
    else:
        for role, raw_path in entrypoints_raw.items():
            if not isinstance(role, str) or not role:
                _issue(
                    errors,
                    "INVALID_ENTRYPOINT",
                    "entrypoints",
                    "entrypoint roles must be non-empty strings",
                )
                continue
            normalized = _normalize_relative_path(raw_path)
            if normalized is None:
                _issue(
                    errors,
                    "UNSAFE_RELATIVE_PATH",
                    f"entrypoints.{role}",
                    "entrypoint must be project-relative",
                )
            else:
                entrypoints[role] = normalized

    state_raw = data.get("state_file")
    state_file: str | None = None
    if state_raw is not None:
        state_file = _normalize_relative_path(state_raw)
        if state_file is None:
            _issue(
                errors,
                "UNSAFE_RELATIVE_PATH",
                "state_file",
                "state_file must be null or project-relative",
            )

    runtime_raw = data.get("runtime_adapters")
    runtime_adapters: tuple[str, ...] = ()
    if (
        not _is_sequence(runtime_raw)
        or not runtime_raw
        or any(not isinstance(item, str) or not item for item in runtime_raw)
    ):
        _issue(
            errors,
            "INVALID_RUNTIME_ADAPTERS",
            "runtime_adapters",
            "runtime_adapters must be a non-empty list of names",
        )
    else:
        runtime_adapters = tuple(dict.fromkeys(item.casefold() for item in runtime_raw))
        for index, adapter in enumerate(runtime_adapters):
            if not _ADAPTER_NAME_PATTERN.fullmatch(adapter):
                _issue(
                    errors,
                    "INVALID_RUNTIME_ADAPTER",
                    f"runtime_adapters[{index}]",
                    "runtime adapter must be a lowercase stable identifier",
                )

    commands = _validate_commands(data.get("commands"), project_type, runtime_adapters, errors)
    adapter_requirements = _validate_adapter_requirements(
        data.get("adapter_requirements"), errors
    )

    permissions_raw = data.get("permissions")
    permission_values: dict[str, bool] = {}
    if not isinstance(permissions_raw, Mapping):
        _issue(errors, "INVALID_TYPE", "permissions", "permissions must be a mapping")
    else:
        for permission in ("read", "workspace_write", "validation", "git_publish"):
            raw_value = permissions_raw.get(permission)
            if not isinstance(raw_value, bool):
                _issue(
                    errors,
                    "INVALID_PERMISSION",
                    f"permissions.{permission}",
                    "permission must be true or false",
                )
                permission_values[permission] = False
            else:
                permission_values[permission] = raw_value
        for unknown in sorted(
            set(permissions_raw) - {"read", "workspace_write", "validation", "git_publish"}
        ):
            _issue(
                errors,
                "UNKNOWN_PERMISSION",
                f"permissions.{unknown}",
                "unknown permission cannot expand Gateway authority",
            )
    permissions = ProjectPermissions(
        read=permission_values.get("read", False),
        workspace_write=permission_values.get("workspace_write", False),
        validation=permission_values.get("validation", False),
        git_publish=permission_values.get("git_publish", False),
    )

    validation_raw = data.get("validation_requirements")
    validation_requirements: tuple[str, ...] = ()
    if not _is_sequence(validation_raw) or any(
        not isinstance(item, str) for item in validation_raw
    ):
        _issue(
            errors,
            "INVALID_VALIDATION_REQUIREMENTS",
            "validation_requirements",
            "validation_requirements must list action names",
        )
    else:
        validation_requirements = tuple(dict.fromkeys(validation_raw))
        for index, action in enumerate(validation_requirements):
            if action not in COMMAND_NAMES or action == "install":
                _issue(
                    errors,
                    "INVALID_VALIDATION_ACTION",
                    f"validation_requirements[{index}]",
                    "validation action is not supported",
                )
            elif commands.get(action) is None:
                _issue(
                    errors,
                    "MISSING_VALIDATION_COMMAND",
                    f"validation_requirements[{index}]",
                    f"required validation action {action!r} has no command",
                )
    if validation_requirements and not permissions.validation:
        _issue(
            errors,
            "VALIDATION_PERMISSION_REQUIRED",
            "permissions.validation",
            "mandatory validation requires validation permission",
        )

    publication_raw = data.get("publication_policy")
    publication_policy: dict[str, bool] = {}
    publication_fields = ("allow_local_branch", "allow_push", "allow_merge")
    if not isinstance(publication_raw, Mapping):
        _issue(errors, "INVALID_TYPE", "publication_policy", "publication_policy must be a mapping")
    else:
        for field in publication_fields:
            raw_value = publication_raw.get(field)
            if not isinstance(raw_value, bool):
                _issue(
                    errors,
                    "INVALID_PUBLICATION_POLICY",
                    f"publication_policy.{field}",
                    "publication policy must be true or false",
                )
                publication_policy[field] = False
            else:
                publication_policy[field] = raw_value
        for unknown in sorted(set(publication_raw) - set(publication_fields)):
            code = (
                "PROHIBITED_PUBLICATION_POLICY"
                if unknown in {"allow_force_push", "allow_deploy", "allow_production"}
                else "UNKNOWN_PUBLICATION_POLICY"
            )
            _issue(
                errors,
                code,
                f"publication_policy.{unknown}",
                "unknown or globally prohibited publication authority is not supported",
            )
        if publication_policy.get("allow_merge"):
            _issue(
                errors,
                "PROHIBITED_PUBLICATION_POLICY",
                "publication_policy.allow_merge",
                "merge is globally prohibited in this MVP",
            )
        if (
            publication_policy.get("allow_local_branch") or publication_policy.get("allow_push")
        ) and not permissions.git_publish:
            _issue(
                errors,
                "GIT_PERMISSION_REQUIRED",
                "permissions.git_publish",
                "publication policy requires git_publish permission",
            )

    protected_prefixes = tuple(path.rstrip("/") for path in protected_paths)
    for field, paths in (
        ("important_paths", important_paths),
        ("memory_files", memory_files),
        ("entrypoints", tuple(entrypoints.values())),
    ):
        for path in paths:
            if any(
                path == protected or path.startswith(f"{protected}/")
                for protected in protected_prefixes
            ):
                _issue(
                    errors,
                    "PROTECTED_PATH_CONFLICT",
                    field,
                    f"declared context path {path!r} is protected",
                )
    if state_file and any(
        state_file == protected or state_file.startswith(f"{protected}/")
        for protected in protected_prefixes
    ):
        _issue(errors, "PROTECTED_PATH_CONFLICT", "state_file", "state_file is protected")

    if errors:
        return ManifestValidationResult(errors=tuple(errors), warnings=tuple(warnings))

    manifest = ProjectManifest(
        schema_version=schema_version,
        contract_version=contract_version,
        project_id=project_id,
        name=name,
        description=description,
        project_type=project_type,
        sources=ProjectSources(local_path=local_path, github_repository=github_repository),
        stack=stack,
        important_paths=important_paths,
        entrypoints=entrypoints,
        memory_files=memory_files,
        commands=commands,
        permissions=permissions,
        protected_paths=protected_paths,
        validation_requirements=validation_requirements,
        publication_policy=publication_policy,
        runtime_adapters=runtime_adapters,
        state_file=state_file,
        adapter_requirements=adapter_requirements,
        manifest_path=resolved_manifest_path,
    )
    from .runtime.registry import built_in_adapter_registry

    compatibility_issues = built_in_adapter_registry().validate_manifest(manifest)
    if compatibility_issues:
        return ManifestValidationResult(
            errors=tuple(
                ManifestValidationIssue(issue.code, issue.path, issue.message)
                for issue in compatibility_issues
            ),
            warnings=tuple(warnings),
        )
    return ManifestValidationResult(errors=(), warnings=tuple(warnings), manifest=manifest)


def _read_yaml(path: Path) -> tuple[Any | None, ManifestValidationIssue | None]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        return None, ManifestValidationIssue(
            "MANIFEST_NOT_FOUND", "$", f"cannot read manifest: {exc}"
        )
    if size > MAX_MANIFEST_BYTES:
        return None, ManifestValidationIssue(
            "MANIFEST_TOO_LARGE", "$", f"manifest exceeds {MAX_MANIFEST_BYTES} bytes"
        )
    try:
        text = path.read_text(encoding="utf-8-sig")
        return yaml.load(text, Loader=_UniqueKeyLoader), None
    except UnicodeError as exc:
        return None, ManifestValidationIssue(
            "MANIFEST_NOT_UTF8", "$", f"manifest must be UTF-8: {exc}"
        )
    except (OSError, yaml.YAMLError) as exc:
        return None, ManifestValidationIssue(
            "INVALID_YAML", "$", f"cannot parse manifest YAML: {exc}"
        )


class ManifestLoader:
    """Side-effect-free manifest loader and validator."""

    def validate(self, source: str | Path | Mapping[str, Any]) -> ManifestValidationResult:
        if isinstance(source, Mapping):
            return validate_manifest_data(source)
        path = Path(source).expanduser().resolve()
        data, parse_error = _read_yaml(path)
        if parse_error is not None:
            return ManifestValidationResult(errors=(parse_error,))
        return validate_manifest_data(data, manifest_path=path)

    def load(self, path: str | Path) -> ProjectManifest:
        result = self.validate(path)
        if not result.valid or result.manifest is None:
            raise ManifestValidationError(result.errors)
        return result.manifest


def validate_manifest(source: str | Path | Mapping[str, Any]) -> ManifestValidationResult:
    return ManifestLoader().validate(source)


def load_manifest(path: str | Path) -> ProjectManifest:
    return ManifestLoader().load(path)
