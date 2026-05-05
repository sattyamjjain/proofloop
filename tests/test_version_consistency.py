#!/usr/bin/env python3
"""Forcing function: version stamps must agree across the manifests + CHANGELOG.

PR #26 (v2.0.1 ship) cut a fresh CHANGELOG entry but did NOT bump
``.claude-plugin/plugin.json``, ``marketplace.json``, or
``skills/judge/SKILL.md`` frontmatter. The marketplace listing
therefore advertised v2.0.0 even though the code was v2.0.1.

This test pins:

- ``plugin.json.version`` == latest ``## [X.Y.Z]`` in CHANGELOG.md
- ``marketplace.json.plugins[*].version`` == same (when the field is present)
- ``SKILL.md`` frontmatter ``version`` == same

Adding a fresh CHANGELOG heading without bumping the other surfaces
fails this test loudly. The test assumes the CHANGELOG follows
Keep-a-Changelog ``## [X.Y.Z] - YYYY-MM-DD`` heading shape, which
is the convention used since v1.0.0.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_JSON = PROJECT_ROOT / ".claude-plugin" / "plugin.json"
MARKETPLACE_JSON = PROJECT_ROOT / ".claude-plugin" / "marketplace.json"
SKILL_MD = PROJECT_ROOT / "skills" / "judge" / "SKILL.md"
CHANGELOG_MD = PROJECT_ROOT / "CHANGELOG.md"

# Latest released version is the FIRST ``## [X.Y.Z] - ...`` heading
# (an `[Unreleased]` heading immediately above is allowed and skipped).
_RELEASED_HEADING = re.compile(
    r"^##\s+\[(?P<v>\d+\.\d+\.\d+)\]\s+-\s+\d{4}-\d{2}-\d{2}",
    re.MULTILINE,
)
_FRONTMATTER_VERSION = re.compile(r'^version:\s*"?(\d+\.\d+\.\d+)"?', re.MULTILINE)


def _changelog_latest_released() -> str:
    text = CHANGELOG_MD.read_text(encoding="utf-8")
    match = _RELEASED_HEADING.search(text)
    if match is None:
        raise AssertionError(
            "CHANGELOG.md has no ``## [X.Y.Z] - YYYY-MM-DD`` heading. "
            "The latest released version cannot be inferred."
        )
    return match.group("v")


class TestVersionConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.expected = _changelog_latest_released()

    def test_plugin_json_version_matches_changelog(self) -> None:
        manifest = json.loads(PLUGIN_JSON.read_text(encoding="utf-8"))
        self.assertEqual(
            manifest.get("version"),
            self.expected,
            f".claude-plugin/plugin.json version ({manifest.get('version')!r}) "
            f"must match the latest CHANGELOG release ({self.expected!r}).",
        )

    def test_marketplace_json_versions_match_changelog(self) -> None:
        market = json.loads(MARKETPLACE_JSON.read_text(encoding="utf-8"))
        plugins = market.get("plugins") or []
        for i, plugin in enumerate(plugins):
            if not isinstance(plugin, dict) or "version" not in plugin:
                continue
            self.assertEqual(
                plugin["version"],
                self.expected,
                f"marketplace.json plugins[{i}].version "
                f"({plugin['version']!r}) must match the latest "
                f"CHANGELOG release ({self.expected!r}).",
            )

    def test_skill_md_frontmatter_version_matches_changelog(self) -> None:
        # Read only the frontmatter (everything before the second ``---``).
        text = SKILL_MD.read_text(encoding="utf-8")
        if not text.startswith("---"):
            self.fail("SKILL.md is missing a YAML frontmatter block.")
        end = text.find("\n---", 3)
        frontmatter = text[: end if end != -1 else len(text)]
        match = _FRONTMATTER_VERSION.search(frontmatter)
        self.assertIsNotNone(
            match,
            "SKILL.md frontmatter is missing a ``version:`` field.",
        )
        assert match is not None
        self.assertEqual(
            match.group(1),
            self.expected,
            f"SKILL.md frontmatter version ({match.group(1)!r}) must "
            f"match the latest CHANGELOG release ({self.expected!r}).",
        )


if __name__ == "__main__":
    unittest.main()
