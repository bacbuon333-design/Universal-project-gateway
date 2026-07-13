"""Deterministic, deliberately modest natural-language intent normalization."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import PurePosixPath

from .models import (
    GatewayError,
    NormalizedIntent,
    PublicationMode,
    RiskLevel,
    unique_strings,
)


class InvalidIntentError(GatewayError):
    default_code = "INVALID_INTENT"


_ABSOLUTE_WINDOWS_PATH = re.compile(r"^[A-Za-z]:[/\\]")

_PROHIBITED_PATTERNS = (
    r"\bdelete\b",
    r"\bremove\b",
    r"\bdestroy\b",
    r"\bdeploy(?:ment)?\b",
    r"\bproduction\b",
    r"\bmerge\b",
    r"\bforce[ -]?push\b",
    r"\bcredential(?:s)?\b",
    r"\bsecret(?:s)?\b",
    r"\bdirect(?:ly)?\s+(?:edit|modify|write).{0,20}\bsource\b",
)
_PUBLICATION_PATTERNS = (
    r"\bcommit\b",
    r"\bcreate.{0,15}\bbranch\b",
    r"\bpublish\b",
    r"\bpush\b",
)
_VALIDATION_PATTERNS = (
    r"\brun.{0,10}\btests?\b",
    r"\btest\b",
    r"\blint\b",
    r"\bvalidate\b",
    r"\bverification\b",
    r"\bbuild\b",
    r"\bsmoke[ -]?test\b",
    r"\bcompile\b",
)
_WRITE_PATTERNS = (
    r"\badd\b",
    r"\bchange\b",
    r"\bcreate\b",
    r"\bedit\b",
    r"\bfix\b",
    r"\bimplement\b",
    r"\bmodify\b",
    r"\bmove\b",
    r"\bpatch\b",
    r"\brefactor\b",
    r"\brename\b",
    r"\breplace\b",
    r"\bupdate\b",
    r"\bwrite\b",
)
_READ_PATTERNS = (
    r"\bdescribe\b",
    r"\bdiff\b",
    r"\bexamine\b",
    r"\bfind\b",
    r"\binspect\b",
    r"\blist\b",
    r"\bread\b",
    r"\breview\b",
    r"\bsearch\b",
    r"\bshow\b",
    r"\bsummarize\b",
)

_EXPLICIT_OPERATIONS = {
    "inspect": ("inspection", "read_files", RiskLevel.R0),
    "read": ("inspection", "read_files", RiskLevel.R0),
    "search": ("inspection", "read_files", RiskLevel.R0),
    "list": ("inspection", "read_files", RiskLevel.R0),
    "diff": ("inspection", "read_files", RiskLevel.R0),
    "create": ("modification", "write_files", RiskLevel.R1),
    "edit": ("modification", "write_files", RiskLevel.R1),
    "modify": ("modification", "write_files", RiskLevel.R1),
    "move": ("modification", "write_files", RiskLevel.R1),
    "patch": ("modification", "write_files", RiskLevel.R1),
    "replace": ("modification", "write_files", RiskLevel.R1),
    "update": ("modification", "write_files", RiskLevel.R1),
    "write": ("modification", "write_files", RiskLevel.R1),
    "build": ("validation", "run_validation", RiskLevel.R2),
    "install": ("validation", "run_validation", RiskLevel.R2),
    "lint": ("validation", "run_validation", RiskLevel.R2),
    "smoke_test": ("validation", "run_validation", RiskLevel.R2),
    "test": ("validation", "run_validation", RiskLevel.R2),
    "validate": ("validation", "run_validation", RiskLevel.R2),
    "commit": ("publication", "publish_local_commit", RiskLevel.R3),
    "create_branch": ("publication", "publish_local_commit", RiskLevel.R3),
    "publish": ("publication", "publish_local_commit", RiskLevel.R3),
    "push": ("publication", "push", RiskLevel.R3),
    "delete": ("prohibited", "destructive_action", RiskLevel.R4),
    "deploy": ("prohibited", "destructive_action", RiskLevel.R4),
    "force_push": ("prohibited", "destructive_action", RiskLevel.R4),
    "merge": ("prohibited", "destructive_action", RiskLevel.R4),
}


def _matches_any(text: str, patterns: Sequence[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _normalize_target(path: str) -> str:
    candidate = path.strip().replace("\\", "/")
    if (
        not candidate
        or candidate.startswith("/")
        or candidate.startswith("//")
        or _ABSOLUTE_WINDOWS_PATH.match(candidate)
    ):
        raise InvalidIntentError(
            "target paths must be non-empty and workspace-relative",
            code="UNSAFE_TARGET_PATH",
            details={"path": path},
        )
    normalized = PurePosixPath(candidate)
    if any(part in {"", ".", ".."} for part in normalized.parts):
        raise InvalidIntentError(
            "target paths may not contain traversal components",
            code="UNSAFE_TARGET_PATH",
            details={"path": path},
        )
    return normalized.as_posix()


def _publication_mode(value: str | PublicationMode | None) -> PublicationMode:
    if value is None:
        return PublicationMode.NONE
    if isinstance(value, PublicationMode):
        return value
    aliases = {
        "": PublicationMode.NONE,
        "none": PublicationMode.NONE,
        "no": PublicationMode.NONE,
        "local": PublicationMode.LOCAL_COMMIT,
        "local_branch": PublicationMode.LOCAL_COMMIT,
        "local_commit": PublicationMode.LOCAL_COMMIT,
        "commit": PublicationMode.LOCAL_COMMIT,
        "push": PublicationMode.PUSH,
    }
    try:
        return aliases[value.strip().casefold()]
    except (AttributeError, KeyError) as exc:
        raise InvalidIntentError(
            "publication preference must be none, local_commit, or push",
            code="INVALID_PUBLICATION_MODE",
        ) from exc


class IntentCompiler:
    """Compile a bounded intent without pretending to understand open-ended work."""

    def compile(
        self,
        project_id: str,
        task: str | None = None,
        target_paths: Sequence[str] | None = None,
        requested_operation: str | None = None,
        publication_preference: str | PublicationMode | None = "none",
        required_validation: Sequence[str] | None = None,
        *,
        natural_language_task: str | None = None,
        request: str | None = None,
    ) -> NormalizedIntent:
        if not isinstance(project_id, str) or not project_id.strip():
            raise InvalidIntentError("project_id must be a non-empty string")
        supplied_tasks = [
            value for value in (task, natural_language_task, request) if value is not None
        ]
        if len(supplied_tasks) > 1 and any(
            value != supplied_tasks[0] for value in supplied_tasks[1:]
        ):
            raise InvalidIntentError("provide only one task/request value")
        task_text = supplied_tasks[0] if supplied_tasks else None
        if not isinstance(task_text, str) or not task_text.strip():
            raise InvalidIntentError("natural-language task must be a non-empty string")
        if target_paths is None:
            normalized_targets: tuple[str, ...] = ()
        elif isinstance(target_paths, (str, bytes)):
            raise InvalidIntentError("target_paths must be a sequence of relative path strings")
        else:
            normalized_list: list[str] = []
            for target in target_paths:
                if not isinstance(target, str):
                    raise InvalidIntentError("every target path must be a string")
                normalized_list.append(_normalize_target(target))
            normalized_targets = unique_strings(normalized_list)
        if required_validation is None:
            validations: tuple[str, ...] = ()
        elif isinstance(required_validation, (str, bytes)) or any(
            not isinstance(action, str) or not action for action in required_validation
        ):
            raise InvalidIntentError("required_validation must list action names")
        else:
            validations = unique_strings(required_validation)

        mode = _publication_mode(publication_preference)
        task_type: str | None = None
        operations: list[str] = []
        levels: list[RiskLevel] = []

        if requested_operation is not None:
            if not isinstance(requested_operation, str) or not requested_operation.strip():
                raise InvalidIntentError("requested_operation must be a non-empty action name")
            operation_key = (
                requested_operation.strip().casefold().replace("-", "_").replace(" ", "_")
            )
            explicit = _EXPLICIT_OPERATIONS.get(operation_key)
            if explicit is None:
                raise InvalidIntentError(
                    f"requested operation {requested_operation!r} is not recognized",
                    code="UNKNOWN_REQUESTED_OPERATION",
                )
            task_type, operation, level = explicit
            operations.append(operation)
            levels.append(level)

        lowered = task_text.casefold()
        prohibited = _matches_any(lowered, _PROHIBITED_PATTERNS)
        publication = _matches_any(lowered, _PUBLICATION_PATTERNS)
        validation = _matches_any(lowered, _VALIDATION_PATTERNS)
        write = _matches_any(lowered, _WRITE_PATTERNS)
        read = _matches_any(lowered, _READ_PATTERNS)

        if prohibited:
            task_type = "prohibited"
            operations.append("destructive_action")
            levels.append(RiskLevel.R4)
        else:
            if read or write:
                operations.append("read_files")
                levels.append(RiskLevel.R0)
            if write:
                task_type = "modification"
                operations.append("write_files")
                levels.append(RiskLevel.R1)
            elif validation and task_type is None:
                task_type = "validation"
            elif read and task_type is None:
                task_type = "inspection"
            if validation:
                operations.append("run_validation")
                levels.append(RiskLevel.R2)
            if publication:
                operations.append("publish_local_commit")
                levels.append(RiskLevel.R3)
                if task_type is None:
                    task_type = "publication"

        if mode is PublicationMode.LOCAL_COMMIT:
            operations.append("publish_local_commit")
            levels.append(RiskLevel.R3)
        elif mode is PublicationMode.PUSH:
            operations.append("push")
            levels.append(RiskLevel.R3)

        requires_ai_planning = task_type is None
        if task_type is None:
            task_type = "unknown"
            levels.append(RiskLevel.R0)
        operation_order = (
            "read_files",
            "write_files",
            "run_validation",
            "publish_local_commit",
            "push",
            "destructive_action",
        )
        unique_operations = set(operations)
        return NormalizedIntent(
            project_id=project_id.strip(),
            task_type=task_type,
            target_scope=normalized_targets,
            expected_operations=tuple(
                operation for operation in operation_order if operation in unique_operations
            ),
            risk_level=RiskLevel.highest(*levels),
            required_validation=validations,
            publication_mode=mode,
            requires_ai_planning=requires_ai_planning,
        )


def compile_intent(
    project_id: str,
    task: str,
    target_paths: Sequence[str] | None = None,
    requested_operation: str | None = None,
    publication_preference: str | PublicationMode | None = "none",
    required_validation: Sequence[str] | None = None,
) -> NormalizedIntent:
    return IntentCompiler().compile(
        project_id,
        task,
        target_paths,
        requested_operation,
        publication_preference,
        required_validation,
    )
