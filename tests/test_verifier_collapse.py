#!/usr/bin/env python3
"""Tests for the verifier-collapse detector (v2.0.4).

Covers:

1. ``_detect_verifier_collapse`` short-circuits when config is missing
   or ``enabled=false``; no false positives below ``min_samples``;
   fires on a flatlined-top window; does NOT fire when variance
   exceeds ``max_std_dev``.
2. ``_analyze_consistency`` composes the dock with the existing
   variance-based reasoning so a collapsed verifier nets to a dock
   rather than the prior +1 low-variance bonus, and the returned dict
   carries ``verifier_collapse`` / ``verifier_collapse_reason`` /
   ``verifier_collapse_stats``.
3. ``build_scorecard`` end-to-end produces a scorecard with the
   top-level ``verifier_collapse`` mirror.
4. ``explain.v1`` JSON renders the top-level flag + the per-dim
   reason + stats; Markdown renders the ``⚠️ Verifier collapse
   detected`` callout, anchored on the Soft-SVeRL project anchor
   (no sibling benchmarks named).
5. ``hooks/judge-on-stop.sh`` honours ``gate_mode``:
   ``warn`` -> exit 0 + stderr warning; ``fail`` -> exit 2 + stderr
   BLOCKED line; ``off`` -> exit 0 + silent.

Stdlib-only; no third-party deps.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "skills" / "judge" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import score  # noqa: E402  -- must follow sys.path manipulation
import explain  # noqa: E402  -- must follow sys.path manipulation


_DEFAULT_CFG: Dict[str, Any] = {
    "enabled": True,
    "window": 10,
    "min_samples": 5,
    "top_threshold": 8.5,
    "top_bucket_fraction": 0.95,
    "max_std_dev": 0.3,
    "consistency_dock": 3,
}


def _hist(composites: List[float]) -> List[Dict[str, Any]]:
    """Build a synthetic history of scorecards with the given composites."""
    return [{"composite_score": c} for c in composites]


# ---------------------------------------------------------------------------
# Pure detector
# ---------------------------------------------------------------------------


class TestDetectorGuards(unittest.TestCase):
    def test_none_config_short_circuits(self) -> None:
        r = score._detect_verifier_collapse(_hist([9.5] * 10), None)
        self.assertFalse(r["flagged"])
        self.assertEqual(r["stats"], {})

    def test_disabled_config_short_circuits(self) -> None:
        cfg = {**_DEFAULT_CFG, "enabled": False}
        r = score._detect_verifier_collapse(_hist([9.5] * 10), cfg)
        self.assertFalse(r["flagged"])

    def test_empty_history_no_flag(self) -> None:
        r = score._detect_verifier_collapse([], _DEFAULT_CFG)
        self.assertFalse(r["flagged"])

    def test_below_min_samples_no_flag(self) -> None:
        r = score._detect_verifier_collapse(
            _hist([9.5, 9.5, 9.5]), _DEFAULT_CFG
        )
        self.assertFalse(r["flagged"])
        # Stats still reported so callers can see the window size.
        self.assertEqual(r["stats"]["window"], 3)
        self.assertEqual(r["stats"]["min_samples"], 5)


class TestDetectorPositive(unittest.TestCase):
    def test_flatlined_top_window_flags(self) -> None:
        r = score._detect_verifier_collapse(_hist([9.5] * 10), _DEFAULT_CFG)
        self.assertTrue(r["flagged"])
        self.assertIn("verifier collapse", r["reason"])
        self.assertGreaterEqual(r["stats"]["top_bucket_fraction"], 0.95)
        self.assertLess(r["stats"]["std_dev"], 0.3)

    def test_uses_rolling_window_tail(self) -> None:
        # Old varied history followed by 10 collapsed cards: window=10
        # should look at the tail and flag.
        composites = [6.0, 7.0, 8.0, 5.5, 7.2] + [9.5] * 10
        r = score._detect_verifier_collapse(_hist(composites), _DEFAULT_CFG)
        self.assertTrue(r["flagged"])

    def test_custom_threshold_respected(self) -> None:
        cfg = {**_DEFAULT_CFG, "top_threshold": 9.8}
        # All 9.5 -- below the bumped top_threshold of 9.8.
        r = score._detect_verifier_collapse(_hist([9.5] * 10), cfg)
        self.assertFalse(r["flagged"])


class TestDetectorNegative(unittest.TestCase):
    def test_variance_hides_collapse(self) -> None:
        # Alternating 9.5 / 8.0 -- top fraction stays high but std_dev
        # exceeds 0.3.
        composites = [9.5 if i % 2 else 8.0 for i in range(10)]
        r = score._detect_verifier_collapse(_hist(composites), _DEFAULT_CFG)
        self.assertFalse(r["flagged"])
        self.assertGreater(r["stats"]["std_dev"], 0.3)

    def test_below_top_threshold_no_flag(self) -> None:
        # All composites are 8.0 -- below top_threshold of 8.5.
        r = score._detect_verifier_collapse(_hist([8.0] * 10), _DEFAULT_CFG)
        self.assertFalse(r["flagged"])

    def test_malformed_config_silently_skips(self) -> None:
        cfg = {"enabled": True, "window": "ten"}  # non-numeric
        r = score._detect_verifier_collapse(_hist([9.5] * 10), cfg)
        self.assertFalse(r["flagged"])

    def test_non_dict_history_entries_ignored(self) -> None:
        # Past _analyze_consistency calls survived corrupt entries; the
        # detector must too.
        history = [
            {"composite_score": 9.5},
            "garbage",
            None,
            {"composite_score": 9.5},
            {"composite_score": "not a number"},
        ]
        r = score._detect_verifier_collapse(history, _DEFAULT_CFG)
        # Only 2 valid samples -> below min_samples, not flagged.
        self.assertFalse(r["flagged"])


# ---------------------------------------------------------------------------
# Consistency analyzer composition
# ---------------------------------------------------------------------------


class TestConsistencyComposition(unittest.TestCase):
    def test_collapsed_history_docks_and_flags(self) -> None:
        # All 9.5s -- existing logic would award base 8 + 1 (low-std)
        # = 9. With dock 3 -> 6.
        r = score._analyze_consistency(_hist([9.5] * 10), _DEFAULT_CFG)
        self.assertTrue(r["verifier_collapse"])
        self.assertEqual(r["score"], 6)
        self.assertIn("verifier collapse", r["justification"])
        self.assertIn("verifier_collapse_reason", r)
        self.assertIn("verifier_collapse_stats", r)

    def test_varied_history_no_flag_no_dock(self) -> None:
        # Spread 6.0 - 8.5 -- std_dev ~ 0.8+. Not collapsed.
        composites = [6.0, 6.5, 7.0, 7.2, 7.5, 8.0, 8.3, 8.5]
        r = score._analyze_consistency(_hist(composites), _DEFAULT_CFG)
        self.assertFalse(r["verifier_collapse"])
        # Score should be reasonable (not docked by collapse).
        self.assertGreaterEqual(r["score"], 6)

    def test_no_history_neutral_no_flag(self) -> None:
        r = score._analyze_consistency([], _DEFAULT_CFG)
        self.assertEqual(r["score"], 5)
        self.assertFalse(r["verifier_collapse"])

    def test_disabled_config_acts_like_pre_v204(self) -> None:
        # All 9.5s with detector disabled -> existing low-std bonus
        # kicks in, score lands at 9, and the verifier_collapse key
        # is OMITTED entirely (so CI can tell "did not run" from
        # "ran and saw nothing").
        cfg = {**_DEFAULT_CFG, "enabled": False}
        r = score._analyze_consistency(_hist([9.5] * 10), cfg)
        self.assertNotIn("verifier_collapse", r)
        self.assertEqual(r["score"], 9)

    def test_custom_dock_respected(self) -> None:
        cfg = {**_DEFAULT_CFG, "consistency_dock": 5}
        r = score._analyze_consistency(_hist([9.5] * 10), cfg)
        # base 8 + 1 (low-std) - 5 (dock) = 4
        self.assertEqual(r["score"], 4)
        self.assertTrue(r["verifier_collapse"])


# ---------------------------------------------------------------------------
# build_scorecard end-to-end
# ---------------------------------------------------------------------------


class TestScorecardTopLevelMirror(unittest.TestCase):
    """Drive build_scorecard against a pre-populated scores dir."""

    def _make_history(self, scores_dir: Path, skill: str) -> None:
        """Write 10 high-composite scorecards for *skill* into *scores_dir*."""
        scores_dir.mkdir(parents=True, exist_ok=True)
        for i in range(10):
            ts = f"2026-05-2{i % 9}T0{i}-00-00Z"
            (scores_dir / f"{skill}_{ts}.json").write_text(
                json.dumps(
                    {
                        "skill": skill,
                        "timestamp": ts,
                        "composite_score": 9.5,
                        "grade": "A",
                        "dimensions": {},
                    }
                )
            )

    def _make_transcript(self, path: Path) -> None:
        path.write_text(
            '{"role":"user","content":"hi"}\n'
            '{"role":"assistant","content":"hello"}\n'
        )

    def _make_config(self, path: Path, enabled: bool) -> None:
        path.write_text(
            json.dumps(
                {
                    "auto_judge": {"enabled": True, "always": [], "never": []},
                    "scoring": {
                        "dimensions": {
                            "correctness": 0.25,
                            "completeness": 0.20,
                            "adherence": 0.15,
                            "actionability": 0.15,
                            "efficiency": 0.10,
                            "safety": 0.10,
                            "consistency": 0.05,
                        }
                    },
                    "verifier_collapse": {**_DEFAULT_CFG, "enabled": enabled},
                }
            )
        )

    def test_flag_mirrored_to_top_level_when_collapsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scores_dir = tmp_path / "scores"
            self._make_history(scores_dir, "code-review")
            transcript = tmp_path / "t.jsonl"
            self._make_transcript(transcript)
            cfg = tmp_path / "judge-config.json"
            self._make_config(cfg, enabled=True)

            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(scores_dir),
                config_path=str(cfg),
            )
            self.assertTrue(card.get("verifier_collapse"))
            consistency = card["dimensions"]["consistency"]
            self.assertTrue(consistency["verifier_collapse"])
            self.assertIn("verifier_collapse_reason", consistency)
            self.assertIn("verifier_collapse_stats", consistency)

    def test_flag_false_when_detector_runs_but_no_collapse(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scores_dir = tmp_path / "scores"
            scores_dir.mkdir(parents=True, exist_ok=True)
            # Varied history -> detector runs but does not flag.
            for i, composite in enumerate([5.0, 6.5, 7.0, 8.0, 6.5, 7.5, 8.0, 7.0]):
                ts = f"2026-05-2{i % 9}T0{i}-00-00Z"
                (scores_dir / f"code-review_{ts}.json").write_text(
                    json.dumps(
                        {
                            "skill": "code-review",
                            "timestamp": ts,
                            "composite_score": composite,
                            "grade": "B",
                            "dimensions": {},
                        }
                    )
                )
            transcript = tmp_path / "t.jsonl"
            self._make_transcript(transcript)
            cfg = tmp_path / "judge-config.json"
            self._make_config(cfg, enabled=True)

            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(scores_dir),
                config_path=str(cfg),
            )
            self.assertFalse(card.get("verifier_collapse", True))
            self.assertFalse(
                card["dimensions"]["consistency"]["verifier_collapse"]
            )

    def test_no_field_when_detector_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            scores_dir = tmp_path / "scores"
            self._make_history(scores_dir, "code-review")
            transcript = tmp_path / "t.jsonl"
            self._make_transcript(transcript)
            cfg = tmp_path / "judge-config.json"
            self._make_config(cfg, enabled=False)

            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(transcript),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(scores_dir),
                config_path=str(cfg),
            )
            # Detector disabled => the field is omitted entirely at
            # both top level and the consistency dim, so CI consumers
            # can tell "did not run" apart from "ran and saw nothing".
            self.assertNotIn("verifier_collapse", card)
            consistency = card["dimensions"]["consistency"]
            self.assertNotIn("verifier_collapse", consistency)


# ---------------------------------------------------------------------------
# explain.v1
# ---------------------------------------------------------------------------


def _synthetic_collapsed_card() -> Dict[str, Any]:
    return {
        "skill": "code-review",
        "composite_score": 8.7,
        "grade": "A-",
        "grade_label": "Very Good",
        "rubric_used": "code-review",
        "model": "claude-opus-4-7",
        "timestamp": "2026-05-29T12:00:00Z",
        "summary": "OK.",
        "one_liner": "Solid execution.",
        "verifier_collapse": True,
        "dimensions": {
            "correctness": {
                "score": 9,
                "weight": 0.25,
                "weighted": 2.25,
                "justification": "clean",
            },
            "consistency": {
                "score": 6,
                "weight": 0.05,
                "weighted": 0.3,
                "justification": "collapsed",
                "verifier_collapse": True,
                "verifier_collapse_reason": "verifier collapse: 10/10 of recent composites >= 8.5 (fraction 1.00 >= 0.95) and std_dev 0.10 < 0.30",
                "verifier_collapse_stats": {
                    "window": 10,
                    "top_bucket_fraction": 1.0,
                    "std_dev": 0.10,
                    "max_std_dev": 0.3,
                    "top_threshold": 8.5,
                },
            },
        },
        "red_flags": [],
        "bonuses": [],
        "critical_issues": [],
        "recommendations": [],
        "adjustments": {"deduction": 0.0, "bonus": 0.0},
        "transcript_lines": 100,
    }


class TestExplainJsonV1(unittest.TestCase):
    def test_top_level_verifier_collapse_emitted(self) -> None:
        card = _synthetic_collapsed_card()
        payload = json.loads(explain.render_json(card))
        self.assertTrue(payload.get("verifier_collapse"))

    def test_per_dim_reason_and_stats_surfaced(self) -> None:
        card = _synthetic_collapsed_card()
        payload = json.loads(explain.render_json(card))
        consistency = next(
            d for d in payload["dimensions"] if d["name"] == "consistency"
        )
        self.assertTrue(consistency["verifier_collapse"])
        self.assertIn("verifier_collapse_reason", consistency)
        self.assertIn("verifier_collapse_stats", consistency)

    def test_field_omitted_when_no_collapse(self) -> None:
        card = _synthetic_collapsed_card()
        del card["verifier_collapse"]
        card["dimensions"]["consistency"]["verifier_collapse"] = False
        del card["dimensions"]["consistency"]["verifier_collapse_reason"]
        del card["dimensions"]["consistency"]["verifier_collapse_stats"]
        payload = json.loads(explain.render_json(card))
        self.assertNotIn("verifier_collapse", payload)

    def test_format_version_unchanged(self) -> None:
        card = _synthetic_collapsed_card()
        payload = json.loads(explain.render_json(card))
        self.assertEqual(payload["format_version"], "explain.v1")


class TestExplainMarkdown(unittest.TestCase):
    def test_callout_emitted_when_flagged(self) -> None:
        md = explain.render_markdown(_synthetic_collapsed_card())
        self.assertIn("⚠️ Verifier collapse detected", md)
        self.assertIn("Soft-SVeRL", md)
        self.assertIn("window n=10", md)

    def test_no_callout_when_not_flagged(self) -> None:
        card = _synthetic_collapsed_card()
        del card["verifier_collapse"]
        card["dimensions"]["consistency"]["verifier_collapse"] = False
        md = explain.render_markdown(card)
        self.assertNotIn("Verifier collapse detected", md)

    def test_no_sibling_benchmark_named(self) -> None:
        """G13 anti-cross-pollination: no SWE-bench, MMLU, GSM8K, etc."""
        md = explain.render_markdown(_synthetic_collapsed_card())
        forbidden = ("SWE-bench", "MMLU", "GSM8K", "BIG-bench", "HumanEval")
        for token in forbidden:
            self.assertNotIn(token, md, f"forbidden sibling-bench '{token}' leaked into Markdown")


# ---------------------------------------------------------------------------
# Hook ship-gate
# ---------------------------------------------------------------------------


class TestHookGateMode(unittest.TestCase):
    """End-to-end test of judge-on-stop.sh gate_mode behaviour.

    We stage a temp PLUGIN_ROOT mirroring the real layout, then drive
    the hook from a pre-populated scores dir so the actual score.py
    invocation produces a verifier_collapse=true scorecard. This
    exercises both the hook plumbing and the verifier_collapse plumbing
    in one shot.
    """

    @classmethod
    def setUpClass(cls) -> None:
        if not shutil.which("jq") or not shutil.which("bc"):
            raise unittest.SkipTest("jq + bc required for hook tests")

    def _stage(self, tmp: Path, gate_mode: str) -> Tuple[Path, Path]:
        """Build a temp PLUGIN_ROOT; return (plugin_root, transcript_path)."""
        plugin = tmp / "plugin"
        (plugin / "hooks").mkdir(parents=True)
        (plugin / "skills" / "judge" / "scripts").mkdir(parents=True)
        (plugin / "skills" / "judge" / "rubrics").mkdir(parents=True)
        (plugin / "skills" / "judge" / "scores").mkdir(parents=True)

        # Copy the real hook + common + score machinery.
        shutil.copy(
            PROJECT_ROOT / "hooks" / "common.sh",
            plugin / "hooks" / "common.sh",
        )
        shutil.copy(
            PROJECT_ROOT / "hooks" / "judge-on-stop.sh",
            plugin / "hooks" / "judge-on-stop.sh",
        )
        (plugin / "hooks" / "judge-on-stop.sh").chmod(0o755)
        # The scoring engine and rubric set must be the actual ones --
        # symlink to avoid copying ~1.5 MB of rubrics.
        (plugin / "skills" / "judge" / "scripts").rmdir()
        (plugin / "skills" / "judge" / "scripts").symlink_to(
            PROJECT_ROOT / "skills" / "judge" / "scripts"
        )
        # ditto rubrics + analyzers + adapters (the scripts need them
        # via sys.path at runtime).
        (plugin / "skills" / "judge" / "rubrics").rmdir()
        (plugin / "skills" / "judge" / "rubrics").symlink_to(
            PROJECT_ROOT / "skills" / "judge" / "rubrics"
        )
        (plugin / "skills" / "judge" / "analyzers").symlink_to(
            PROJECT_ROOT / "skills" / "judge" / "analyzers"
        )
        (plugin / "skills" / "judge" / "adapters").symlink_to(
            PROJECT_ROOT / "skills" / "judge" / "adapters"
        )

        # Pre-populate scores/ with 10 high-composite cards so the
        # detector flags collapse.
        scores = plugin / "skills" / "judge" / "scores"
        for i in range(10):
            ts = f"2026-05-2{i % 9}T0{i}-00-00Z"
            (scores / f"code-review_{ts}.json").write_text(
                json.dumps(
                    {
                        "skill": "code-review",
                        "timestamp": ts,
                        "composite_score": 9.5,
                        "grade": "A",
                        "dimensions": {},
                    }
                )
            )

        # auto_judge.always includes code-review so should_auto_judge
        # returns true; threshold is low enough that we do not trip
        # the existing exit-2 gate (we want the collapse gate to fire,
        # not the threshold gate).
        (plugin / "judge-config.json").write_text(
            json.dumps(
                {
                    "auto_judge": {
                        "enabled": True,
                        "always": ["code-review"],
                        "never": [],
                        "threshold": 0.0,
                    },
                    "scoring": {
                        "dimensions": {
                            "correctness": 0.25,
                            "completeness": 0.20,
                            "adherence": 0.15,
                            "actionability": 0.15,
                            "efficiency": 0.10,
                            "safety": 0.10,
                            "consistency": 0.05,
                        }
                    },
                    "verifier_collapse": {**_DEFAULT_CFG, "gate_mode": gate_mode},
                }
            )
        )

        # Transcript with a skill marker the hook's detect_skill
        # patterns will pick up. The "skill" JSON field is the most
        # robust pattern (works for stdin-style hook payloads).
        transcript = tmp / "transcript.jsonl"
        transcript.write_text(
            '{"role":"user","content":"reviewing","skill":"code-review"}\n'
            '{"role":"assistant","content":"ok"}\n'
        )
        return plugin, transcript

    def _run_hook(self, plugin: Path, transcript: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(plugin / "hooks" / "judge-on-stop.sh")],
            input=json.dumps({"transcript_path": str(transcript)}),
            capture_output=True,
            text=True,
        )

    def test_gate_mode_warn_exits_0_with_stderr_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin, transcript = self._stage(Path(tmp), gate_mode="warn")
            result = self._run_hook(plugin, transcript)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Proofloop WARNING: verifier collapse", result.stderr)

    def test_gate_mode_fail_exits_2_with_stderr_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin, transcript = self._stage(Path(tmp), gate_mode="fail")
            result = self._run_hook(plugin, transcript)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertIn("Proofloop BLOCKED: verifier collapse", result.stderr)

    def test_gate_mode_off_silent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plugin, transcript = self._stage(Path(tmp), gate_mode="off")
            result = self._run_hook(plugin, transcript)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("verifier collapse", result.stderr)


if __name__ == "__main__":
    unittest.main()
