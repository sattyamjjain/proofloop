#!/usr/bin/env python3
"""Tests for the score-based adapter dispatcher (O1 fix).

After Y6 added OpenTelemetry GenAI semconv attrs to ``mlflow_trace``,
both ``inspect_ai_log`` and ``mlflow_trace`` could fingerprint a trace
carrying ``gen_ai.*`` keys plus Inspect-style ``samples[]`` arrays.
The first-match-wins ordering was undefined cross-platform.

This test file pins the new contract: each adapter exposes a
``detection_score(path) -> float`` in ``[0.0, 1.0]``, and
``adapters.detect_adapter`` picks the highest-scoring name.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
import adapters  # noqa: E402
from adapters import (  # noqa: E402
    inspect_ai_log,
    mlflow_trace,
    terminal_bench,
    gemini_deep_research,
)


def _write(content: str, suffix: str = ".json") -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    os.write(fd, content.encode("utf-8"))
    os.close(fd)
    return path


class TestEachAdapterExposesScore(unittest.TestCase):
    """Every collision-prone adapter has a detection_score()."""

    def test_inspect_ai_has_score(self) -> None:
        self.assertTrue(callable(getattr(inspect_ai_log, "detection_score")))

    def test_mlflow_trace_has_score(self) -> None:
        self.assertTrue(callable(getattr(mlflow_trace, "detection_score")))

    def test_terminal_bench_has_score(self) -> None:
        self.assertTrue(callable(getattr(terminal_bench, "detection_score")))

    def test_gemini_deep_research_has_score(self) -> None:
        self.assertTrue(callable(getattr(gemini_deep_research, "detection_score")))


class TestNoCollisions(unittest.TestCase):
    """Specific collision payloads must resolve deterministically."""

    def test_otel_enriched_mlflow_trace_with_inspect_samples(self) -> None:
        """The motivating O1 case: MLflow trace shape + Inspect samples."""
        payload = (
            '{"schema": "mlflow.entities.Trace",'
            '"info": {"request_id": "r1", "status": "OK"},'
            '"data": {"spans": [{"attributes":'
            '{"gen_ai.request.model":"claude-opus-4-7"},'
            '"events":[]}]},'
            # Inspect-flavoured noise that would have collided pre-fix.
            '"samples": [{"id":"s1","messages":[]}]}'
        )
        path = _write(payload)
        try:
            self.assertEqual(adapters.detect_adapter(path), "mlflow-trace")
        finally:
            os.unlink(path)

    def test_inspect_ai_alone_resolves_to_inspect(self) -> None:
        payload = '{"eval": {"task":"x"}, "samples":[{"id":"s1"}]}'
        path = _write(payload)
        try:
            self.assertEqual(adapters.detect_adapter(path), "inspect-ai")
        finally:
            os.unlink(path)

    def test_mlflow_alone_resolves_to_mlflow(self) -> None:
        payload = (
            '{"schema":"mlflow.entities.Trace",'
            '"data":{"spans":[]}}'
        )
        path = _write(payload)
        try:
            self.assertEqual(adapters.detect_adapter(path), "mlflow-trace")
        finally:
            os.unlink(path)

    def test_terminal_bench_alone_resolves(self) -> None:
        payload = '{"steps":[{"command":"ls","exit_code":0}]}'
        path = _write(payload)
        try:
            self.assertEqual(adapters.detect_adapter(path), "terminal-bench")
        finally:
            os.unlink(path)

    def test_gemini_deep_research_wins_over_unrelated(self) -> None:
        payload = (
            '{"deep_research_mode": true,"research_plan":[],'
            '"verifier_notes":[],"assistant_synthesis":""}'
        )
        path = _write(payload)
        try:
            self.assertEqual(adapters.detect_adapter(path), "gemini-deep-research")
        finally:
            os.unlink(path)

    def test_falls_back_to_claude_code_when_all_zero(self) -> None:
        payload = '{"role":"user","content":"hello"}'
        path = _write(payload, suffix=".jsonl")
        try:
            self.assertEqual(adapters.detect_adapter(path), "claude-code")
        finally:
            os.unlink(path)

    def test_missing_file_falls_back(self) -> None:
        self.assertEqual(
            adapters.detect_adapter("/tmp/verdict-no-such-file"),
            "claude-code",
        )


class TestScoreRanges(unittest.TestCase):
    """detection_score must return values in [0.0, 1.0]."""

    def _check_range(self, fn, payload: str) -> None:
        path = _write(payload)
        try:
            score = fn(path)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
        finally:
            os.unlink(path)

    def test_all_adapters_in_range_for_negative_payload(self) -> None:
        for fn in (
            inspect_ai_log.detection_score,
            mlflow_trace.detection_score,
            terminal_bench.detection_score,
            gemini_deep_research.detection_score,
        ):
            self._check_range(fn, '{"unrelated":true}')

    def test_all_adapters_in_range_for_positive_payload(self) -> None:
        positives = {
            inspect_ai_log.detection_score: '{"inspect_ai": true,"samples":[]}',
            mlflow_trace.detection_score: '{"schema":"mlflow.entities.Trace","data":{}}',
            terminal_bench.detection_score: '{"terminal_bench":true,"steps":[]}',
            gemini_deep_research.detection_score: '{"deep_research_mode":true}',
        }
        for fn, payload in positives.items():
            self._check_range(fn, payload)

    def test_scorer_swallows_exceptions(self) -> None:
        """An exception inside any scorer must not crash dispatch."""
        # detect_adapter wraps each call in try/except; a malformed
        # path produces score 0.0 not a raised exception.
        result = adapters.detect_adapter("/tmp/this/path/cannot/exist")
        self.assertEqual(result, "claude-code")


class TestExistingFixturesStillResolve(unittest.TestCase):
    """Regression: every shipped fixture must keep its existing adapter."""

    def test_inspect_ai_fixture(self) -> None:
        self.assertEqual(
            adapters.detect_adapter(str(FIXTURES_DIR / "inspect-ai-log.json")),
            "inspect-ai",
        )

    def test_terminal_bench_fixture(self) -> None:
        self.assertEqual(
            adapters.detect_adapter(
                str(FIXTURES_DIR / "terminal-bench-trajectory.json")
            ),
            "terminal-bench",
        )

    def test_gemini_deep_research_fixture(self) -> None:
        self.assertEqual(
            adapters.detect_adapter(
                str(FIXTURES_DIR / "gemini-deep-research.json")
            ),
            "gemini-deep-research",
        )


if __name__ == "__main__":
    unittest.main()
