#!/usr/bin/env python3
"""Ensure the v1.2.0 rubric pack files are well-formed and parseable."""
from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "judge" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
import score  # noqa: E402

NEW_RUBRICS: list[str] = [
    "code-review-aider-polyglot",
    "skill-compliance",
    "model-spec-compliance",
]

REQUIRED_DIMENSIONS: list[str] = [
    "Correctness", "Completeness", "Adherence",
    "Actionability", "Efficiency", "Safety", "Consistency",
]


class TestRubricFilesPresent(unittest.TestCase):
    def test_all_three_rubrics_exist(self) -> None:
        for name in NEW_RUBRICS:
            path = RUBRICS_DIR / f"{name}.md"
            self.assertTrue(path.is_file(), f"missing rubric file: {path}")

    def test_all_three_have_source_signal_citation(self) -> None:
        """Every new rubric must cite the 2026-04-20 signal it rides."""
        pattern = re.compile(r"source_signal\s*:", re.IGNORECASE)
        for name in NEW_RUBRICS:
            text = (RUBRICS_DIR / f"{name}.md").read_text(encoding="utf-8")
            self.assertRegex(
                text, pattern,
                f"{name}: missing 'source_signal:' header citing the origin post",
            )


class TestRubricStructure(unittest.TestCase):
    def test_every_rubric_contains_every_dimension_heading(self) -> None:
        for name in NEW_RUBRICS:
            text = (RUBRICS_DIR / f"{name}.md").read_text(encoding="utf-8")
            for dim in REQUIRED_DIMENSIONS:
                self.assertIn(
                    f"### {dim}",
                    text,
                    f"{name}: missing '### {dim}' heading",
                )

    def test_parser_extracts_criteria_for_every_dimension(self) -> None:
        for name in NEW_RUBRICS:
            text = (RUBRICS_DIR / f"{name}.md").read_text(encoding="utf-8")
            criteria = score._parse_rubric_criteria(text)
            for dim in ["correctness", "completeness", "adherence",
                        "actionability", "efficiency", "safety", "consistency"]:
                self.assertIn(
                    dim, criteria,
                    f"{name}: parser failed to extract '{dim}' section",
                )
                self.assertTrue(
                    criteria[dim].strip(),
                    f"{name}: '{dim}' section is empty after parse",
                )


class TestRubricResolution(unittest.TestCase):
    def test_load_rubric_resolves_each_new_rubric(self) -> None:
        for name in NEW_RUBRICS:
            resolved_name, text = score.load_rubric(str(RUBRICS_DIR), name)
            self.assertEqual(resolved_name, name)
            self.assertGreater(len(text), 500)


class TestRubricsScore(unittest.TestCase):
    """End-to-end: scoring a transcript against each new rubric produces
    a schema-conformant scorecard (proves N3 integrates with A1)."""

    def _tx(self, tmp: Path) -> Path:
        p = tmp / "tx.jsonl"
        p.write_text(
            json.dumps({"role": "user", "content": "/code-review patch src/foo.py"}) + "\n"
            + json.dumps({"role": "assistant", "content": "Patch applied; tests green."}) + "\n",
            encoding="utf-8",
        )
        return p

    def test_each_rubric_produces_scorecard(self) -> None:
        import tempfile
        for name in NEW_RUBRICS:
            with tempfile.TemporaryDirectory() as t:
                tmp = Path(t)
                card = score.build_scorecard(
                    skill_name=name,
                    transcript_path=str(self._tx(tmp)),
                    rubric_dir=str(RUBRICS_DIR),
                    scores_dir=str(tmp / "scores"),
                    config_path=str(PROJECT_ROOT / "judge-config.json"),
                )
                self.assertEqual(card["rubric_used"], name)
                self.assertEqual(set(card["dimensions"]), {
                    "correctness", "completeness", "adherence",
                    "actionability", "efficiency", "safety", "consistency",
                })


if __name__ == "__main__":
    unittest.main()
