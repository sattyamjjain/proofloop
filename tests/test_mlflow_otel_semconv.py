#!/usr/bin/env python3
"""Tests for OpenTelemetry GenAI semconv enrichment in the MLflow adapter.

Covers:
- ``_extract_otel_genai_attrs`` shape and field extraction
- pseudo-turn emission (``[model]``, ``[usage]``, ``[finish_reason]``)
- compatibility with ``score.detect_model_from_transcript`` so the
  v1.1.0 model-aware efficiency thresholds apply to MLflow traces
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

from adapters import mlflow_trace  # noqa: E402
import score  # noqa: E402


def _write_trace(payload: dict) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    os.write(fd, json.dumps(payload).encode("utf-8"))
    os.close(fd)
    return path


def _span_with_otel(model: str = "claude-opus-4-7") -> dict:
    return {
        "name": "run",
        "attributes": {
            "gen_ai.request.model": model,
            "gen_ai.usage.input_tokens": 120,
            "gen_ai.usage.output_tokens": 60,
            "gen_ai.response.finish_reasons": ["stop"],
        },
        "events": [
            {"name": "assistant", "attributes": {"content": "hi"}},
        ],
    }


def _trace_envelope(spans: list) -> dict:
    return {
        "schema": "mlflow.entities.Trace",
        "info": {"request_id": "req-1", "status": "OK"},
        "data": {"spans": spans},
    }


class TestExtractOtelGenAiAttrs(unittest.TestCase):
    def test_empty_for_non_dict(self) -> None:
        self.assertEqual(mlflow_trace._extract_otel_genai_attrs("not-a-dict"), {})
        self.assertEqual(mlflow_trace._extract_otel_genai_attrs(None), {})

    def test_empty_when_no_attributes(self) -> None:
        self.assertEqual(mlflow_trace._extract_otel_genai_attrs({}), {})

    def test_extracts_all_four_fields(self) -> None:
        attrs = mlflow_trace._extract_otel_genai_attrs(_span_with_otel())
        self.assertEqual(attrs["model"], "claude-opus-4-7")
        self.assertEqual(attrs["input_tokens"], 120)
        self.assertEqual(attrs["output_tokens"], 60)
        self.assertEqual(attrs["finish_reasons"], ["stop"])

    def test_response_model_fallback(self) -> None:
        span = {"attributes": {"gen_ai.response.model": "claude-haiku-4-5"}}
        attrs = mlflow_trace._extract_otel_genai_attrs(span)
        self.assertEqual(attrs["model"], "claude-haiku-4-5")

    def test_finish_reason_string_promoted_to_list(self) -> None:
        span = {"attributes": {
            "gen_ai.response.finish_reasons": "length",
        }}
        attrs = mlflow_trace._extract_otel_genai_attrs(span)
        self.assertEqual(attrs["finish_reasons"], ["length"])

    def test_float_token_count_coerced(self) -> None:
        span = {"attributes": {
            "gen_ai.usage.input_tokens": 99.0,
            "gen_ai.usage.output_tokens": 42.0,
        }}
        attrs = mlflow_trace._extract_otel_genai_attrs(span)
        self.assertEqual(attrs["input_tokens"], 99)
        self.assertEqual(attrs["output_tokens"], 42)

    def test_malformed_fields_silently_dropped(self) -> None:
        span = {"attributes": {
            "gen_ai.request.model": 42,        # wrong type
            "gen_ai.usage.input_tokens": True,  # bool is not int
            "gen_ai.response.finish_reasons": [None, 1, "stop"],
        }}
        attrs = mlflow_trace._extract_otel_genai_attrs(span)
        self.assertNotIn("model", attrs)
        self.assertNotIn("input_tokens", attrs)
        self.assertEqual(attrs["finish_reasons"], ["stop"])


class TestOtelPseudoTurnsInExtractLines(unittest.TestCase):
    def test_emits_model_and_usage_and_finish(self) -> None:
        path = _write_trace(_trace_envelope([_span_with_otel()]))
        try:
            lines = mlflow_trace.extract_lines(path)
        finally:
            os.unlink(path)
        joined = "\n".join(lines)
        self.assertIn('[model] "model":"claude-opus-4-7"', lines)
        self.assertTrue(any(l.startswith("[usage] input_tokens=120") for l in lines))
        self.assertIn("[finish_reason] stop", lines)
        # Existing assistant event still flows through.
        self.assertIn("[assistant] hi", joined)

    def test_no_otel_span_still_flows_through(self) -> None:
        bare_span = {
            "name": "run",
            "events": [{"name": "user", "attributes": {"content": "q"}}],
        }
        path = _write_trace(_trace_envelope([bare_span]))
        try:
            lines = mlflow_trace.extract_lines(path)
        finally:
            os.unlink(path)
        self.assertNotIn('[model] "model":"', "\n".join(lines))
        self.assertIn("[user] q", lines)

    def test_per_span_enrichment_precedes_events(self) -> None:
        path = _write_trace(_trace_envelope([_span_with_otel()]))
        try:
            lines = mlflow_trace.extract_lines(path)
        finally:
            os.unlink(path)
        model_idx = next(i for i, l in enumerate(lines) if l.startswith("[model]"))
        assistant_idx = next(
            i for i, l in enumerate(lines) if l.startswith("[assistant]")
        )
        self.assertLess(model_idx, assistant_idx)


class TestModelDetectionCompatibility(unittest.TestCase):
    """Regex in score.py must pick up OTel model keys in the raw file."""

    def test_gen_ai_request_model_matches(self) -> None:
        path = _write_trace({
            "schema": "mlflow.entities.Trace",
            "data": {"spans": [_span_with_otel("claude-sonnet-4-6")]},
        })
        try:
            detected = score.detect_model_from_transcript(path)
        finally:
            os.unlink(path)
        self.assertEqual(detected, "claude-sonnet-4-6")

    def test_plain_model_key_still_matches(self) -> None:
        # Back-compat: the pre-OTel ``"model":"..."`` form must still
        # resolve; the regex widening must not regress on Claude Code.
        fd, path = tempfile.mkstemp(suffix=".jsonl")
        try:
            os.write(fd, b'{"model":"claude-opus-4-7","role":"assistant"}\n')
            os.close(fd)
            detected = score.detect_model_from_transcript(path)
        finally:
            os.unlink(path)
        self.assertEqual(detected, "claude-opus-4-7")

    def test_mlflow_trace_tokenizer_baseline_applied(self) -> None:
        path = _write_trace({
            "schema": "mlflow.entities.Trace",
            "info": {"request_id": "r", "status": "OK"},
            "data": {"spans": [_span_with_otel("claude-opus-4-7")]},
        })
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            try:
                card = score.build_scorecard(
                    skill_name="default",
                    transcript_path=path,
                    rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                    scores_dir=str(tmp),
                    adapter="mlflow-trace",
                )
            finally:
                os.unlink(path)
        # The Opus 4.7 tokenizer baseline (1.35x) must be applied when
        # the model is detected from the OTel attrs. Default baseline
        # is 1.0, so a non-1.0 value proves detection reached the
        # efficiency analyzer.
        self.assertEqual(card["model"], "claude-opus-4-7")
        self.assertAlmostEqual(card["tokenizer_baseline"], 1.35)


if __name__ == "__main__":
    unittest.main()
