"""Checksummed compatibility evidence plus an additive canonical hash chain."""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any

from .evidence_chain import (
    ATTESTATION_FILE,
    CHAIN_FILE,
    EVIDENCE_SCHEMA_VERSION,
    GENESIS_EVENT_HASH,
    HASH_ALGORITHM,
    EvidenceChainError,
    canonical_json,
    compatibility_manifest_checksum,
    create_event,
    verify_event_records,
)
from .models import GatewayError, utc_now
from .scoped_fs import is_reparse_point

COMPATIBILITY_EVIDENCE_FILES = (
    "task.json",
    "intent.json",
    "context_pack.json",
    "source_snapshot.json",
    "operations.json",
    "files_changed.json",
    "patch.diff",
    "validation.json",
    "stdout.log",
    "stderr.log",
    "environment.json",
    "final_report.json",
)
CHAIN_EVIDENCE_FILES = (CHAIN_FILE, ATTESTATION_FILE)
# Preserve the v1 public constant for consumers that expect exactly 12 files.
EVIDENCE_FILES = COMPATIBILITY_EVIDENCE_FILES
ALL_EVIDENCE_FILES = (*COMPATIBILITY_EVIDENCE_FILES, *CHAIN_EVIDENCE_FILES)
CHECKSUM_FILE = "manifest.sha256.json"
_SAFE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_WINDOWS_RESERVED_JOB_IDS = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}
_SECRET_KEY = re.compile(
    r"(?:^|[_-])(password|passwd|secret|token|api[_-]?key|authorization|cookie|private[_-]?key)(?:$|[_-])",
    re.IGNORECASE,
)
_LABELED_SECRET = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key|authorization)\b(\s*[:=]\s*)([^\s,;]+)"
)
_BEARER = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*")
_URL_CREDENTIAL = re.compile(r"(?i)(https?://)([^/@\s:]+):([^/@\s]+)@")
_TOKEN_SHAPES = re.compile(
    r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"
)


class EvidenceError(GatewayError):
    default_code = "EVIDENCE_ERROR"


@dataclass(frozen=True, slots=True)
class EvidenceVerification:
    valid: bool
    evidence_path: Path
    checked_files: int
    errors: tuple[dict[str, str], ...] = ()
    chain_checked: bool = False
    checked_events: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "evidence_path": str(self.evidence_path),
            "checked_files": self.checked_files,
            "errors": list(self.errors),
            "chain_checked": self.chain_checked,
            "checked_events": self.checked_events,
        }

    def __bool__(self) -> bool:
        return self.valid


