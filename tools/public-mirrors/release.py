#!/usr/bin/env python3
"""Publish one prepared staging directory to ynwa/ or team/ only.

The release uses a temporary worktree taken from the fetched branch tip.
It does not reset the caller's checkout, does not stage other paths, and
does not force-push. A non-fast-forward push is rebased once per attempt and
retried. A conflict aborts with the remote unchanged by this process.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from common import MirrorError, assert_target, redact
from sensitive import scan_bytes, scan_text
from ynwa_prepare import allowed, scan_payload

LABELS = {
    "ynwa": "YNWA mirror",
    "team": "Team Status mirror",
}


def release(
    target: str,
    staging: str,
    repo: str,
    remote: str = "origin",
    branch: str = "main",
    lock_timeout: float = 60,
    before_push=None,
) -> str:
    global _EMPTY_HOOKS
    subdir = assert_target(target)
    _reject_bad_remote(remote, branch)
    hooks = tempfile.mkdtemp(prefix="public-mirror-hooks-")
    _EMPTY_HOOKS = hooks
    repo_path = Path(repo)
    lock = None
    work = None
    try:
        staging_path = Path(staging)
        if not staging_path.is_dir():
            raise MirrorError(f"staging directory does not exist: {staging}")
        if not _is_git(repo_path):
            raise MirrorError(
                f"not an existing git checkout: {repo}. This tool does not create a clone."
            )
        files = _read_staging(subdir, staging_path)
        lock = _acquire_lock(repo_path, lock_timeout)
        _git(repo_path, "fetch", remote, branch)
        scratch = Path(tempfile.mkdtemp(prefix="public-mirror-"))
        work = scratch / "wt"
        _git(repo_path, "worktree", "add", "--detach", str(work), "FETCH_HEAD")
        dest = work / subdir
        if dest.is_symlink():
            raise MirrorError(f"{subdir} is a symlink; refusing to replace it")
        if dest.exists():
            _remove_tree(dest)
        _copy_files(work, subdir, files)
        _git(work, "add", "--all", "--", subdir)
        staged = _staged_paths(work)
        if not staged:
            return f"public-mirrors: {subdir} has no changes"
        _assert_scoped(staged, subdir)
        stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")
        message = f"{LABELS[subdir]}: {stamp} build"
        _git(
            work,
            "-c",
            "user.name=2comma",
            "-c",
            "user.email=2comma@users.noreply.github.com",
            "commit",
            "-m",
            message,
        )
        if before_push is not None:
            before_push()
        _push_with_retry(work, remote, branch, subdir)
        head = _git(work, "rev-parse", "--short", "HEAD").stdout.strip()
        return f"public-mirrors: pushed {subdir} ({head}) to {remote} {branch}"
    finally:
        if work is not None:
            shutil.rmtree(work.parent, ignore_errors=True)
            subprocess.run(
                ["git", "-C", str(repo_path), "worktree", "prune"],
                check=False,
                capture_output=True,
                text=True,
            )
        if lock is not None:
            fcntl.flock(lock, fcntl.LOCK_UN)
            lock.close()
        shutil.rmtree(hooks, ignore_errors=True)
        _EMPTY_HOOKS = None


def _reject_bad_remote(remote: str, branch: str) -> None:
    if remote.startswith("-") or branch.startswith("-"):
        raise MirrorError("refusing a remote or branch that looks like an option")
    if branch in {"HEAD", ""} or "/" in branch:
        raise MirrorError(f"refusing branch name {branch!r}")
    lowered = remote.lower()
    if "://" in remote and "@" in remote.split("://", 1)[1].split("/", 1)[0]:
        raise MirrorError("refusing a remote URL that embeds credentials")


def _is_git(path: Path) -> bool:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--is-inside-work-tree"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        env=_git_env(),
    )
    if check and result.returncode != 0:
        detail = redact((result.stderr or result.stdout).strip())
        raise MirrorError(f"git {' '.join(args)} failed: {detail}")
    return result


_EMPTY_HOOKS: str | None = None


def _git_env() -> dict[str, str]:
    """Pass the operator environment through, but do not let repo hooks run.

    Tokens are not read or recorded here. Push output is redacted. An empty
    hooks path stops a clone hook from force-pushing or printing credentials.
    """
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    if _EMPTY_HOOKS:
        env["GIT_CONFIG_COUNT"] = "1"
        env["GIT_CONFIG_KEY_0"] = "core.hooksPath"
        env["GIT_CONFIG_VALUE_0"] = _EMPTY_HOOKS
    return env


def _acquire_lock(repo: Path, timeout: float):
    import time

    common = _git(repo, "rev-parse", "--git-common-dir").stdout.strip()
    common_path = Path(common)
    if not common_path.is_absolute():
        common_path = (repo / common_path).resolve()
    handle = open(common_path / "public-mirrors.lock", "a", encoding="utf-8")
    start = time.monotonic()
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if time.monotonic() - start >= timeout:
                handle.close()
                raise MirrorError(
                    "another public-mirrors release holds the lock. Nothing was published."
                )
            time.sleep(0.05)


def _read_staging(target: str, staging: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    for dirpath, dirnames, filenames in os.walk(staging, followlinks=False):
        for name in dirnames:
            if (Path(dirpath) / name).is_symlink():
                raise MirrorError("symlink in staging")
        for name in filenames:
            candidate = Path(dirpath) / name
            if candidate.is_symlink():
                raise MirrorError("symlink in staging")
            rel = candidate.relative_to(staging).as_posix()
            files[rel] = candidate.read_bytes()
    if target == "team":
        allowed_names = {"index.html", ".nojekyll"}
        extra = sorted(set(files) - allowed_names)
        if extra or set(files) != allowed_names:
            raise MirrorError("team staging must contain only index.html and .nojekyll")
        if files[".nojekyll"] != b"":
            raise MirrorError("team .nojekyll must be empty")
        text = files["index.html"].decode("utf-8")
        scan_text(text, "team/index.html")
        return files
    if ".nojekyll" in files and files[".nojekyll"] != b"":
        raise MirrorError("ynwa .nojekyll must be empty")
    for rel, data in files.items():
        if rel == ".nojekyll":
            continue
        if not allowed(rel):
            raise MirrorError(f"staging path is not on the YNWA allowlist: {rel}")
        scan_payload(rel, data)
        scan_bytes(data, rel)
    if "index.html" not in files:
        raise MirrorError("ynwa staging has no index.html")
    return files


def _copy_files(work: Path, subdir: str, files: dict[str, bytes]) -> None:
    dest_root = work / subdir
    dest_root.mkdir(parents=True)
    for rel, data in files.items():
        dest = dest_root.joinpath(*rel.split("/"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)


def _remove_tree(path: Path) -> None:
    if path.is_symlink():
        raise MirrorError(f"refusing to remove symlink {path}")
    for child in path.iterdir():
        if child.is_symlink():
            child.unlink()
        elif child.is_dir():
            _remove_tree(child)
        else:
            child.unlink()
    path.rmdir()


def _staged_paths(work: Path) -> list[str]:
    result = _git(work, "diff", "--cached", "--name-only")
    return [line for line in result.stdout.splitlines() if line]


def _assert_scoped(paths: list[str], subdir: str) -> None:
    for path in paths:
        if path != subdir and not path.startswith(subdir + "/"):
            raise MirrorError(f"refusing to commit path outside /{subdir}/: {path}")


def _push_with_retry(work: Path, remote: str, branch: str, subdir: str) -> None:
    refspec = f"HEAD:{branch}"
    for attempt in range(1, 6):
        result = subprocess.run(
            ["git", "-C", str(work), "push", remote, refspec],
            capture_output=True,
            text=True,
            env=_git_env(),
        )
        if result.returncode == 0:
            return
        detail = (result.stderr or "") + (result.stdout or "")
        if attempt == 5 or not _non_fast_forward(detail):
            raise MirrorError("push failed: " + redact(detail.strip()))
        _git(work, "fetch", remote, branch)
        rebase = subprocess.run(
            ["git", "-C", str(work), "rebase", "FETCH_HEAD"],
            capture_output=True,
            text=True,
            env=_git_env(),
        )
        if rebase.returncode != 0:
            subprocess.run(
                ["git", "-C", str(work), "rebase", "--abort"],
                capture_output=True,
                text=True,
                env=_git_env(),
            )
            message = redact((rebase.stderr or rebase.stdout).strip())
            raise MirrorError(
                "rebase onto the updated branch conflicted. "
                f"Nothing was force-pushed. {message}"
            )
        head = _git(work, "rev-parse", "HEAD").stdout.strip()
        fetched = _git(work, "rev-parse", "FETCH_HEAD").stdout.strip()
        if head == fetched:
            return
        diff = _git(work, "diff", "--name-only", "HEAD~1", "HEAD").stdout.splitlines()
        _assert_scoped([line for line in diff if line], subdir)


def _non_fast_forward(detail: str) -> bool:
    lowered = detail.lower()
    return "non-fast-forward" in lowered or "fetch first" in lowered


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Publish a prepared public mirror directory.")
    parser.add_argument("--target", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--lock-timeout", type=float, default=60)
    args = parser.parse_args(argv)
    try:
        print(
            release(
                args.target,
                args.staging,
                args.repo,
                remote=args.remote,
                branch=args.branch,
                lock_timeout=args.lock_timeout,
            )
        )
    except MirrorError as exc:
        print(f"public-mirrors: ERROR {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
