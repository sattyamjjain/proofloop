#!/usr/bin/env python3
"""Forcing-function: pin the Rubber Duck cross-family-critic citation.

`skills/judge/analyzers/llm_judge.py` carries a module-docstring note
referencing GitHub Copilot CLI's Rubber Duck (2026-05-07) as
independent corroboration of the cross-family critic pattern verdict
already implements. This test pins:

1. The substring "Rubber Duck" appears in the analyzer source exactly
   once (no accidental duplication on future edits).
2. The primary URL — github.blog/changelog/2026-05-07-rubber-duck-...
   — appears verbatim. Aggregator URLs are NOT acceptable.

Why this test exists: cross-family-critic is a recognized product
surface at multiple vendors, not a verdict-novel concept. The
docstring note makes that legibility explicit. A future edit that
deletes the note (intentionally or by accident) would surface here.
Source: <https://code.claude.com/docs/en/changelog>-style external
anchor, recorded once.
"""
from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LLM_JUDGE_PATH = (
    PROJECT_ROOT / "skills" / "judge" / "analyzers" / "llm_judge.py"
)
PRIMARY_URL_FRAGMENT = (
    "github.blog/changelog/"
    "2026-05-07-rubber-duck-in-github-copilot-cli-now-supports-more-models"
)


class TestRubberDuckCitation(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = LLM_JUDGE_PATH.read_text(encoding="utf-8")

    def test_rubber_duck_substring_present_exactly_once(self) -> None:
        count = self.source.count("Rubber Duck")
        self.assertEqual(
            count,
            1,
            msg=(
                f"analyzers/llm_judge.py mentions 'Rubber Duck' "
                f"{count} time(s); expected exactly 1. The docstring "
                f"block citing the 2026-05-07 GitHub Copilot CLI "
                f"announcement is the single source of truth — do not "
                f"duplicate it elsewhere in the file."
            ),
        )

    def test_primary_url_fragment_present(self) -> None:
        self.assertIn(
            PRIMARY_URL_FRAGMENT,
            self.source,
            msg=(
                "analyzers/llm_judge.py is missing the GitHub Changelog "
                "primary URL fragment "
                f"({PRIMARY_URL_FRAGMENT!r}). Aggregator URLs are NOT "
                "acceptable; the citation must point at the GitHub "
                "Changelog primary."
            ),
        )


if __name__ == "__main__":
    unittest.main()
