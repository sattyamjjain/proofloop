#!/usr/bin/env python3
"""Tests for /judge --explain rationale exporter (skills/judge/scripts/explain.py)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

import explain  # noqa: E402
import score  # noqa: E402


def _sample_card(
    skill: str = "code-review",
    composite: float = 8.4,
    with_llm: bool = False,
    with_contamination: bool = False,
    red_flags: list | None = None,
    bonuses: list | None = None,
) -> Dict[str, Any]:
    """A minimal scorecard JSON shaped like score.build_scorecard's output."""
    dims: Dict[str, Dict[str, Any]] = {}
    for dim in explain.DIMENSIONS:
        dim_entry: Dict[str, Any] = {
            "score": 8,
            "weight": 0.15,
            "weighted": 1.20,
            "justification": f"heuristic note on {dim}",
        }
        if with_llm:
            dim_entry["llm_score"] = 9
            dim_entry["llm_justification"] = f"llm thinks {dim} is strong"
        dims[dim] = dim_entry
    card = {
        "skill": skill,
        "timestamp": "2026-04-25T10:00:00Z",
        "composite_score": composite,
        "raw_composite": composite,
        "grade": "B+",
        "grade_label": "Good",
        "dimensions": dims,
        "red_flags": red_flags or [],
        "bonuses": bonuses or [],
        "adjustments": {
            "deduction": 0.0,
            "bonus": 0.0,
            "contamination": 1.5 if with_contamination else 0.0,
        },
        "summary": "Solid execution.",
        "one_liner": "Good code-review (B+) -- strong adherence",
        "critical_issues": [],
        "recommendations": ["Add tests for edge cases"],
        "rubric_used": "code-review",
        "transcript_lines": 42,
        "model": "claude-opus-4-7",
        "tokenizer_baseline": 1.35,
        "weights_source": "config",
    }
    return card


def _write_card(card: Dict[str, Any]) -> Path:
    fd = tempfile.NamedTemporaryFile(
        delete=False, suffix=".json", mode="w", encoding="utf-8",
    )
    json.dump(card, fd)
    fd.close()
    return Path(fd.name)


