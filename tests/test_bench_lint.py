#!/usr/bin/env python3
"""Tests for scripts/bench_lint.py and the --lint wire into benchmark_pack.

The lint adapts the Auto Benchmark Audit framework (Wang et al. 2026,
arXiv:2605.26079) to Verdict's transcript-regression manifest. These
tests verify that:

1. The shipped benchmarks/manifest.json passes hygiene cleanly
   (bench_hygiene_score == 1.0, exit 0).
2. Each of the four hygiene rule classes (VBL001-004) fires on an
   injected bad case.
3. SARIF output is valid v2.1.0 shape with one result per finding.
4. Exit codes follow the contract: 0 above threshold, 1 below, 2 on
   IO/arg failure.
5. The benchmark_pack --lint pre-flight gate aborts before the
   regression suite runs when the corpus is below threshold.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import bench_lint as bl  # noqa: E402  -- must follow sys.path manipulation


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_manifest(tmp: Path, cases: List[Dict[str, Any]]) -> Path:
    """Write a tiny manifest + populate transcript files referenced by cases.

    Any case carrying ``_make_transcript`` is materialised on disk with
    that content (and the helper key stripped before write).
    """
    cleaned: List[Dict[str, Any]] = []
    for case in cases:
        case = dict(case)
        body = case.pop("_make_transcript", None)
        if body is not None and case.get("transcript"):
            (tmp / case["transcript"]).parent.mkdir(parents=True, exist_ok=True)
            (tmp / case["transcript"]).write_text(body, encoding="utf-8")
        cleaned.append(case)
    manifest = {"description": "test fixture", "cases": cleaned}
    path = tmp / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path


_GOOD_TRANSCRIPT = (
    '{"role":"user","content":"hi"}\n'
    '{"role":"assistant","content":"hello"}\n'
)


# ---------------------------------------------------------------------------
# Unit tests for individual rules
# ---------------------------------------------------------------------------


class TestSpecGap(unittest.TestCase):
    def test_missing_name_flags_VBL001(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "",
                        "skill": "code-review",
                        "transcript": "t.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": _GOOD_TRANSCRIPT,
                    }
                ],
            )
            report = bl.lint_manifest(mp)
            rule_ids = {f["rule_id"] for f in report["findings"]}
            self.assertIn("VBL001", rule_ids)

    def test_missing_skill_flags_VBL001(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "no-skill",
                        "transcript": "t.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": _GOOD_TRANSCRIPT,
                    }
                ],
            )
            self.assertIn(
                "VBL001",
                {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]},
            )

    def test_no_expected_assertion_flags_VBL001(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "nothing-asserted",
                        "skill": "code-review",
                        "transcript": "t.jsonl",
                        "_make_transcript": _GOOD_TRANSCRIPT,
                    }
                ],
            )
            report = bl.lint_manifest(mp)
            self.assertIn(
                "VBL001",
                {f["rule_id"] for f in report["findings"]},
            )


class TestEnvCoupling(unittest.TestCase):
    def test_absolute_transcript_path_flags_VBL002(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            absolute = tmp_path / "abs.jsonl"
            absolute.write_text(_GOOD_TRANSCRIPT, encoding="utf-8")
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "absolute-leak",
                        "skill": "code-review",
                        "transcript": str(absolute),
                        "expected_composite_min": 7.0,
                    }
                ],
            )
            self.assertIn(
                "VBL002",
                {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]},
            )

    def test_missing_transcript_flags_VBL002(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "ghost",
                        "skill": "code-review",
                        "transcript": "does-not-exist.jsonl",
                        "expected_composite_min": 7.0,
                    }
                ],
            )
            self.assertIn(
                "VBL002",
                {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]},
            )

    def test_adapter_extension_mismatch_flags_VBL002(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "openai-but-jsonl",
                        "skill": "code-review",
                        "transcript": "wrong.jsonl",
                        "adapter": "openai-compatible",
                        "expected_composite_min": 7.0,
                        "_make_transcript": _GOOD_TRANSCRIPT,
                    }
                ],
            )
            self.assertIn(
                "VBL002",
                {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]},
            )


class TestBrittleGrading(unittest.TestCase):
    def test_single_point_composite_flags_VBL003(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "pin-composite",
                        "skill": "code-review",
                        "transcript": "t.jsonl",
                        "expected_composite_min": 8.0,
                        "expected_composite_max": 8.0,
                        "_make_transcript": _GOOD_TRANSCRIPT,
                    }
                ],
            )
            self.assertIn(
                "VBL003",
                {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]},
            )

    def test_narrow_composite_range_flags_VBL003(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "narrow",
                        "skill": "code-review",
                        "transcript": "t.jsonl",
                        "expected_composite_min": 8.0,
                        "expected_composite_max": 8.2,
                        "_make_transcript": _GOOD_TRANSCRIPT,
                    }
                ],
            )
            self.assertIn(
                "VBL003",
                {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]},
            )

    def test_pinned_dimension_flags_VBL003(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "pin-dim",
                        "skill": "code-review",
                        "transcript": "t.jsonl",
                        "expected_dimension_min": {"safety": 9},
                        "expected_dimension_max": {"safety": 9},
                        "_make_transcript": _GOOD_TRANSCRIPT,
                    }
                ],
            )
            self.assertIn(
                "VBL003",
                {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]},
            )


class TestMissingGroundTruth(unittest.TestCase):
    def test_empty_file_flags_VBL004(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "empty-transcript",
                        "skill": "code-review",
                        "transcript": "empty.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": "",
                    }
                ],
            )
            rule_ids = {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]}
            self.assertIn("VBL004", rule_ids)

    def test_blank_only_file_flags_VBL004(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "blank-lines-only",
                        "skill": "code-review",
                        "transcript": "blank.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": "\n\n   \n\t\n",
                    }
                ],
            )
            self.assertIn(
                "VBL004",
                {f["rule_id"] for f in bl.lint_manifest(mp)["findings"]},
            )


# ---------------------------------------------------------------------------
# End-to-end behaviour
# ---------------------------------------------------------------------------


class TestShippedManifestIsClean(unittest.TestCase):
    """The repo's own benchmarks/manifest.json must pass the lint."""

    def test_shipped_manifest_scores_1_0(self) -> None:
        report = bl.lint_manifest(PROJECT_ROOT / "benchmarks" / "manifest.json")
        self.assertEqual(report["flagged_cases"], 0, report["findings"])
        self.assertEqual(report["bench_hygiene_score"], 1.0)

    def test_shipped_manifest_exit_0(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bench_lint.py"), "--quiet"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


class TestHygieneScoreAggregate(unittest.TestCase):
    def test_one_bad_out_of_two_scores_0_5(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "clean",
                        "skill": "code-review",
                        "transcript": "good.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": _GOOD_TRANSCRIPT,
                    },
                    {
                        "name": "bad",
                        "skill": "code-review",
                        "transcript": "empty.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": "",
                    },
                ],
            )
            report = bl.lint_manifest(mp)
            self.assertEqual(report["total_cases"], 2)
            self.assertEqual(report["flagged_cases"], 1)
            self.assertEqual(report["bench_hygiene_score"], 0.5)


