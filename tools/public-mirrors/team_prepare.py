"""Prepare a sanitized Team Status export for /team/.

The artifact is the handoff bundle: TeamStatus.tsx plus a provenance README.
This module does not fetch Canvas, does not scrape, and does not redact
identifiers. A sensitive field, the wrong canvas, or JSX this renderer cannot
show aborts the prepare before any file is written.
"""

from __future__ import annotations

import os
import stat
import zipfile
from pathlib import Path

from common import MirrorError
from jsx_subset import iter_strings, parse_module, validate_tree
from sensitive import scan_text
from team_render import render_team_status

ALLOWED_FILES = {"TeamStatus.tsx", "README.md"}
MAX_FILE_BYTES = 500 * 1024


def prepare_team(artifact: str, out_dir: str) -> list[str]:
    files = load_bundle(artifact)
    unexpected = sorted(set(files) - ALLOWED_FILES)
    if unexpected:
        raise MirrorError(
            f"unexpected file in Team Status bundle: {unexpected[0]}. "
            "Nothing was published."
        )
    missing = sorted(ALLOWED_FILES - set(files))
    if missing:
        raise MirrorError(
            f"Team Status bundle is missing {missing[0]}. Nothing was published."
        )
    try:
        source = files["TeamStatus.tsx"].decode("utf-8")
        provenance = files["README.md"].decode("utf-8")
    except UnicodeError as exc:
        raise MirrorError("Team Status bundle is not utf-8. Nothing was published.") from exc
    scan_text(provenance, "README.md", allow_canvas_provenance=True)
    scan_text(source, "TeamStatus.tsx")
    names, tree = parse_module(source)
    validate_tree(names, tree)
    page = render_team_status(tree)
    for literal in iter_strings(tree):
        if literal not in page and _escape_check(literal) not in page:
            raise MirrorError(
                "rendered page is missing source text. Refusing to publish a partial export."
            )
    scan_text(page, "team/index.html")
    if "cursor.com/canvas/" in page or "grok/canvas" in page:
        raise MirrorError("rendered page still depends on Canvas. Nothing was published.")
    out = Path(out_dir)
    if out.exists() and any(out.iterdir()):
        raise MirrorError(f"output directory is not empty: {out_dir}")
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(page, encoding="utf-8")
    (out / ".nojekyll").write_bytes(b"")
    return [f"public-mirrors: prepared team ({2} files)"]


def _escape_check(literal: str) -> str:
    return literal.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_bundle(artifact: str) -> dict[str, bytes]:
    path = Path(artifact)
    if not path.exists():
        raise MirrorError(f"artifact does not exist: {artifact}")
    if path.is_symlink():
        raise MirrorError("artifact path is a symlink")
    if path.is_dir():
        return read_directory(path)
    if path.is_file() and zipfile.is_zipfile(path):
        return read_zip(path)
    raise MirrorError("Team Status artifact must be a directory or a zip file")


def read_directory(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for dirpath, dirnames, filenames in os.walk(path, followlinks=False):
        for name in dirnames:
            if (Path(dirpath) / name).is_symlink():
                raise MirrorError("symlink rejected in Team Status bundle")
        for name in filenames:
            candidate = Path(dirpath) / name
            if candidate.is_symlink():
                raise MirrorError("symlink rejected in Team Status bundle")
            rel = candidate.relative_to(path).as_posix()
            if "/" in rel or rel.startswith("."):
                raise MirrorError(f"unexpected path in Team Status bundle: {rel}")
            data = candidate.read_bytes()
            if len(data) > MAX_FILE_BYTES:
                raise MirrorError(f"Team Status file exceeds size limit: {rel}")
            files[rel] = data
    return files


def read_zip(path: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            if name.endswith("/"):
                continue
            if name.startswith("/") or ".." in name.split("/"):
                raise MirrorError(f"unsafe path in Team Status bundle: {name}")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise MirrorError(f"symlink rejected in Team Status bundle: {name}")
            if "/" in name or name.startswith("."):
                raise MirrorError(f"unexpected path in Team Status bundle: {name}")
            if info.file_size > MAX_FILE_BYTES:
                raise MirrorError(f"Team Status file exceeds size limit: {name}")
            files[name] = archive.read(info)
    return files