class TestLoadScorecard(unittest.TestCase):
    def test_load_existing(self) -> None:
        path = _write_card(_sample_card())
        try:
            card = explain.load_scorecard(path)
            self.assertEqual(card["skill"], "code-review")
        finally:
            path.unlink()

    def test_missing_file_raises(self) -> None:
        with self.assertRaises(ValueError):
            explain.load_scorecard(Path("/tmp/verdict-explain-missing.json"))

    def test_bad_json_raises(self) -> None:
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text("not-json", encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                explain.load_scorecard(path)
        finally:
            path.unlink()


class TestRenderJson(unittest.TestCase):
    def test_format_version_present(self) -> None:
        out = json.loads(explain.render_json(_sample_card()))
        self.assertEqual(out["format_version"], "explain.v1")

    def test_top_level_fields(self) -> None:
        out = json.loads(explain.render_json(_sample_card()))
        for key in (
            "skill", "timestamp", "rubric", "model", "composite", "grade",
            "summary", "dimensions", "adjustments", "evidence",
        ):
            self.assertIn(key, out)

    def test_dimensions_in_canonical_order(self) -> None:
        out = json.loads(explain.render_json(_sample_card()))
        names = [d["name"] for d in out["dimensions"]]
        self.assertEqual(names, explain.DIMENSIONS)

    def test_llm_fields_omitted_when_absent(self) -> None:
        out = json.loads(explain.render_json(_sample_card(with_llm=False)))
        for entry in out["dimensions"]:
            self.assertNotIn("llm_score", entry)
            self.assertNotIn("llm_justification", entry)

    def test_llm_fields_present_when_set(self) -> None:
        out = json.loads(explain.render_json(_sample_card(with_llm=True)))
        for entry in out["dimensions"]:
            self.assertEqual(entry["llm_score"], 9)
            self.assertIn("llm thinks", entry["llm_justification"])

    def test_contamination_round_trips_when_nonzero(self) -> None:
        out = json.loads(explain.render_json(_sample_card(with_contamination=True)))
        self.assertEqual(out["adjustments"]["contamination"], 1.5)

    def test_evidence_block_counts_red_flags_and_bonuses(self) -> None:
        out = json.loads(explain.render_json(_sample_card(
            red_flags=["foo", "bar"], bonuses=["baz"],
        )))
        self.assertEqual(out["evidence"]["red_flag_count"], 2)
        self.assertEqual(out["evidence"]["bonus_count"], 1)
        self.assertEqual(out["evidence"]["transcript_lines"], 42)


class TestRenderMarkdown(unittest.TestCase):
    def test_starts_with_h1(self) -> None:
        text = explain.render_markdown(_sample_card())
        self.assertTrue(text.startswith("# Verdict Scorecard"))

    def test_has_dimension_table_header(self) -> None:
        text = explain.render_markdown(_sample_card())
        self.assertIn("| Dimension | Score | Weight |", text)

    def test_each_dimension_appears_once(self) -> None:
        text = explain.render_markdown(_sample_card())
        for dim in explain.DIMENSIONS:
            count = text.count(f"| {dim} |")
            self.assertEqual(count, 1, f"expected 1 row for {dim}, got {count}")

    def test_llm_section_omitted_when_absent(self) -> None:
        text = explain.render_markdown(_sample_card(with_llm=False))
        self.assertNotIn("### LLM second opinion", text)

    def test_llm_section_present_when_set(self) -> None:
        text = explain.render_markdown(_sample_card(with_llm=True))
        self.assertIn("### LLM second opinion", text)
        self.assertIn("llm thinks correctness is strong", text)

    def test_red_flag_block_only_when_present(self) -> None:
        clean = explain.render_markdown(_sample_card())
        dirty = explain.render_markdown(_sample_card(
            red_flags=["destructive_command", "secret_leak"],
        ))
        self.assertNotIn("Red flags", clean)
        self.assertIn("Red flags", dirty)
        self.assertIn("destructive_command", dirty)

    def test_contamination_row_only_when_nonzero(self) -> None:
        zero = explain.render_markdown(_sample_card())
        nonzero = explain.render_markdown(_sample_card(with_contamination=True))
        self.assertNotIn("Contamination penalty", zero)
        self.assertIn("Contamination penalty", nonzero)

    def test_recommendations_listed(self) -> None:
        text = explain.render_markdown(_sample_card())
        self.assertIn("Add tests for edge cases", text)

    def test_evidence_block_present(self) -> None:
        text = explain.render_markdown(_sample_card())
        self.assertIn("transcript lines analysed", text)
        self.assertIn("42 transcript lines", text)


class TestCli(unittest.TestCase):
    def test_md_path_writes_to_out(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            card_path = _write_card(_sample_card())
            try:
                out_path = tmp / "explain.md"
                rc = explain.main([
                    "--scorecard", str(card_path),
                    "--format", "md",
                    "--out", str(out_path),
                ])
                self.assertEqual(rc, 0)
                self.assertTrue(out_path.is_file())
                self.assertIn("# Verdict Scorecard", out_path.read_text())
            finally:
                card_path.unlink()

    def test_json_path_writes_valid_schema(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            card_path = _write_card(_sample_card())
            try:
                out_path = tmp / "explain.json"
                rc = explain.main([
                    "--scorecard", str(card_path),
                    "--format", "json",
                    "--out", str(out_path),
                ])
                self.assertEqual(rc, 0)
                payload = json.loads(out_path.read_text())
                self.assertEqual(payload["format_version"], "explain.v1")
                self.assertEqual(len(payload["dimensions"]), 7)
            finally:
                card_path.unlink()

    def test_missing_scorecard_returns_nonzero(self) -> None:
        rc = explain.main([
            "--scorecard", "/tmp/verdict-explain-no-such",
            "--format", "md",
        ])
        self.assertNotEqual(rc, 0)


class TestTruncateMarkdown(unittest.TestCase):
    """O2: Markdown output cap to stay under GitHub's PR comment limit."""

    def test_under_cap_passthrough(self) -> None:
        body = "# small\n\nbody text"
        self.assertEqual(explain.truncate_markdown(body, max_chars=1000), body)

    def test_zero_cap_disables_truncation(self) -> None:
        body = "x" * 100_000
        self.assertEqual(explain.truncate_markdown(body, max_chars=0), body)

    def test_truncation_footer_with_url(self) -> None:
        body = "x" * 10_000
        out = explain.truncate_markdown(
            body, max_chars=4000,
            scorecard_url="https://example.com/scorecard/abc",
        )
        self.assertLessEqual(len(out), 4000)
        self.assertIn("Output truncated", out)
        self.assertIn("https://example.com/scorecard/abc", out)

    def test_truncation_footer_without_url(self) -> None:
        body = "x" * 10_000
        out = explain.truncate_markdown(body, max_chars=4000)
        self.assertLessEqual(len(out), 4000)
        self.assertIn("Output truncated", out)
        self.assertIn("--max-evidence-chars=0", out)

    def test_default_cap_is_4000(self) -> None:
        self.assertEqual(explain.DEFAULT_MAX_EVIDENCE_CHARS, 4000)

    def test_real_scorecard_renders_under_default_cap(self) -> None:
        body = explain.render_markdown(_sample_card())
        capped = explain.truncate_markdown(body)
        self.assertEqual(body, capped)

    def test_synthetically_long_scorecard_gets_capped(self) -> None:
        # Build a card whose summary dwarfs the default cap. (Per-dim
        # justifications are column-truncated to 140 chars in the
        # rendered table, so they don't inflate the output the way
        # an unbounded summary string does.)
        card = _sample_card()
        card["summary"] = "long " * 1000  # ~5KB
        body = explain.render_markdown(card)
        self.assertGreater(len(body), 4000)
        capped = explain.truncate_markdown(body)
        self.assertLessEqual(len(capped), 4000)
        self.assertIn("Output truncated", capped)


class TestCliMaxEvidenceChars(unittest.TestCase):
    def test_md_output_respects_cap(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            card = _sample_card()
            card["summary"] = "long " * 1000
            card_path = _write_card(card)
            try:
                out_path = tmp / "explain.md"
                rc = explain.main([
                    "--scorecard", str(card_path),
                    "--format", "md",
                    "--max-evidence-chars", "2000",
                    "--scorecard-url", "https://verdict.example/sc/1",
                    "--out", str(out_path),
                ])
                self.assertEqual(rc, 0)
                rendered = out_path.read_text(encoding="utf-8")
                self.assertLessEqual(len(rendered), 2000)
                self.assertIn("verdict.example", rendered)
            finally:
                card_path.unlink()

    def test_zero_cap_emits_full_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            card = _sample_card()
            card["summary"] = "long " * 1000
            card_path = _write_card(card)
            try:
                out_path = tmp / "explain.md"
                rc = explain.main([
                    "--scorecard", str(card_path),
                    "--format", "md",
                    "--max-evidence-chars", "0",
                    "--out", str(out_path),
                ])
                self.assertEqual(rc, 0)
                rendered = out_path.read_text(encoding="utf-8")
                self.assertGreater(len(rendered), 4000)
                self.assertNotIn("Output truncated", rendered)
            finally:
                card_path.unlink()

    def test_json_output_ignores_cap(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            card_path = _write_card(_sample_card())
            try:
                out_path = tmp / "explain.json"
                rc = explain.main([
                    "--scorecard", str(card_path),
                    "--format", "json",
                    "--max-evidence-chars", "100",
                    "--out", str(out_path),
                ])
                self.assertEqual(rc, 0)
                payload = json.loads(out_path.read_text(encoding="utf-8"))
                self.assertEqual(payload["format_version"], "explain.v1")
            finally:
                card_path.unlink()


class TestRoundTripFromBuildScorecard(unittest.TestCase):
    """End-to-end: build a real scorecard via score.py, then explain it."""

    def test_real_scorecard_renders(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"/code-review look at this"}\n'
                '{"role":"assistant","content":"LGTM, ship it."}\n',
                encoding="utf-8",
            )
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(tmp / "scores"),
            )
            saved_path = Path(card["_saved_to"])
            md = explain.render_markdown(explain.load_scorecard(saved_path))
            self.assertIn("# Verdict Scorecard", md)
            self.assertIn("code-review", md)


if __name__ == "__main__":
    unittest.main()
