"""Reject sensitive identifiers. This module never rewrites them away."""

from __future__ import annotations

import re

from common import (
    APPROVED_CANVAS_ID,
    APPROVED_CANVAS_URL,
    APPROVED_STORE_ID,
    CANVAS_URL_RE,
    EXCLUDED_CANVAS_IDS,
    MirrorError,
)

# High-confidence patterns. The sanitized Team Status text and the public YNWA
# hub do not match them. A hit aborts the export.
PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")),
    ("ups_tracking", re.compile(r"\b1Z(?:[\s\-]?[A-Z0-9]){16}\b", re.I)),
    ("long_digit_identifier", re.compile(r"\b\d{8,}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "phone",
        re.compile(r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"),
    ),
    (
        "policy_identifier",
        re.compile(
            r"(?i)\b(?:policy|certificate)\s*(?:number|no\.?|#|id)\b\s*[:#-]?\s*[A-Z0-9][A-Z0-9\-]{3,}"
        ),
    ),
    (
        "tracking_identifier",
        re.compile(
            r"(?i)\btracking\s*(?:number|no\.?|#|id)\b\s*[:#-]?\s*[A-Z0-9][A-Z0-9\-]{3,}"
        ),
    ),
    (
        "account_identifier",
        re.compile(
            r"(?i)\b(?:account|member|customer)\s*(?:number|no\.?|#|id)\b\s*[:#-]?\s*[A-Z0-9][A-Z0-9\-]{3,}"
        ),
    ),
    (
        "secret_assignment",
        re.compile(r"(?i)\b(?:password|passwd|secret|api[_-]?key|token)\s*[:=]\s*\S+"),
    ),
    ("github_token", re.compile(r"\b(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{8,}")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{8,}")),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{8,}")),
    ("url_credentials", re.compile(r"://[^/\s:@]+:[^/\s@]+@")),
]

UUID_RE = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
BINARY_MARKERS = (
    b"-----BEGIN",
    b"ghp_",
    b"github_pat_",
    b"xoxb-",
    b"xoxp-",
    b"AKIA",
)


def scan_text(text: str, label: str, *, allow_canvas_provenance: bool = False) -> None:
    """Reject published text that still contains identifiers or credentials."""
    for name, pattern in PATTERNS:
        if pattern.search(text):
            raise MirrorError(
                f"sensitive {name} in {label}. "
                "The export was not modified and nothing was published."
            )
    for canvas_id in EXCLUDED_CANVAS_IDS:
        if canvas_id in text:
            raise MirrorError(
                f"excluded Team TwoComma canvas id in {label}. Nothing was published."
            )
    if allow_canvas_provenance:
        _check_provenance(text, label)
        return
    if "cursor.com/canvas/" in text or UUID_RE.search(text):
        raise MirrorError(
            f"canvas locator in {label}. Public page text must not carry it. "
            "Nothing was published."
        )


def scan_bytes(data: bytes, label: str) -> None:
    for marker in BINARY_MARKERS:
        if marker in data:
            raise MirrorError(
                f"sensitive marker in {label}. Nothing was published."
            )


def _check_provenance(text: str, label: str) -> None:
    if APPROVED_CANVAS_URL not in text:
        raise MirrorError(
            f"{label} does not name the approved Team Status canvas. "
            "Nothing was published."
        )
    if "/team/" not in text or "Team Status" not in text:
        raise MirrorError(
            f"{label} does not identify the /team/ Team Status target. "
            "Nothing was published."
        )
    matches = CANVAS_URL_RE.findall(text)
    if not matches:
        raise MirrorError(f"{label} has no canvas URL. Nothing was published.")
    for _store_token, store_id, canvas_id in matches:
        if store_id != APPROVED_STORE_ID or canvas_id != APPROVED_CANVAS_ID:
            raise MirrorError(
                f"{label} names a canvas other than Team Status. Nothing was published."
            )
    for canvas_id in EXCLUDED_CANVAS_IDS:
        if canvas_id in text:
            raise MirrorError(
                f"{label} names the excluded Team TwoComma canvas. Nothing was published."
            )
