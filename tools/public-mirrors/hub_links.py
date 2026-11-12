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


# Owner 2026-11-11: Slack, YouTube, and TikTok icons to the right of the YNWA
# title (order: Slack, YouTube, TikTok). Applied on every root-hub prepare so a
# later ZIP sync cannot drop the icons.
SLACK_HREF = "https://twocomma.slack.com"
YOUTUBE_HREF = "https://www.youtube.com/@TwoSnipped"
TIKTOK_HREF = "https://www.tiktok.com/@twosnipped"
SLACK_ICON_CSS = (
    ".ynwa-title{display:flex;align-items:center;gap:14px;margin:0 0 32px}"
    ".ynwa-title h1{margin:0}"
    "a.slack-icon,a.youtube-icon,a.tiktok-icon{display:inline-flex;flex-shrink:0;line-height:0}"
    "a.slack-icon svg,a.youtube-icon svg,a.tiktok-icon svg{width:2rem;height:2rem;display:block}"
)
_OLD_SLACK_ICON_CSS = (
    ".ynwa-title{display:flex;align-items:center;gap:14px;margin:0 0 32px}"
    ".ynwa-title h1{margin:0}"
    "a.slack-icon{display:inline-flex;flex-shrink:0;line-height:0}"
    "a.slack-icon svg{width:2rem;height:2rem;display:block}"
)
_SLACK_A = (
    f'<a class="slack-icon" href="{SLACK_HREF}" target="_blank" rel="noopener" aria-label="TwoComma Slack">'
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 127 127" width="32" height="32" aria-hidden="true">'
    '<path fill="#E01E5A" d="M27.2 80c0 7.3-5.9 13.2-13.2 13.2C6.7 93.2.8 87.3.8 80c0-7.3 5.9-13.2 13.2-13.2h13.2V80zm6.6 0c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2v33c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V80z"/>'
    '<path fill="#36C5F0" d="M47 27.2c-7.3 0-13.2-5.9-13.2-13.2C33.8 6.7 39.7.8 47 .8c7.3 0 13.2 5.9 13.2 13.2v13.2H47zm0 6.6c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H14c-7.3 0-13.2-5.9-13.2-13.2 0-7.3 5.9-13.2 13.2-13.2h33z"/>'
    '<path fill="#2EB67D" d="M99.8 47c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H99.8V47zm-6.6 0c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V14c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2v33z"/>'
    '<path fill="#ECB22E" d="M80 99.8c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V99.8H80zm0-6.6c-7.3 0-13.2-5.9-13.2-13.2 0-7.3 5.9-13.2 13.2-13.2h33c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H80z"/>'
    "</svg></a>"
)
_YOUTUBE_A = (
    f'<a class="youtube-icon" href="{YOUTUBE_HREF}" target="_blank" rel="noopener" aria-label="TwoSnipped on YouTube">'
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32" aria-hidden="true">'
    '<path fill="#FF0000" d="M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814z"/>'
    '<path fill="#FFF" d="M9.545 15.568V8.432L15.818 12l-6.273 3.568z"/>'
    "</svg></a>"
)
_TIKTOK_PATH = (
    "M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z"
)
_TIKTOK_A = (
    f'<a class="tiktok-icon" href="{TIKTOK_HREF}" target="_blank" rel="noopener" aria-label="TwoSnipped on TikTok">'
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-2 -2 28 28" width="32" height="32" aria-hidden="true">'
    f'<path fill="#25F4EE" d="{_TIKTOK_PATH}" transform="translate(-1.2 -0.8)"/>'
    f'<path fill="#FE2C55" d="{_TIKTOK_PATH}" transform="translate(1.2 0.8)"/>'
    f'<path fill="#000" d="{_TIKTOK_PATH}"/>'
    "</svg></a>"
)
SLACK_ICON_MARKUP = (
    f'<div class="ynwa-title"><h1>YNWA</h1>{_SLACK_A}{_YOUTUBE_A}{_TIKTOK_A}</div>'
)
_H1_YNWA = re.compile(r"<h1>\s*YNWA\s*</h1>")
_SLACK_ANCHOR = re.compile(r'<a class="slack-icon"[^>]*>.*?</a>', re.S)
_YOUTUBE_ANCHOR = re.compile(r'<a class="youtube-icon"[^>]*>.*?</a>', re.S)


def ensure_slack_icon(text: str) -> str:
    """Place Slack, YouTube, and TikTok icons to the right of the YNWA title. Idempotent."""
    if _H1_YNWA.search(text) and 'class="ynwa-title"' not in text and "class='ynwa-title'" not in text:
        text = _H1_YNWA.sub(SLACK_ICON_MARKUP, text, count=1)
    if 'class="ynwa-title"' in text or "class='ynwa-title'" in text:
        if _OLD_SLACK_ICON_CSS in text:
            text = text.replace(_OLD_SLACK_ICON_CSS, SLACK_ICON_CSS, 1)
        if "ynwa-title{" not in text and "</style>" in text:
            text = text.replace("</style>", SLACK_ICON_CSS + "</style>", 1)
        if "youtube-icon" not in text:
            if _SLACK_ANCHOR.search(text):
                text = _SLACK_ANCHOR.sub(lambda m: m.group(0) + _YOUTUBE_A + _TIKTOK_A, text, count=1)
        elif "tiktok-icon" not in text:
            if _YOUTUBE_ANCHOR.search(text):
                text = _YOUTUBE_ANCHOR.sub(lambda m: m.group(0) + _TIKTOK_A, text, count=1)
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
