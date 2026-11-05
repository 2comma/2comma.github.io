"""The only GitHub Pages document allowed at /ynwa/.

The public YNWA site stays on its own deploy. GitHub Pages /ynwa/ redirects to
the site root. The HTML file next to this module is the source of those bytes
so a handoff cannot replace them with the duplicate hub.
"""

from __future__ import annotations

from pathlib import Path

from common import MirrorError

ROOT_URL = "https://2comma.github.io/"
REDIRECT_HTML = (
    Path(__file__).with_name("fixtures").joinpath("ynwa-redirect", "index.html").read_bytes()
)


def redirect_files() -> dict[str, bytes]:
    return {"index.html": REDIRECT_HTML, ".nojekyll": b""}


def assert_redirect_tree(files: dict[str, bytes]) -> None:
    """Reject every YNWA tree except the root redirect."""
    if set(files) != {"index.html", ".nojekyll"} or files.get(".nojekyll") != b"":
        raise MirrorError(
            "refusing to publish duplicate YNWA content over the /ynwa/ redirect. "
            f"/ynwa/ only redirects to {ROOT_URL}."
        )
    if files.get("index.html") != REDIRECT_HTML:
        raise MirrorError(
            "refusing to replace the /ynwa/ redirect. "
            f"The page must send visitors to {ROOT_URL}."
        )
