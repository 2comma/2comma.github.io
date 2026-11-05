"""Paths the YNWA hub may create, replace, or delete at the repository root.

news/, lfc/, team/, tools/, and ynwa/ are not owned. A root sync cannot stage
them. Owned paths are the public hub's root files, avatars/, and icons/.
"""

from __future__ import annotations

PROTECTED_PREFIXES = ("news/", "lfc/", "team/", "tools/", "ynwa/")
PROTECTED_EXACT = {
    "README.md",
    ".gitignore",
    ".github",
    ".nojekyll",
}


def is_protected(rel: str) -> bool:
    if not rel or rel.startswith("/") or rel.startswith("."):
        return True
    if rel in PROTECTED_EXACT:
        return True
    return any(rel == prefix.rstrip("/") or rel.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def is_owned(rel: str) -> bool:
    from ynwa_prepare import allowed

    return bool(rel) and not is_protected(rel) and allowed(rel)
