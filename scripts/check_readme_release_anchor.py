#!/usr/bin/env python3
"""Verify README.md "Latest release" anchor matches CHANGELOG's top entry.

Stdlib-only. Exits 0 on match, 1 on mismatch (with a one-line
diagnostic), 2 on missing/malformed inputs.

Usage:
    python3 scripts/check_readme_release_anchor.py

Reads ``CHANGELOG.md`` for the most recent ``## [X.Y.Z] - YYYY-MM-DD``
heading, then asserts ``README.md`` carries a matching
``releases/tag/vX.Y.Z`` link.

Design: the README's release-anchor surface is the user-visible drift
that our v2.0.0 / v2.0.1 cycle exposed (the anchor was three releases
behind for over a month). This check is the forcing function so the
two files land in the same PR.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG_MD = REPO_ROOT / "CHANGELOG.md"
README_MD = REPO_ROOT / "README.md"

_RELEASED_HEADING = re.compile(
    r"^##\s+\[(?P<v>\d+\.\d+\.\d+)\]\s+-\s+\d{4}-\d{2}-\d{2}",
    re.MULTILINE,
)
_README_TAG_LINK = re.compile(
    r"releases/tag/v(?P<v>\d+\.\d+\.\d+)",
)


def _latest_changelog_release() -> str | None:
    if not CHANGELOG_MD.is_file():
        print(f"Error: {CHANGELOG_MD} does not exist.", file=sys.stderr)
        return None
    match = _RELEASED_HEADING.search(CHANGELOG_MD.read_text(encoding="utf-8"))
    if match is None:
        print(
            f"Error: {CHANGELOG_MD} has no '## [X.Y.Z] - YYYY-MM-DD' heading.",
            file=sys.stderr,
        )
        return None
    return match.group("v")


def _readme_advertises(version: str) -> bool:
    if not README_MD.is_file():
        print(f"Error: {README_MD} does not exist.", file=sys.stderr)
        return False
    text = README_MD.read_text(encoding="utf-8")
    for match in _README_TAG_LINK.finditer(text):
        if match.group("v") == version:
            return True
    return False


def main() -> int:
    expected = _latest_changelog_release()
    if expected is None:
        return 2
    if _readme_advertises(expected):
        print(
            f"README.md ✓ advertises latest CHANGELOG release v{expected}."
        )
        return 0
    print(
        f"README.md does not link to releases/tag/v{expected} — "
        f"the 'Latest release' anchor is stale relative to CHANGELOG.md.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
