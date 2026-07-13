from __future__ import annotations

from pathlib import Path

import pytest

from universal_project_gateway.scoped_fs import ScopedFileError, ScopedWorkspace
from universal_project_gateway.workspaces import WorkspaceManager


@pytest.fixture
def scoped_workspace(tmp_path: Path) -> tuple[ScopedWorkspace, Path]:
    root = tmp_path / "workspace"
    root.mkdir()
    (root / "safe.txt").write_text("safe\n", encoding="utf-8")
    (root / "secrets").mkdir()
    (root / "secrets" / "token.txt").write_text("do-not-read\n", encoding="utf-8")
    (root / ".env").write_text("PASSWORD=do-not-read\n", encoding="utf-8")
    return ScopedWorkspace(root, protected_paths=("secrets/", ".env")), root


@pytest.mark.parametrize(
    "malicious_path",
    [
        "../outside.txt",
        "sub/../../outside.txt",
        "..\\outside.txt",
        "safe/../../../outside.txt",
    ],
)
def test_parent_traversal_is_rejected_before_io(
    scoped_workspace: tuple[ScopedWorkspace, Path], malicious_path: str
) -> None:
    scoped, root = scoped_workspace
    outside = root.parent / "outside.txt"

    with pytest.raises(ScopedFileError) as caught:
        scoped.create_text(malicious_path, "escaped")

    assert caught.value.code == "PATH_TRAVERSAL_FORBIDDEN"
    assert not outside.exists()


@pytest.mark.parametrize(
    "absolute_path",
    [
        "/etc/passwd",
        "C:\\Windows\\System32\\drivers\\etc\\hosts",
        "D:/outside.txt",
        "\\\\server\\share\\secret.txt",
    ],
)
def test_posix_drive_and_unc_absolute_paths_are_rejected(
    scoped_workspace: tuple[ScopedWorkspace, Path], absolute_path: str
) -> None:
    scoped, _ = scoped_workspace

    with pytest.raises(ScopedFileError) as caught:
        scoped.read_text(absolute_path)

    assert caught.value.code == "ABSOLUTE_PATH_FORBIDDEN"


def test_manifest_protected_paths_are_hidden_and_inaccessible(
    scoped_workspace: tuple[ScopedWorkspace, Path],
) -> None:
    scoped, root = scoped_workspace

    listed_names = {entry["name"] for entry in scoped.list_dir(".")}
    assert "safe.txt" in listed_names
    assert "secrets" not in listed_names
    assert ".env" not in listed_names
    for path in (".env", "secrets/token.txt", "secrets/new.txt"):
        with pytest.raises(ScopedFileError) as caught:
            scoped.write_text(path, "not allowed")
        assert caught.value.code == "PROTECTED_PATH_FORBIDDEN"

    assert (root / "secrets" / "token.txt").read_text(encoding="utf-8") == "do-not-read\n"


def test_symlink_escape_is_rejected_where_supported(
    scoped_workspace: tuple[ScopedWorkspace, Path],
) -> None:
    scoped, root = scoped_workspace
    outside = root.parent / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    link = root / "escape.txt"
    try:
        link.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable on this host: {exc}")

    with pytest.raises(ScopedFileError) as caught:
        scoped.read_text("escape.txt")

    assert caught.value.code == "LINK_PATH_FORBIDDEN"
    assert outside.read_text(encoding="utf-8") == "outside\n"


def test_workspace_copy_omits_protected_content_and_source_links(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "public.txt").write_text("public\n", encoding="utf-8")
    (source / ".env").write_text("TOKEN=raw-secret\n", encoding="utf-8")
    (source / "secrets").mkdir()
    (source / "secrets" / "key.txt").write_text("raw-secret\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    linked = source / "linked.txt"
    symlink_supported = True
    try:
        linked.symlink_to(outside)
    except (NotImplementedError, OSError):
        symlink_supported = False

    manager = WorkspaceManager(tmp_path / "jobs")
    snapshot = manager.create(
        "job-copy-boundary",
        source,
        protected_paths=(".env", "secrets/"),
    )

    workspace = snapshot.workspace_root
    assert (workspace / "public.txt").read_text(encoding="utf-8") == "public\n"
    assert not (workspace / ".env").exists()
    assert not (workspace / "secrets").exists()
    if symlink_supported:
        assert not (workspace / "linked.txt").exists()
    omitted = {item["path"]: item["reason"] for item in snapshot.omitted_paths}
    assert omitted[".env"] == "excluded"
    assert omitted["secrets"] == "excluded"
    if symlink_supported:
        assert omitted["linked.txt"] == "link_or_reparse_point"
    assert outside.read_text(encoding="utf-8") == "outside\n"
