"""Paths the YNWA hub may create, replace, or delete at the repository root.

Ownership is exact. The hub owns index.html, favicon.svg, team-logo.svg, and
image files directly under avatars/ and icons/. It does not own other root
files, and it does not own news/, lfc/, team/, tools/, ynwa/, or slack/.
The /slack page was removed on 2026-11-11; a root sync must not recreate it.
"""

from __future__ import annotations

import re

PROTECTED_PREFIXES = ("news/", "lfc/", "team/", "tools/", "ynwa/", "slack/")
PROTECTED_EXACT = {
    "README.md",
    ".gitignore",
    ".github",
    ".nojekyll",
}
OWNED_ROOT_FILES = frozenset({"index.html", "favicon.svg", "team-logo.svg"})
AVATAR_FILE = re.compile(
    r"^avatars/[a-z0-9][a-z0-9._-]{0,80}\.(png|jpg|jpeg|webp|gif|svg)$"
)
ICON_FILE = re.compile(
    r"^icons/[a-z0-9][a-z0-9._-]{0,80}\.(png|jpg|jpeg|webp|gif|svg|ico)$"
)


def is_protected(rel: str) -> bool:
    if not rel or rel.startswith("/") or rel.startswith("."):
        return True
    if rel in PROTECTED_EXACT:
        return True
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def is_owned(rel: str) -> bool:
    """True only for the three hub files or one image directly under avatars/ or icons/."""
    if is_protected(rel):
        return False
    if rel in OWNED_ROOT_FILES:
        return True
    return bool(AVATAR_FILE.fullmatch(rel) or ICON_FILE.fullmatch(rel))