class EvidenceLedger:
    """Create and verify one evidence directory per job."""

    def __init__(self, artifacts_root: str | os.PathLike[str]) -> None:
        self.root = Path(artifacts_root).expanduser().resolve()

    @staticmethod
    def _validate_job_id(job_id: str) -> str:
        if (
            not isinstance(job_id, str)
            or not _SAFE_JOB_ID.fullmatch(job_id)
            or job_id in {".", ".."}
            or job_id.endswith(".")
            or ".." in job_id
            or job_id.split(".", 1)[0].upper() in _WINDOWS_RESERVED_JOB_IDS
        ):
            raise EvidenceError(
                "job_id must be a filesystem-safe identifier",
                code="INVALID_JOB_ID",
                details={"job_id": str(job_id)},
            )
        return job_id

    def job_path(self, job_id: str) -> Path:
        safe_id = self._validate_job_id(job_id)
        candidate = self.root / safe_id
        if candidate.resolve(strict=False).parent != self.root:
            raise EvidenceError("evidence path escaped artifact root", code="EVIDENCE_PATH_ESCAPE")
        return candidate

    def initialize(self, job_id: str, **initial_documents: Any) -> Path:
        job_path = self.job_path(job_id)
        if job_path.exists() and any(job_path.iterdir()):
            raise EvidenceError(
                "evidence already exists for this job",
                code="EVIDENCE_ALREADY_EXISTS",
                details={"job_id": job_id},
            )
        job_path.mkdir(parents=True, exist_ok=True)
        aliases = {
            "task": "task.json",
            "intent": "intent.json",
            "context_pack": "context_pack.json",
            "source_snapshot": "source_snapshot.json",
            "operations": "operations.json",
            "files_changed": "files_changed.json",
            "patch": "patch.diff",
            "validation": "validation.json",
            "stdout": "stdout.log",
            "stderr": "stderr.log",
            "environment": "environment.json",
            "final_report": "final_report.json",
        }
        for name, value in initial_documents.items():
            filename = aliases.get(name, name)
            self.write(job_id, filename, value)
        return job_path

    def write(self, job_id: str, name: str, data: Any) -> Path:
        if name not in COMPATIBILITY_EVIDENCE_FILES:
            raise EvidenceError(
                "evidence filename is not allowlisted",
                code="EVIDENCE_FILE_FORBIDDEN",
                details={"name": name},
            )
        job_path = self.job_path(job_id)
        job_path.mkdir(parents=True, exist_ok=True)
        if is_reparse_point(job_path):
            raise EvidenceError("evidence directory may not be a link", code="EVIDENCE_LINK_FORBIDDEN")
        destination = job_path / name
        if destination.exists() and is_reparse_point(destination):
            raise EvidenceError("evidence file may not be a link", code="EVIDENCE_LINK_FORBIDDEN")

        if name.endswith(".json"):
            value = redact(_plain(data))
            content = json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        else:
            if isinstance(data, bytes):
                try:
                    text = data.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise EvidenceError(
                        "evidence logs and patches must be UTF-8 text",
                        code="BINARY_EVIDENCE_FORBIDDEN",
                    ) from exc
            elif isinstance(data, str):
                text = data
            else:
                text = json.dumps(_plain(data), sort_keys=True, ensure_ascii=False)
            content = redact_text(text)
            if content and not content.endswith("\n"):
                content += "\n"
        _write_text_atomic(destination, content)
        return destination

    write_json = write

    def append_event(
        self,
        job_id: str,
        project_id: str,
        event_type: str,
        payload: Mapping[str, Any] | None = None,
        *,
        actor: str,
        timestamp: str | None = None,
    ) -> dict[str, Any]:
        """Append one canonical event without rewriting existing chain bytes."""

        job_path = self.job_path(job_id)
        job_path.mkdir(parents=True, exist_ok=True)
        if is_reparse_point(job_path):
            raise EvidenceError("evidence directory may not be a link", code="EVIDENCE_LINK_FORBIDDEN")
        chain_path = job_path / CHAIN_FILE
        if chain_path.exists() and is_reparse_point(chain_path):
            raise EvidenceError("evidence chain may not be a link", code="EVIDENCE_LINK_FORBIDDEN")

        events = _read_event_chain(chain_path)
        existing_errors = verify_event_records(events) if events else []
        if existing_errors:
            raise EvidenceError(
                "cannot append to an invalid evidence event chain",
                code="EVIDENCE_CHAIN_INVALID",
                details={"errors": existing_errors},
            )
        if events and (
            events[0].get("job_id") != job_id or events[0].get("project_id") != project_id
        ):
            raise EvidenceError(
                "evidence event identity does not match the existing chain",
                code="EVIDENCE_EVENT_IDENTITY_MISMATCH",
                details={"job_id": job_id, "project_id": project_id},
            )
        previous_hash = events[-1]["event_hash"] if events else GENESIS_EVENT_HASH
        safe_payload = redact(_plain(dict(payload or {})))
        try:
            event = create_event(
                sequence=len(events) + 1,
                event_type=event_type,
                timestamp=timestamp or utc_now(),
                job_id=job_id,
                project_id=project_id,
                actor=actor,
                previous_event_hash=previous_hash,
                payload=safe_payload,
            )
        except EvidenceChainError as exc:
            raise EvidenceError(
                str(exc),
                code="EVIDENCE_EVENT_INVALID",
                details={"event_type": event_type},
            ) from exc

        # These files are derived snapshots. Removing them permits a later
        # append (for example local publication) while the JSONL itself remains
        # byte-for-byte append-only.
        (job_path / CHECKSUM_FILE).unlink(missing_ok=True)
        (job_path / ATTESTATION_FILE).unlink(missing_ok=True)
        _append_text_durable(chain_path, canonical_json(event) + "\n")
        return event

    def record_operation(self, job_id: str, operation: Mapping[str, Any]) -> Path:
        path = self.job_path(job_id) / "operations.json"
        operations: list[Any] = []
        if path.is_file():
            try:
                current = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(current, list):
                    operations = current
            except json.JSONDecodeError as exc:
                raise EvidenceError(
                    "operations ledger is not valid JSON",
                    code="EVIDENCE_INVALID",
                ) from exc
        operations.append(dict(operation))
        return self.write(job_id, "operations.json", operations)

    def finalize(
        self,
        job_id: str,
        final_report: Mapping[str, Any] | None = None,
    ) -> Path:
        job_path = self.job_path(job_id)
        job_path.mkdir(parents=True, exist_ok=True)
        checksum_path = job_path / CHECKSUM_FILE
        checksum_path.unlink(missing_ok=True)
        (job_path / ATTESTATION_FILE).unlink(missing_ok=True)
        if final_report is not None:
            self.write(job_id, "final_report.json", final_report)

        defaults: dict[str, Any] = {
            "task.json": {},
            "intent.json": {},
            "context_pack.json": {},
            "source_snapshot.json": {},
            "operations.json": [],
            "files_changed.json": [],
            "patch.diff": "",
            "validation.json": {
                "overall_status": "not_run",
                "checks": [],
                "summary": {"passed": 0, "failed": 0, "skipped": 0, "not_run": 0},
            },
            "stdout.log": "",
            "stderr.log": "",
            "environment.json": {},
            "final_report.json": {"status": "not_run", "success": False},
        }
        for filename in COMPATIBILITY_EVIDENCE_FILES:
            if not (job_path / filename).is_file():
                self.write(job_id, filename, defaults[filename])

        final_report_document = _read_json_mapping(job_path / "final_report.json")
        project_id = _infer_project_id(job_path, final_report_document)
        generated_at = utc_now()
        final_event = self.append_event(
            job_id,
            project_id,
            "evidence_finalized",
            {
                "status": final_report_document.get("status", "unknown"),
                "success": bool(final_report_document.get("success", False)),
                "compatibility_file_count": len(COMPATIBILITY_EVIDENCE_FILES),
            },
            actor="evidence_ledger",
            timestamp=generated_at,
        )

        compatibility_checksums = {
            filename: _sha256(job_path / filename)
            for filename in COMPATIBILITY_EVIDENCE_FILES
        }
        attestation = _build_attestation(
            job_path,
            job_id=job_id,
            project_id=project_id,
            final_event_hash=str(final_event["event_hash"]),
            manifest_checksum=compatibility_manifest_checksum(compatibility_checksums),
            generated_at=generated_at,
        )
        _write_text_atomic(
            job_path / ATTESTATION_FILE,
            json.dumps(attestation, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        )

        checksums: dict[str, str] = {}
        for path in _evidence_files(job_path):
            relative = path.relative_to(job_path).as_posix()
            if relative == CHECKSUM_FILE:
                continue
            checksums[relative] = _sha256(path)
        manifest = {
            "algorithm": HASH_ALGORITHM,
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "files": dict(sorted(checksums.items())),
        }
        _write_text_atomic(
            checksum_path,
            json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n",
        )
        return checksum_path

    create_checksums = finalize

    def verify(self, job_id_or_path: str | os.PathLike[str]) -> EvidenceVerification:
        supplied = Path(job_id_or_path)
        if supplied.is_dir():
            evidence_path = supplied.expanduser().resolve(strict=True)
        else:
            evidence_path = self.job_path(os.fspath(job_id_or_path))
        errors: list[dict[str, str]] = []
        manifest_path = evidence_path / CHECKSUM_FILE
        if not manifest_path.is_file():
            return EvidenceVerification(
                False,
                evidence_path,
                0,
                ({"code": "CHECKSUM_MANIFEST_MISSING", "path": CHECKSUM_FILE},),
            )
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return EvidenceVerification(
                False,
                evidence_path,
                0,
                ({"code": "CHECKSUM_MANIFEST_INVALID", "path": CHECKSUM_FILE},),
            )
        expected = manifest.get("files") if isinstance(manifest, Mapping) else None
        if (
            not isinstance(manifest, Mapping)
            or manifest.get("algorithm") != "sha256"
            or not isinstance(expected, Mapping)
        ):
            return EvidenceVerification(
                False,
                evidence_path,
                0,
                ({"code": "CHECKSUM_MANIFEST_INVALID", "path": CHECKSUM_FILE},),
            )

        actual_names = {
            path.relative_to(evidence_path).as_posix()
            for path in _evidence_files(evidence_path)
            if path.name != CHECKSUM_FILE
        }
        expected_names = {str(name) for name in expected}
        for missing in sorted(expected_names - actual_names):
            errors.append({"code": "EVIDENCE_FILE_MISSING", "path": missing})
        for unexpected in sorted(actual_names - expected_names):
            errors.append({"code": "EVIDENCE_FILE_UNCHECKSUMMED", "path": unexpected})

        checked = 0
        for relative, expected_digest in sorted(expected.items(), key=lambda item: str(item[0])):
            relative_text = str(relative).replace("\\", "/")
            pure = PurePosixPath(relative_text)
            if pure.is_absolute() or ".." in pure.parts or relative_text == CHECKSUM_FILE:
                errors.append({"code": "CHECKSUM_PATH_INVALID", "path": relative_text})
                continue
            path = evidence_path.joinpath(*pure.parts)
            resolved = path.resolve(strict=False)
            if resolved != evidence_path and evidence_path not in resolved.parents:
                errors.append({"code": "CHECKSUM_PATH_ESCAPE", "path": relative_text})
                continue
            if not path.is_file() or is_reparse_point(path):
                continue
            checked += 1
            if not isinstance(expected_digest, str) or _sha256(path) != expected_digest:
                errors.append({"code": "CHECKSUM_MISMATCH", "path": relative_text})
        chain_checked = False
        checked_events = 0
        chain_path = evidence_path / CHAIN_FILE
        attestation_path = evidence_path / ATTESTATION_FILE
        if chain_path.exists() != attestation_path.exists():
            errors.append({"code": "EVIDENCE_CHAIN_INCOMPLETE", "path": CHAIN_FILE})
        elif chain_path.is_file() and attestation_path.is_file():
            chain_checked = True
            events = _read_event_chain(chain_path, errors=errors)
            checked_events = len(events)
            errors.extend(verify_event_records(events))
            attestation = _read_json_mapping(attestation_path, errors=errors)
            errors.extend(
                _verify_attestation(
                    attestation,
                    events,
                    expected,
                    evidence_path=evidence_path,
                )
            )
        return EvidenceVerification(
            not errors,
            evidence_path,
            checked,
            tuple(errors),
            chain_checked,
            checked_events,
        )

    verify_checksums = verify


def _build_attestation(
    job_path: Path,
    *,
    job_id: str,
    project_id: str,
    final_event_hash: str,
    manifest_checksum: str,
    generated_at: str,
) -> dict[str, Any]:
    from . import __version__

    snapshot = _read_json_mapping(job_path / "source_snapshot.json")
    environment = _read_json_mapping(job_path / "environment.json")
    validation = _read_json_mapping(job_path / "validation.json")
    sandbox = environment.get("sandbox")
    sandbox_mapping = sandbox if isinstance(sandbox, Mapping) else {}
    return {
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "hash_algorithm": HASH_ALGORITHM,
        "gateway_version": __version__,
        "job_id": job_id,
        "project_id": project_id,
        "source_commit": snapshot.get("source_revision"),
        "sandbox_backend": {
            "backend_id": sandbox_mapping.get("backend_id", "not_recorded"),
            "safety_level": sandbox_mapping.get("safety_level", "not_recorded"),
        },
        "validation_summary": {
            "passed": bool(validation.get("passed", False)),
            "mandatory": list(validation.get("mandatory", []))
            if isinstance(validation.get("mandatory", []), list)
            else [],
            "counts": dict(validation.get("counts", {}))
            if isinstance(validation.get("counts", {}), Mapping)
            else {},
            "cancelled": bool(validation.get("cancelled", False)),
        },
        "final_event_hash": final_event_hash,
        "manifest_checksum": {
            "algorithm": HASH_ALGORITHM,
            "scope": "compatibility_evidence_file_digests",
            "value": manifest_checksum,
        },
        "generated_at": generated_at,
        "signer": {
            "identity": "universal-project-gateway-local-development",
            "signature_algorithm": "none",
            "signature": None,
        },
    }


def _verify_attestation(
    attestation: Mapping[str, Any],
    events: list[Any],
    manifest_files: Mapping[Any, Any],
    *,
    evidence_path: Path,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    if attestation.get("evidence_schema_version") != EVIDENCE_SCHEMA_VERSION:
        errors.append({"code": "ATTESTATION_SCHEMA_INVALID", "path": ATTESTATION_FILE})
    if attestation.get("hash_algorithm") != HASH_ALGORITHM:
        errors.append({"code": "ATTESTATION_ALGORITHM_INVALID", "path": ATTESTATION_FILE})
    final_event = events[-1] if events and isinstance(events[-1], Mapping) else {}
    if final_event.get("event_type") != "evidence_finalized":
        errors.append({"code": "EVIDENCE_FINAL_EVENT_INVALID", "path": CHAIN_FILE})
    if attestation.get("final_event_hash") != final_event.get("event_hash"):
        errors.append({"code": "ATTESTATION_FINAL_HASH_MISMATCH", "path": ATTESTATION_FILE})
    if attestation.get("job_id") != final_event.get("job_id"):
        errors.append({"code": "ATTESTATION_JOB_MISMATCH", "path": ATTESTATION_FILE})
    if attestation.get("project_id") != final_event.get("project_id"):
        errors.append({"code": "ATTESTATION_PROJECT_MISMATCH", "path": ATTESTATION_FILE})

    compatibility_checksums: dict[str, str] = {}
    for filename in COMPATIBILITY_EVIDENCE_FILES:
        digest = manifest_files.get(filename)
        if not isinstance(digest, str):
            errors.append({"code": "COMPATIBILITY_CHECKSUM_MISSING", "path": filename})
        else:
            compatibility_checksums[filename] = digest
    recorded_manifest_checksum = attestation.get("manifest_checksum")
    if not isinstance(recorded_manifest_checksum, Mapping) or (
        recorded_manifest_checksum.get("algorithm") != HASH_ALGORITHM
        or recorded_manifest_checksum.get("scope")
        != "compatibility_evidence_file_digests"
        or recorded_manifest_checksum.get("value")
        != compatibility_manifest_checksum(compatibility_checksums)
    ):
        errors.append({"code": "ATTESTATION_MANIFEST_CHECKSUM_MISMATCH", "path": ATTESTATION_FILE})

    signer = attestation.get("signer")
    if not isinstance(signer, Mapping) or (
        signer.get("identity") != "universal-project-gateway-local-development"
        or signer.get("signature_algorithm") != "none"
        or signer.get("signature") is not None
    ):
        errors.append({"code": "ATTESTATION_SIGNER_INVALID", "path": ATTESTATION_FILE})
    if not evidence_path.is_dir():
        errors.append({"code": "EVIDENCE_PATH_INVALID", "path": str(evidence_path)})
    return errors


def _infer_project_id(job_path: Path, final_report: Mapping[str, Any]) -> str:
    for document in (
        final_report,
        _read_json_mapping(job_path / "task.json"),
        _read_json_mapping(job_path / "intent.json"),
    ):
        project_id = document.get("project_id")
        if isinstance(project_id, str) and project_id:
            return project_id
    events = _read_event_chain(job_path / CHAIN_FILE)
    if events and isinstance(events[0], Mapping):
        project_id = events[0].get("project_id")
        if isinstance(project_id, str) and project_id:
            return project_id
    return "unknown-project"


def _read_json_mapping(
    path: Path,
    *,
    errors: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        if errors is not None:
            errors.append({"code": "EVIDENCE_JSON_INVALID", "path": path.name})
            return {}
        raise EvidenceError(
            "evidence JSON document is invalid",
            code="EVIDENCE_INVALID",
            details={"path": path.name},
        ) from exc
    if not isinstance(value, Mapping):
        if errors is not None:
            errors.append({"code": "EVIDENCE_JSON_INVALID", "path": path.name})
            return {}
        raise EvidenceError(
            "evidence JSON document must contain an object",
            code="EVIDENCE_INVALID",
            details={"path": path.name},
        )
    return dict(value)


def _read_event_chain(
    path: Path,
    *,
    errors: list[dict[str, str]] | None = None,
) -> list[Any]:
    if not path.exists():
        return []
    events: list[Any] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        if errors is not None:
            errors.append({"code": "EVIDENCE_CHAIN_INVALID", "path": CHAIN_FILE})
            return []
        raise EvidenceError("evidence chain cannot be read", code="EVIDENCE_CHAIN_INVALID") from exc
    for line_number, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            if errors is not None:
                errors.append(
                    {
                        "code": "EVIDENCE_EVENT_INVALID",
                        "path": f"{CHAIN_FILE}:{line_number}",
                    }
                )
                events.append(None)
                continue
            raise EvidenceError(
                "evidence chain contains invalid JSONL",
                code="EVIDENCE_CHAIN_INVALID",
                details={"line": line_number},
            ) from exc
        events.append(event)
    return events


def redact(value: Any) -> Any:
    """Recursively redact secret-bearing keys and common token shapes."""

    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _SECRET_KEY.search(f"_{key_text}_"):
                result[key_text] = "[REDACTED]"
            else:
                result[key_text] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, tuple):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(text: str) -> str:
    result = _BEARER.sub("Bearer [REDACTED]", text)
    result = _LABELED_SECRET.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", result)
    result = _URL_CREDENTIAL.sub(r"\1[REDACTED]@", result)
    return _TOKEN_SHAPES.sub("[REDACTED]", result)


def verify_evidence(path: str | os.PathLike[str]) -> EvidenceVerification:
    evidence_path = Path(path).expanduser().resolve(strict=False)
    return EvidenceLedger(evidence_path.parent).verify(evidence_path)


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if dataclasses.is_dataclass(value):
        return _plain(dataclasses.asdict(value))
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _plain(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(item) for item in value]
    return value


def _evidence_files(root: Path) -> list[Path]:
    files: list[Path] = []

    def visit(directory: Path) -> None:
        for entry in sorted(os.scandir(directory), key=lambda item: item.name.casefold()):
            path = Path(entry.path)
            if is_reparse_point(path):
                raise EvidenceError(
                    "links are forbidden inside evidence bundles",
                    code="EVIDENCE_LINK_FORBIDDEN",
                    details={"path": path.relative_to(root).as_posix()},
                )
            if path.is_dir():
                visit(path)
            elif path.is_file():
                files.append(path)

    visit(root)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".upg-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _append_text_durable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


__all__ = [
    "ALL_EVIDENCE_FILES",
    "ATTESTATION_FILE",
    "CHAIN_EVIDENCE_FILES",
    "CHAIN_FILE",
    "CHECKSUM_FILE",
    "COMPATIBILITY_EVIDENCE_FILES",
    "EVIDENCE_FILES",
    "EvidenceError",
    "EvidenceLedger",
    "EvidenceVerification",
    "redact",
    "redact_text",
    "verify_evidence",
]
