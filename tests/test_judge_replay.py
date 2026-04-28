#!/usr/bin/env python3
"""Tests for the verdict judge-replay CLI (S3, v1.4.1)."""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))
import judge_replay  # noqa: E402
import score  # noqa: E402


def _baseline(per_dim_score: int = 7, composite: float = 7.5) -> dict:
    return {
        "skill": "code-review",
        "composite_score": composite,
        "dimensions": {
            dim: {"score": per_dim_score, "weight": 0.15, "weighted": 1.0,
                  "justification": ""}
            for dim in (
                "correctness", "completeness", "adherence", "actionability",
                "efficiency", "safety", "consistency",
            )
        },
    }


class TestLoadScorecard(unittest.TestCase):
    def test_missing_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            judge_replay.load_scorecard("/tmp/verdict-no-such.json")

    def test_malformed_raises(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "bad.json"
            p.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError):
                judge_replay.load_scorecard(str(p))


class TestDiffScorecards(unittest.TestCase):
    def test_no_change(self) -> None:
        diff = judge_replay.diff_scorecards(
            _baseline(), _baseline(),
            tolerance=0.5, composite_tolerance=0.3,
        )
        self.assertTrue(diff["passed"])
        self.assertEqual(diff["composite_delta"], 0.0)
        self.assertEqual(diff["breached_dimensions"], [])

    def test_within_tolerance(self) -> None:
        candidate = _baseline()
        candidate["dimensions"]["correctness"]["score"] = 7  # delta 0.0
        diff = judge_replay.diff_scorecards(
            candidate, _baseline(), tolerance=0.5, composite_tolerance=0.3,
        )
        self.assertTrue(diff["passed"])

    def test_dimension_breach(self) -> None:
        candidate = _baseline()
        candidate["dimensions"]["correctness"]["score"] = 9  # delta +2.0
        diff = judge_replay.diff_scorecards(
            candidate, _baseline(),
            tolerance=0.5, composite_tolerance=10.0,  # huge composite tol
        )
        self.assertFalse(diff["passed"])
        self.assertIn("correctness", diff["breached_dimensions"])

    def test_composite_breach(self) -> None:
        candidate = _baseline(composite=8.5)
        diff = judge_replay.diff_scorecards(
            candidate, _baseline(composite=7.5),
            tolerance=10.0, composite_tolerance=0.3,
        )
        self.assertFalse(diff["passed"])
        self.assertTrue(diff["composite_breach"])

    def test_missing_dimension_skipped(self) -> None:
        candidate = _baseline()
        baseline = {"composite_score": 7.5, "dimensions": {
            "correctness": {"score": 7},
        }}
        diff = judge_replay.diff_scorecards(
            candidate, baseline,
            tolerance=0.5, composite_tolerance=0.3,
        )
        # Only correctness is paired.
        self.assertEqual(len(diff["per_dimension"]), 1)
        self.assertIn("correctness", diff["per_dimension"])


class TestReplay(unittest.TestCase):
    def test_replay_matches_self(self) -> None:
        # Replaying a scorecard against itself must always pass —
        # this is the "is the replay deterministic?" floor.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"review this PR"}\n'
                '{"role":"assistant","content":"LGTM"}\n',
                encoding="utf-8",
            )
            initial = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            baseline_path = tmp / "baseline.json"
            baseline_path.write_text(json.dumps(initial), encoding="utf-8")
            diff, _ = judge_replay.replay(
                transcript_path=str(transcript),
                skill="code-review",
                rubric_dir=str(RUBRICS_DIR),
                baseline_scorecard_path=str(baseline_path),
                tolerance=0.5,
                composite_tolerance=0.3,
            )
            self.assertTrue(diff["passed"])

    def test_replay_detects_synthetic_drift(self) -> None:
        # Hand-crafted baseline with all-9s — current heuristic
        # scoring won't reproduce that, so it should drift.
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"review this"}\n'
                '{"role":"assistant","content":"LGTM"}\n',
                encoding="utf-8",
            )
            baseline_path = tmp / "baseline.json"
            baseline_path.write_text(
                json.dumps(_baseline(per_dim_score=10, composite=10.0)),
                encoding="utf-8",
            )
            diff, _ = judge_replay.replay(
                transcript_path=str(transcript),
                skill="code-review",
                rubric_dir=str(RUBRICS_DIR),
                baseline_scorecard_path=str(baseline_path),
                tolerance=0.5,
                composite_tolerance=0.3,
            )
            self.assertFalse(diff["passed"])


class TestCli(unittest.TestCase):
    def test_passing_returns_zero(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"hello"}\n'
                '{"role":"assistant","content":"hi"}\n',
                encoding="utf-8",
            )
            initial = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            baseline_path = tmp / "baseline.json"
            baseline_path.write_text(json.dumps(initial), encoding="utf-8")
            with patch("sys.stdout", io.StringIO()):
                rc = judge_replay.main([
                    "--transcript", str(transcript),
                    "--skill", "code-review",
                    "--rubric-dir", str(RUBRICS_DIR),
                    "--baseline-scorecard", str(baseline_path),
                ])
            self.assertEqual(rc, 0)

    def test_missing_baseline_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"hi"}\n', encoding="utf-8",
            )
            with patch("sys.stderr", io.StringIO()) as err:
                rc = judge_replay.main([
                    "--transcript", str(transcript),
                    "--skill", "code-review",
                    "--rubric-dir", str(RUBRICS_DIR),
                    "--baseline-scorecard", "/tmp/verdict-no-such.json",
                ])
            self.assertEqual(rc, 2)
            self.assertIn("baseline scorecard not found", err.getvalue())

    def test_drift_returns_one(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"hi"}\n', encoding="utf-8",
            )
            baseline_path = tmp / "baseline.json"
            baseline_path.write_text(
                json.dumps(_baseline(per_dim_score=10, composite=10.0)),
                encoding="utf-8",
            )
            with patch("sys.stdout", io.StringIO()):
                rc = judge_replay.main([
                    "--transcript", str(transcript),
                    "--skill", "code-review",
                    "--rubric-dir", str(RUBRICS_DIR),
                    "--baseline-scorecard", str(baseline_path),
                ])
            self.assertEqual(rc, 1)

    def test_json_output_returns_diff(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            transcript = tmp / "tx.jsonl"
            transcript.write_text(
                '{"role":"user","content":"hi"}\n', encoding="utf-8",
            )
            initial = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(RUBRICS_DIR),
                scores_dir=str(tmp / "scores"),
            )
            baseline_path = tmp / "baseline.json"
            baseline_path.write_text(json.dumps(initial), encoding="utf-8")
            buf = io.StringIO()
            with patch("sys.stdout", buf):
                rc = judge_replay.main([
                    "--transcript", str(transcript),
                    "--skill", "code-review",
                    "--rubric-dir", str(RUBRICS_DIR),
                    "--baseline-scorecard", str(baseline_path),
                    "--output", "json",
                ])
            self.assertEqual(rc, 0)
            payload = json.loads(buf.getvalue())
            self.assertIn("per_dimension", payload)
            self.assertTrue(payload["passed"])


if __name__ == "__main__":
    unittest.main()
