"""Filesystem configuration for a local Universal Project Gateway instance."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_MAX_TEXT_FILE_BYTES = 1_000_000
DEFAULT_COMMAND_TIMEOUT_SECONDS = 120
DEFAULT_CONTEXT_MAX_FILES = 500
DEFAULT_CONTEXT_MAX_BYTES = 2_000_000


@dataclass(frozen=True, slots=True)
class GatewayConfig:
    """Resolved paths and conservative resource limits used by the gateway.

    Construction is side-effect free. Call :meth:`ensure_runtime_dirs` only at a
    command boundary that is allowed to create local runtime state.
    """

    root_dir: Path
    registry_path: Path
    database_path: Path
    workspaces_root: Path
    artifacts_root: Path
    max_text_file_bytes: int = DEFAULT_MAX_TEXT_FILE_BYTES
    command_timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS
    context_max_files: int = DEFAULT_CONTEXT_MAX_FILES
    context_max_bytes: int = DEFAULT_CONTEXT_MAX_BYTES
    intelligence_root: Path | None = None

    @classmethod
    def from_root(cls, root: str | os.PathLike[str]) -> GatewayConfig:
        root_dir = Path(root).expanduser().resolve()
        return cls(
            root_dir=root_dir,
            registry_path=root_dir / "var" / "registry" / "projects.yaml",
            database_path=root_dir / "var" / "gateway.db",
            workspaces_root=root_dir / "workspaces" / "jobs",
            artifacts_root=root_dir / "artifacts" / "jobs",
        )

    @classmethod
    def discover(cls, start: str | os.PathLike[str] | None = None) -> GatewayConfig:
        """Discover the repository root, honoring ``UPG_ROOT`` when provided."""

        configured = os.environ.get("UPG_ROOT")
        if configured:
            return cls.from_root(configured)

        candidate = Path(start or Path.cwd()).expanduser().resolve()
        for directory in (candidate, *candidate.parents):
            if (directory / "pyproject.toml").is_file() or (directory / "registry").is_dir():
                return cls.from_root(directory)
        return cls.from_root(candidate)

    @property
    def jobs_database_path(self) -> Path:
        """Compatibility alias for callers that name the database by purpose."""

        return self.database_path

    @property
    def workspace_root(self) -> Path:
        """Compatibility alias for the root containing per-job workspaces."""

        return self.workspaces_root

    @property
    def evidence_root(self) -> Path:
        """Compatibility alias for the root containing per-job evidence."""

        return self.artifacts_root

    @property
    def intelligence_cache_root(self) -> Path:
        """Gateway-owned cache state, separate from registered project sources."""

        configured = self.intelligence_root or self.database_path.parent / "project_intelligence"
        return configured.expanduser().resolve()

    def ensure_runtime_dirs(self) -> None:
        """Create only gateway-owned state directories."""

        for directory in (
            self.registry_path.parent,
            self.database_path.parent,
            self.workspaces_root,
            self.artifacts_root,
            self.intelligence_cache_root,
        ):
            directory.mkdir(parents=True, exist_ok=True)
