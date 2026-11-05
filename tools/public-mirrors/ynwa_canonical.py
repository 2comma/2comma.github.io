#!/usr/bin/env python3
"""Canonical YNWA dist, packaging, and post-dashboard mirror handoff.

This does not upload to Cloudflare, crawl the live site, or create a repository checkout.
The dashboard remains the deploy route. Mirroring runs only after a person
confirms that the ZIP they name was the ZIP the dashboard accepted, and only
when that file's digest still matches the confirmation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import tempfile
from pathlib import Path

from common import MirrorError
from release import release_root
from ynwa_prepare import prepare_root_hub
from ynwa_prepare import (
    load_site,
    scan_payload,
    validate_canonical_references,
    write_tree,
)

BASELINE_PATH = Path(__file__).with_name("ynwa-baseline.txt")
VAGUE_DEPLOYMENT_IDS = {
    "todo",
    "unknown",
    "dashboard",
    "pending",
    "success",
    "none",
    "n/a",
    "na",
    "test",
    "xxx",
    "id",
    "deployment",
    "confirmed",
}


def load_baseline(path: Path | None = None) -> tuple[str, dict[str, str]]:
    source = path or BASELINE_PATH
    zip_sha = ""
    files: dict[str, str] = {}
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, rest = line.split(None, 1)
        if kind == "zip":
            zip_sha = rest.strip().lower()
        elif kind == "file":
            digest, rel = rest.split(None, 1)
            files[rel] = digest.strip().lower()
        else:
            raise MirrorError(f"bad baseline line: {line}")
    if len(zip_sha) != 64 or len(files) != 21:
        raise MirrorError("YNWA baseline manifest is incomplete")
    return zip_sha, files


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def restore_dist(
    zip_path: str,
    dest: str,
    *,
    expected_sha256: str | None = None,
) -> str:
    """Materialize dist from the known public ZIP. Refuse if dest already has files."""
    archive = Path(zip_path)
    target = Path(dest)
    if not archive.is_file() or archive.is_symlink():
        raise MirrorError(f"public ZIP is missing or is a symlink: {zip_path}")
    if target.is_symlink():
        raise MirrorError(f"refusing to follow a symlink at {dest}")
    if _nonempty(target):
        raise MirrorError(
            f"canonical dist already exists at {dest}. Refusing to overwrite it."
        )
    baseline_sha, baseline_files = load_baseline()
    expected = (expected_sha256 or baseline_sha).lower()
    actual = sha256_file(archive)
    if actual != expected:
        raise MirrorError(
            f"ZIP digest {actual} does not match the known public ZIP {expected}. "
            "Nothing was written."
        )
    files, omitted = load_site(str(archive))
    if omitted:
        raise MirrorError("known public ZIP contained deploy metadata. Nothing was written.")
    if set(files) != set(baseline_files):
        raise MirrorError(
            "ZIP members are not the 21-file public baseline. Nothing was written."
        )
    for rel, digest in baseline_files.items():
        if sha256_bytes(files[rel]) != digest:
            raise MirrorError(f"content hash mismatch for {rel}. Nothing was written.")
    write_tree(str(target), files)
    provenance = {
        "source_zip": str(archive.resolve()),
        "sha256": actual,
        "files": baseline_files,
        "note": "Restored only because the dist directory was absent. Not a deploy.",
    }
    _atomic_write(target.parent / "ynwa-baseline.json", json.dumps(provenance, indent=2) + "\n")
    return f"public-mirrors: restored {len(files)} files into {dest}"


def package_dist(dist: str, out: str) -> str:
    """Zip the canonical dist without modifying it and without deploying."""
    root = Path(dist)
    files = _read_dist(root)
    _, baseline_files = load_baseline()
    expected = set(baseline_files)
    extra = sorted(set(files) - expected)
    missing = sorted(expected - set(files))
    if extra or missing:
        detail = []
        if extra:
            detail.append("unexpected " + extra[0])
        if missing:
            detail.append("missing " + missing[0])
        raise MirrorError(
            "dist is not the reviewed 21-file manifest (" + ", ".join(detail) + "). "
            "Add a path to ynwa-baseline.txt before packaging it. Nothing was packaged."
        )
    for rel, data in files.items():
        scan_payload(rel, data)
    validate_canonical_references(files)
    before = {rel: sha256_bytes(data) for rel, data in files.items()}
    destination = Path(out)
    digest = _write_zip_atomic(destination, files)
    after = _read_dist(root)
    for rel, old in before.items():
        if sha256_bytes(after[rel]) != old:
            raise MirrorError(f"packaging modified {rel}")
    return (
        f"public-mirrors: packaged {destination} sha256={digest}\n"
        "public-mirrors: not deployed and not mirrored. "
        "Upload this ZIP in the Cloudflare dashboard (project ynwa-hub). "
        "After that upload succeeds, run ynwa-dashboard-handoff.sh with this digest."
    )


def confirm_dashboard(
    zip_path: str,
    deployment_id: str,
    marker_path: str,
    *,
    confirm: bool,
    digest: str | None = None,
) -> dict:
    """Record a human dashboard confirmation. This does not deploy or mirror."""
    if not confirm:
        raise MirrorError(
            "dashboard success was not confirmed. Nothing was recorded and nothing was mirrored."
        )
    _require_deployment_id(deployment_id)
    archive = Path(zip_path)
    if not archive.is_file() or archive.is_symlink():
        raise MirrorError(f"ZIP is missing or is a symlink: {zip_path}")
    actual = sha256_file(archive)
    if digest is not None and digest.lower() != actual:
        raise MirrorError(
            f"confirmed digest {digest.lower()} does not match the ZIP {actual}. "
            "Nothing was recorded."
        )
    marker = {
        "zip": str(archive.resolve()),
        "sha256": actual,
        "deployment_id": deployment_id,
        "confirmed_dashboard_success": True,
    }
    _atomic_write(Path(marker_path), json.dumps(marker, indent=2) + "\n")
    return marker


def mirror_confirmed(
    marker_path: str,
    repo: str,
    *,
    remote: str = "origin",
    branch: str = "main",
) -> str:
    """Check the confirmed ZIP, then publish that hub at the repository root.

    Asset paths stay root-absolute, matching the public site. /ynwa/ is not
    filled with a second copy. news/, lfc/, team/, and tools/ are not staged.
    """
    marker_file = Path(marker_path)
    if not marker_file.is_file():
        raise MirrorError(
            f"no dashboard confirmation at {marker_path}. Nothing was mirrored."
        )
    marker = json.loads(marker_file.read_text(encoding="utf-8"))
    if marker.get("confirmed_dashboard_success") is not True:
        raise MirrorError("confirmation marker is not a dashboard success. Nothing was mirrored.")
    archive = Path(marker["zip"])
    if not archive.is_file() or archive.is_symlink():
        raise MirrorError(f"confirmed ZIP is missing: {archive}")
    actual = sha256_file(archive)
    expected = str(marker["sha256"]).lower()
    if actual != expected:
        raise MirrorError(
            f"ZIP digest changed after confirmation ({actual} != {expected}). "
            "Refusing to mirror. Upload the current ZIP in the dashboard and confirm that digest."
        )
    if not repo:
        raise MirrorError(
            "PUBLIC_MIRROR_REPO is unset. Nothing was mirrored and no clone was created."
        )
    if sha256_file(archive) != expected:
        raise MirrorError("ZIP changed before publish. Nothing was mirrored.")
    stage = tempfile.mkdtemp(prefix="ynwa-confirmed-")
    try:
        staging = str(Path(stage) / "site")
        prepare_root_hub(str(archive), staging)
        if sha256_file(archive) != expected:
            raise MirrorError("ZIP changed while staging. Nothing was mirrored.")
        published = release_root(staging, repo, remote=remote, branch=branch)
    finally:
        _remove_tree(Path(stage))
    return (
        published
        + "\npublic-mirrors: YNWA hub is at the site root. "
        "/ynwa/ was not replaced with a duplicate."
    )


def handoff(
    zip_path: str,
    deployment_id: str,
    digest: str,
    marker_path: str,
    repo: str,
    *,
    confirm: bool,
    remote: str = "origin",
    branch: str = "main",
) -> str:
    recorded = confirm_dashboard(
        zip_path,
        deployment_id,
        marker_path,
        confirm=confirm,
        digest=digest,
    )
    if not repo:
        raise MirrorError(
            "confirmation recorded for "
            + recorded["sha256"]
            + " but PUBLIC_MIRROR_REPO is unset. Nothing was mirrored and no clone was created."
        )
    try:
        return mirror_confirmed(marker_path, repo, remote=remote, branch=branch)
    except MirrorError as exc:
        raise MirrorError(
            f"confirmation kept at {marker_path}. Mirror failed: {exc}"
        ) from exc


def _read_dist(root: Path) -> dict[str, bytes]:
    if not root.is_dir() or root.is_symlink():
        raise MirrorError(f"canonical dist is missing or is a symlink: {root}")
    files: dict[str, bytes] = {}
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames:
            candidate = Path(dirpath) / name
            if candidate.is_symlink():
                raise MirrorError(f"symlink rejected in dist: {candidate}")
        for name in filenames:
            candidate = Path(dirpath) / name
            if candidate.is_symlink():
                raise MirrorError(f"symlink rejected in dist: {candidate}")
            rel = candidate.relative_to(root).as_posix()
            files[rel] = candidate.read_bytes()
    if not files:
        raise MirrorError(f"canonical dist is empty: {root}")
    return files


def _write_zip_atomic(destination: Path, files: dict[str, bytes]) -> str:
    import zipfile

    destination.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix=".ynwa-deploy-",
        suffix=".zip",
        dir=destination.parent,
        delete=False,
    )
    temporary = Path(handle.name)
    handle.close()
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for rel in sorted(files):
                info = zipfile.ZipInfo(rel)
                info.date_time = (2026, 11, 2, 0, 0, 0)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = (stat.S_IFREG | 0o644) << 16
                archive.writestr(info, files[rel])
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return sha256_file(destination)


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        prefix="." + path.name + ".",
        dir=path.parent,
        delete=False,
        mode="w",
        encoding="utf-8",
    )
    temporary = Path(handle.name)
    try:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())
        handle.close()
        os.replace(temporary, path)
    except Exception:
        handle.close()
        temporary.unlink(missing_ok=True)
        raise


def _nonempty(path: Path) -> bool:
    if not path.exists():
        return False
    if not path.is_dir():
        return True
    return any(path.iterdir())


def _remove_tree(path: Path) -> None:
    if not path.exists():
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
        return
    for child in path.iterdir():
        _remove_tree(child)
    path.rmdir()


def _require_deployment_id(value: str) -> None:
    import re

    if value.lower() in VAGUE_DEPLOYMENT_IDS or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{5,127}", value):
        raise MirrorError(
            "deployment id must be the id shown by the Cloudflare dashboard after the upload succeeds."
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="YNWA canonical dist and dashboard handoff.")
    sub = parser.add_subparsers(dest="command", required=True)

    restore = sub.add_parser("restore", help="Restore dist from the known public ZIP if the directory is absent.")
    restore.add_argument("--zip", required=True)
    restore.add_argument("--dest", required=True)

    package = sub.add_parser("package", help="Write a deploy ZIP from dist. Does not deploy or mirror.")
    package.add_argument("--dist", required=True)
    package.add_argument("--out", required=True)

    confirm = sub.add_parser("confirm", help="Record dashboard success for one ZIP digest. Does not mirror.")
    confirm.add_argument("--zip", required=True)
    confirm.add_argument("--deployment-id", required=True)
    confirm.add_argument("--digest", required=True)
    confirm.add_argument("--marker", required=True)
    confirm.add_argument("--confirm-dashboard-success", action="store_true")

    mirror = sub.add_parser("mirror-confirmed", help="Mirror the ZIP named by a confirmation marker.")
    mirror.add_argument("--marker", required=True)
    mirror.add_argument("--repo", default=os.environ.get("PUBLIC_MIRROR_REPO", ""))
    mirror.add_argument("--remote", default=os.environ.get("PUBLIC_MIRROR_REMOTE", "origin"))
    mirror.add_argument("--branch", default=os.environ.get("PUBLIC_MIRROR_BRANCH", "main"))

    done = sub.add_parser("handoff", help="Confirm a dashboard upload, then mirror that exact ZIP.")
    done.add_argument("--zip", required=True)
    done.add_argument("--deployment-id", required=True)
    done.add_argument("--digest", required=True)
    done.add_argument("--marker", required=True)
    done.add_argument("--confirm-dashboard-success", action="store_true")
    done.add_argument("--repo", default=os.environ.get("PUBLIC_MIRROR_REPO", ""))
    done.add_argument("--remote", default=os.environ.get("PUBLIC_MIRROR_REMOTE", "origin"))
    done.add_argument("--branch", default=os.environ.get("PUBLIC_MIRROR_BRANCH", "main"))

    args = parser.parse_args(argv)
    try:
        if args.command == "restore":
            print(restore_dist(args.zip, args.dest))
        elif args.command == "package":
            print(package_dist(args.dist, args.out))
        elif args.command == "confirm":
            marker = confirm_dashboard(
                args.zip,
                args.deployment_id,
                args.marker,
                confirm=args.confirm_dashboard_success,
                digest=args.digest,
            )
            print(
                "public-mirrors: recorded dashboard confirmation "
                f"sha256={marker['sha256']} deployment={marker['deployment_id']}. Not mirrored."
            )
        elif args.command == "mirror-confirmed":
            print(mirror_confirmed(args.marker, args.repo, remote=args.remote, branch=args.branch))
        elif args.command == "handoff":
            print(
                handoff(
                    args.zip,
                    args.deployment_id,
                    args.digest,
                    args.marker,
                    args.repo,
                    confirm=args.confirm_dashboard_success,
                    remote=args.remote,
                    branch=args.branch,
                )
            )
    except MirrorError as exc:
        print(f"public-mirrors: ERROR {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
