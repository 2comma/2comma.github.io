"""Which of the five hub paths this public repository may publish.

The root hub may link to all five. Publishing content is a separate decision.
Read, Trade, and the Team TwoComma canvas behind team.twocommanews.com are
not public mirror targets. /team/ remains the sanitized Team Status snapshot.
"""

from __future__ import annotations

BLOCKED_TARGETS = {
    "read": (
        "Read is a server-side password gate with noindex. "
        "GitHub Pages on 2comma.github.io cannot enforce that gate. "
        "No Read content is published."
    ),
    "tcr": (
        "Read is a server-side password gate with noindex. "
        "No Read content is published."
    ),
    "trade": (
        "Trade is a server-side password gate with noindex. "
        "GitHub Pages on 2comma.github.io cannot enforce that gate. "
        "No Trade content is published."
    ),
    "tct": (
        "Trade is a server-side password gate with noindex. "
        "No Trade content is published."
    ),
    "team-twocomma": (
        "team.twocommanews.com points at the private Team TwoComma canvas, "
        "not the sanitized Team Status snapshot at /team/. "
        "No raw Team mirror is published."
    ),
}


def block_reason(target: str) -> str | None:
    return BLOCKED_TARGETS.get(target)
