"""Shared errors, target allowlist, and output redaction for public mirrors."""

from __future__ import annotations

import os
import re

# Explicit publish targets. Anything else is an unknown page and must fail.
TARGETS = {
    "ynwa": "ynwa",
    "team": "team",
}

# Team Status only. team.twocommanews.com currently redirects at the Team TwoComma
# Canvas; that page is not an approved public export.
APPROVED_STORE_ID = "2b9c29d3-0086-4e82-8687-c62137bc8463"
APPROVED_CANVAS_ID = "7160075c-3e2e-45e1-9e05-4a2b2a08f087"
APPROVED_CANVAS_URL = (
    "https://cursor.com/canvas/store-"
    + APPROVED_STORE_ID
    + "/"
    + APPROVED_CANVAS_ID
)
EXCLUDED_CANVAS_IDS = {
    # Team TwoComma. Do not export, fetch, or publish.
    "b7dd82c4-7324-4829-9d67-68ba4fcb7147",
}

CANVAS_URL_RE = re.compile(
    r"cursor\.com/canvas/(store-([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}))/"
    r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
)

_SECRET_RE = re.compile(
    r"("
    r"://[^/\s:@]+:[^/\s@]+@"
    r"|(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{8,}"
    r"|xox[baprs]-[A-Za-z0-9-]{8,}"
    r"|(?i:\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S+)"
    r")"
)


class MirrorError(Exception):
    """Fail-closed mirror error. The message is safe to print."""


def redact(text: str) -> str:
    """Remove credential-shaped substrings from a command error before display."""
    if not text:
        return ""
    redacted = _SECRET_RE.sub("[redacted]", text)
    redacted = re.sub(
        r"(?i)\b(authorization:\s*)\S+",
        r"\1[redacted]",
        redacted,
    )
    return redacted


def assert_target(target: str) -> str:
    if target not in TARGETS:
        known = ", ".join(sorted(TARGETS))
        raise MirrorError(
            f"unknown target page: {target!r}. Approved public targets: {known}. "
            "Team TwoComma, TCR, and TCT are not targets."
        )
    return TARGETS[target]


def assert_inside(root: str, path: str) -> str:
    root_real = os.path.realpath(root)
    path_real = os.path.realpath(path)
    if path_real != root_real and not path_real.startswith(root_real + os.sep):
        raise MirrorError(f"path escapes the mirror root: {path}")
    return path_real
