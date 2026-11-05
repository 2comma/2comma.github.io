"""GitHub Pages root hub links for the five TwoComma sites.

The Cloudflare hub keeps its external URLs. Only the copy prepared for the
repository root is rewritten, and only these hosts. Longer hosts are matched
before twocommanews.com so team, read, trade, and lfc are not swallowed.
"""

from __future__ import annotations

import re

# Longest hosts first. Each public site root maps to its GitHub path.
MIRROR_ORIGINS = (
    ("https://team.twocommanews.com", "/team/"),
    ("http://team.twocommanews.com", "/team/"),
    ("https://read.twocommanews.com", "/read/"),
    ("http://read.twocommanews.com", "/read/"),
    ("https://trade.twocommanews.com", "/trade/"),
    ("http://trade.twocommanews.com", "/trade/"),
    ("https://lfc.twocommanews.com", "/lfc/"),
    ("http://lfc.twocommanews.com", "/lfc/"),
    ("https://twocommanews.com", "/news/"),
    ("http://twocommanews.com", "/news/"),
)

_URL_ATTR = re.compile(
    r"""((?:href|src|data-src|action|data-lp|poster)=)(["'])(https?://[^"']+)(\2)""",
    re.I,
)
_CSS_URL = re.compile(r"""(url\(\s*["']?)(https?://[^"')]+)(["']?\s*\))""", re.I)


def map_mirror_url(url: str) -> str:
    """Map one absolute site URL onto its GitHub path. Other URLs stay put."""
    for origin, dest in MIRROR_ORIGINS:
        if url == origin or url == origin + "/":
            return dest
        prefix = origin + "/"
        if url.startswith(prefix):
            return dest.rstrip("/") + url[len(origin):]
    return url


def rewrite_root_hub_links(text: str) -> str:
    """Rewrite the five hub links in a root copy. The source string is not stored."""
    text = _URL_ATTR.sub(
        lambda match: match.group(1) + match.group(2) + map_mirror_url(match.group(3)) + match.group(4),
        text,
    )
    return _CSS_URL.sub(
        lambda match: match.group(1) + map_mirror_url(match.group(2)) + match.group(3),
        text,
    )
