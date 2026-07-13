"""Deterministic, checksummed evidence bundles with conservative redaction."""

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

from .models import GatewayError
from .scoped_fs import is_reparse_point

EVIDENCE_FILES = (
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "evidence_path": str(self.evidence_path),
            "checked_files": self.checked_files,
            "errors": list(self.errors),
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
        if name not in EVIDENCE_FILES:
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
        for filename in EVIDENCE_FILES:
            if not (job_path / filename).is_file():
                self.write(job_id, filename, defaults[filename])

        checksums: dict[str, str] = {}
        for path in _evidence_files(job_path):
            relative = path.relative_to(job_path).as_posix()
            if relative == CHECKSUM_FILE:
                continue
            checksums[relative] = _sha256(path)
        manifest = {"algorithm": "sha256", "files": dict(sorted(checksums.items()))}
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
        return EvidenceVerification(not errors, evidence_path, checked, tuple(errors))

    verify_checksums = verify


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


__all__ = [
    "CHECKSUM_FILE",
    "EVIDENCE_FILES",
    "EvidenceError",
    "EvidenceLedger",
    "EvidenceVerification",
    "redact",
    "redact_text",
    "verify_evidence",
]
