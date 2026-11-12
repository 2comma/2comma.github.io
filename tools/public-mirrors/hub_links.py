"""GitHub Pages root hub links for the public mirrors.

The Cloudflare hub keeps its external URLs. Only the copy prepared for the
repository root is rewritten. Read and Trade stay on their gated domains.
Longer hosts are matched before twocommanews.com so team and lfc are not swallowed.
"""

from __future__ import annotations

import re

# Public phase only. Read and Trade are not local paths.
MIRROR_ORIGINS = (
    ("https://team.twocommanews.com", "/team/"),
    ("http://team.twocommanews.com", "/team/"),
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


# Owner 2026-11-11: Slack icon to the right of the YNWA title, linking to the workspace.
# Applied on every root-hub prepare so a later ZIP sync cannot drop the icon.
SLACK_HREF = "https://twocomma.slack.com"
SLACK_ICON_CSS = (
    ".ynwa-title{display:flex;align-items:center;gap:14px;margin:0 0 32px}"
    ".ynwa-title h1{margin:0}"
    "a.slack-icon{display:inline-flex;flex-shrink:0;line-height:0}"
    "a.slack-icon svg{width:2rem;height:2rem;display:block}"
)
SLACK_ICON_MARKUP = (
    '<div class="ynwa-title"><h1>YNWA</h1>'
    f'<a class="slack-icon" href="{SLACK_HREF}" target="_blank" rel="noopener" aria-label="TwoComma Slack">'
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 127 127" width="32" height="32" aria-hidden="true">'
    '<path fill="#E01E5A" d="M27.2 80c0 7.3-5.9 13.2-13.2 13.2C6.7 93.2.8 87.3.8 80c0-7.3 5.9-13.2 13.2-13.2h13.2V80zm6.6 0c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2v33c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V80z"/>'
    '<path fill="#36C5F0" d="M47 27.2c-7.3 0-13.2-5.9-13.2-13.2C33.8 6.7 39.7.8 47 .8c7.3 0 13.2 5.9 13.2 13.2v13.2H47zm0 6.6c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H14c-7.3 0-13.2-5.9-13.2-13.2 0-7.3 5.9-13.2 13.2-13.2h33z"/>'
    '<path fill="#2EB67D" d="M99.8 47c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H99.8V47zm-6.6 0c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V14c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2v33z"/>'
    '<path fill="#ECB22E" d="M80 99.8c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V99.8H80zm0-6.6c-7.3 0-13.2-5.9-13.2-13.2 0-7.3 5.9-13.2 13.2-13.2h33c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H80z"/>'
    "</svg></a></div>"
)
_H1_YNWA = re.compile(r"<h1>\s*YNWA\s*</h1>")


def ensure_slack_icon(text: str) -> str:
    """Place the Slack icon immediately to the right of the YNWA title. Idempotent."""
    if _H1_YNWA.search(text) and 'class="ynwa-title"' not in text and "class='ynwa-title'" not in text:
        text = _H1_YNWA.sub(SLACK_ICON_MARKUP, text, count=1)
    if 'class="ynwa-title"' in text or "class='ynwa-title'" in text:
        if "ynwa-title{" not in text and "</style>" in text:
            text = text.replace("</style>", SLACK_ICON_CSS + "</style>", 1)
    return text


def rewrite_root_hub_links(text: str) -> str:
    """Rewrite the public hub links in a root copy. The source string is not stored."""
    text = _URL_ATTR.sub(
        lambda match: match.group(1) + match.group(2) + map_mirror_url(match.group(3)) + match.group(4),
        text,
    )
    text = _CSS_URL.sub(
        lambda match: match.group(1) + map_mirror_url(match.group(2)) + match.group(3),
        text,
    )
    return ensure_slack_icon(text)
