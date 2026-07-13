from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from universal_project_gateway.config import GatewayConfig
from universal_project_gateway.service import GatewayService

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def gateway_factory(
    tmp_path: Path,
) -> Callable[[str], tuple[GatewayService, Path]]:
    """Create an isolated Gateway and a disposable copy of one fixture."""

    counter = 0

    def create(fixture_name: str) -> tuple[GatewayService, Path]:
        nonlocal counter
        counter += 1
        source = tmp_path / f"source-{counter}" / fixture_name
        shutil.copytree(REPOSITORY_ROOT / "fixtures" / fixture_name, source)
        config = GatewayConfig.from_root(tmp_path / f"gateway-{counter}")
        gateway = GatewayService(config)
        gateway.register_project(source / "PROJECT_MANIFEST.yaml")
        return gateway, source

    return create