class TestSarifShape(unittest.TestCase):
    def test_sarif_has_v2_1_0_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "bad",
                        "skill": "code-review",
                        "transcript": "empty.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": "",
                    }
                ],
            )
            report = bl.lint_manifest(mp)
            sarif = bl.to_sarif(report)
            self.assertEqual(sarif["version"], "2.1.0")
            self.assertEqual(len(sarif["runs"]), 1)
            run = sarif["runs"][0]
            self.assertEqual(
                run["tool"]["driver"]["name"], "verdict-bench-lint"
            )
            rule_ids = [r["id"] for r in run["tool"]["driver"]["rules"]]
            self.assertEqual(
                sorted(rule_ids), ["VBL001", "VBL002", "VBL003", "VBL004"]
            )
            # Exactly one result per finding (the empty file fires VBL004).
            self.assertEqual(len(run["results"]), len(report["findings"]))
            self.assertGreaterEqual(len(run["results"]), 1)
            self.assertEqual(run["results"][0]["ruleId"], "VBL004")


class TestCLIExitCodes(unittest.TestCase):
    def _run(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "bench_lint.py"), *args],
            capture_output=True,
            text=True,
            cwd=str(cwd) if cwd else None,
        )

    def test_exit_2_when_manifest_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self._run(str(Path(tmp) / "nope.json"))
            self.assertEqual(result.returncode, 2)
            self.assertIn("not found", result.stderr)

    def test_exit_2_when_manifest_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.json"
            bad.write_text("{not json", encoding="utf-8")
            result = self._run(str(bad))
            self.assertEqual(result.returncode, 2)

    def test_exit_1_when_below_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "bad",
                        "skill": "code-review",
                        "transcript": "empty.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": "",
                    }
                ],
            )
            result = self._run(str(mp), "--quiet")
            self.assertEqual(result.returncode, 1, result.stderr)

    def test_exit_0_when_above_threshold(self) -> None:
        result = self._run(
            str(PROJECT_ROOT / "benchmarks" / "manifest.json"), "--quiet"
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_sarif_file_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "bad",
                        "skill": "code-review",
                        "transcript": "empty.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": "",
                    }
                ],
            )
            sarif_path = tmp_path / "out.sarif"
            result = self._run(str(mp), "--sarif", str(sarif_path), "--quiet")
            self.assertEqual(result.returncode, 1)
            self.assertTrue(sarif_path.is_file())
            doc = json.loads(sarif_path.read_text(encoding="utf-8"))
            self.assertEqual(doc["version"], "2.1.0")


class TestBenchmarkPackLintGate(unittest.TestCase):
    """The ship-gate: benchmark_pack --lint aborts when corpus is suspect."""

    def test_lint_gate_aborts_on_dirty_corpus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            mp = _write_manifest(
                tmp_path,
                [
                    {
                        "name": "bad",
                        "skill": "code-review",
                        "transcript": "empty.jsonl",
                        "expected_composite_min": 7.0,
                        "_make_transcript": "",
                    }
                ],
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS_DIR / "benchmark_pack.py"),
                    str(mp),
                    "--lint",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            # Pre-flight must abort BEFORE the regression suite starts.
            self.assertIn("Pre-flight", result.stdout)
            self.assertNotIn("Running 1 benchmark case", result.stdout)
            self.assertIn("VBL004", result.stderr)


if __name__ == "__main__":
    unittest.main()
