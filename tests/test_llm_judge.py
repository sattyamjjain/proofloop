#!/usr/bin/env python3
"""Tests for the opt-in LLM second-opinion analyzer.

Uses a mock client so no network calls happen. Exercises:
  - transcript truncation math
  - prompt composition (dimension list + rubric criteria inclusion)
  - response parsing (clean JSON, fenced JSON, trailing commas, prose
    wrapper)
  - score clamping (<1 → 1, >10 → 10)
  - integration through ``score.build_scorecard`` when the config
    toggle is on, with the client injected
  - graceful degradation when the LLM call fails
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

from analyzers import llm_judge as lj  # noqa: E402
import score  # noqa: E402


class FakeClient:
    """In-memory LLMClient used by tests. Captures last call for assertions."""

    def __init__(self, response_text: str = "", raises: Optional[Exception] = None):
        self.response_text = response_text
        self.raises = raises
        self.calls: List[Dict[str, Any]] = []

    def messages_create(self, model: str, system: str, prompt: str, max_tokens: int) -> str:
        self.calls.append({
            "model": model, "system": system, "prompt": prompt, "max_tokens": max_tokens,
        })
        if self.raises:
            raise self.raises
        return self.response_text


def _canonical_response(score_per_dim: int = 8) -> str:
    return json.dumps({
        dim: {"score": score_per_dim, "justification": f"llm view of {dim}"}
        for dim in lj.DIMENSIONS
    })


class TestTruncateTranscript(unittest.TestCase):
    def test_under_budget_returns_joined(self) -> None:
        lines = ["a" * 100, "b" * 100]
        out = lj.truncate_transcript(lines, max_chars=1000)
        self.assertEqual(out, "\n".join(lines))

    def test_over_budget_preserves_head_and_tail(self) -> None:
        lines = ["x" * 10_000] + ["middle"] * 50 + ["y" * 10_000]
        out = lj.truncate_transcript(lines, max_chars=2_000)
        self.assertLess(len(out), 3_000)  # ~max_chars + marker overhead
        self.assertTrue(out.startswith("x"))
        self.assertTrue(out.rstrip().endswith("y"))
        self.assertIn("elided", out)

    def test_default_budget_is_16k_chars(self) -> None:
        self.assertEqual(lj.MAX_TRANSCRIPT_CHARS, 16_000)


class TestBuildPrompt(unittest.TestCase):
    def test_includes_all_dimensions(self) -> None:
        prompt = lj.build_prompt(["hello"], {"criteria": {}})
        for dim in lj.DIMENSIONS:
            self.assertIn(dim, prompt)

    def test_includes_rubric_criteria(self) -> None:
        rubric = {"name": "security", "criteria": {
            "safety": "heavy weight on exposed secrets",
            "correctness": "real vulnerabilities only, no false positives",
        }}
        prompt = lj.build_prompt(["x"], rubric)
        self.assertIn("heavy weight on exposed secrets", prompt)
        self.assertIn("real vulnerabilities", prompt)

    def test_transcript_excerpted_inside_markers(self) -> None:
        prompt = lj.build_prompt(["line-one", "line-two"], {"criteria": {}})
        self.assertIn("---BEGIN TRANSCRIPT---", prompt)
        self.assertIn("---END TRANSCRIPT---", prompt)
        self.assertIn("line-one", prompt)
        self.assertIn("line-two", prompt)


class TestParseScores(unittest.TestCase):
    def test_clean_json(self) -> None:
        resp = json.dumps({
            "correctness": {"score": 8, "justification": "ok"},
            "safety": {"score": 10, "justification": "spotless"},
        })
        parsed = lj.parse_scores(resp)
        self.assertEqual(parsed["correctness"], (8, "ok"))
        self.assertEqual(parsed["safety"], (10, "spotless"))

    def test_fenced_json_stripped(self) -> None:
        resp = '```json\n{"correctness": {"score": 7, "justification": "fine"}}\n```'
        parsed = lj.parse_scores(resp)
        self.assertEqual(parsed["correctness"], (7, "fine"))

    def test_trailing_commas_repaired(self) -> None:
        resp = '{"correctness": {"score": 6, "justification": "ok",},}'
        parsed = lj.parse_scores(resp)
        self.assertEqual(parsed["correctness"], (6, "ok"))

    def test_prose_wrapper_tolerated(self) -> None:
        resp = 'Sure! Here you go:\n{"correctness": {"score": 9, "justification": "strong"}}\nCheers.'
        parsed = lj.parse_scores(resp)
        self.assertEqual(parsed["correctness"], (9, "strong"))

    def test_scores_clamped_to_range(self) -> None:
        resp = json.dumps({
            "correctness": {"score": 42, "justification": "hot"},
            "safety":      {"score": -5, "justification": "cold"},
        })
        parsed = lj.parse_scores(resp)
        self.assertEqual(parsed["correctness"][0], 10)
        self.assertEqual(parsed["safety"][0], 1)

    def test_float_scores_rounded_to_int(self) -> None:
        resp = json.dumps({"correctness": {"score": 7.6, "justification": "near A"}})
        self.assertEqual(lj.parse_scores(resp)["correctness"][0], 8)

    def test_missing_dimensions_silently_dropped(self) -> None:
        resp = json.dumps({"correctness": {"score": 8, "justification": "ok"}})
        parsed = lj.parse_scores(resp)
        self.assertIn("correctness", parsed)
        self.assertNotIn("efficiency", parsed)

    def test_non_json_raises(self) -> None:
        with self.assertRaises(lj.LLMJudgeError):
            lj.parse_scores("totally not JSON")

    def test_non_object_root_raises(self) -> None:
        with self.assertRaises(lj.LLMJudgeError):
            lj.parse_scores("[1, 2, 3]")


class TestScoreWithLLM(unittest.TestCase):
    def test_shape_and_score_range(self) -> None:
        client = FakeClient(response_text=_canonical_response(score_per_dim=7))
        result = lj.score_with_llm(
            transcript=["hello world"],
            rubric={"name": "default", "criteria": {}},
            client=client,
        )
        self.assertEqual(set(result), set(lj.DIMENSIONS))
        for dim, (s, _) in result.items():
            self.assertGreaterEqual(s, 1)
            self.assertLessEqual(s, 10)

    def test_passes_configured_model(self) -> None:
        client = FakeClient(response_text=_canonical_response())
        lj.score_with_llm(
            transcript=["x"],
            rubric={"criteria": {}},
            model="claude-opus-4-7",
            client=client,
        )
        self.assertEqual(client.calls[0]["model"], "claude-opus-4-7")

    def test_failing_client_raises_judge_error(self) -> None:
        client = FakeClient(raises=lj.LLMJudgeError("rate limited"))
        with self.assertRaises(lj.LLMJudgeError):
            lj.score_with_llm(["x"], {"criteria": {}}, client=client)


class TestAnthropicClientConstruction(unittest.TestCase):
    def test_raises_without_api_key(self) -> None:
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with self.assertRaises(lj.LLMJudgeError):
                lj.AnthropicClient()

    def test_accepts_explicit_key(self) -> None:
        client = lj.AnthropicClient(api_key="sk-ant-test")
        self.assertEqual(client.api_key, "sk-ant-test")

    def test_budget_tokens_stored(self) -> None:
        client = lj.AnthropicClient(api_key="sk-ant-test", budget_tokens=1024)
        self.assertEqual(client.budget_tokens, 1024)


class TestBuildScorecardIntegration(unittest.TestCase):
    """score.build_scorecard must integrate the LLM pass when enabled."""

    def _fixture_transcript(self, tmp: Path) -> Path:
        path = tmp / "tx.jsonl"
        path.write_text(
            '{"role":"user","content":"/code-review review src/auth/middleware.py"}\n'
            '{"role":"assistant","content":"Looks clean."}\n',
            encoding="utf-8",
        )
        return path

    def _config(self, tmp: Path, enabled: bool) -> Path:
        cfg = {
            "auto_judge": {"enabled": True, "threshold": 5.0},
            "scoring": {"dimensions": {
                "correctness": 0.25, "completeness": 0.20, "adherence": 0.15,
                "actionability": 0.15, "efficiency": 0.10, "safety": 0.10,
                "consistency": 0.05,
            }},
            "llm_second_opinion": {
                "enabled": enabled,
                "model": "claude-haiku-4-5",
                "budget_tokens": None,
            },
        }
        path = tmp / "config.json"
        path.write_text(json.dumps(cfg), encoding="utf-8")
        return path

    def test_disabled_path_omits_llm_fields(self) -> None:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(self._fixture_transcript(tmp)),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(tmp / "scores"),
                config_path=str(self._config(tmp, enabled=False)),
            )
            for dim in card["dimensions"].values():
                self.assertNotIn("llm_score", dim)
                self.assertNotIn("llm_justification", dim)

    def test_enabled_path_merges_llm_fields(self) -> None:
        client = FakeClient(response_text=_canonical_response(score_per_dim=9))
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(self._fixture_transcript(tmp)),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(tmp / "scores"),
                config_path=str(self._config(tmp, enabled=True)),
                llm_client=client,
            )
            self.assertEqual(len(client.calls), 1)
            for dim in lj.DIMENSIONS:
                entry = card["dimensions"][dim]
                self.assertEqual(entry["llm_score"], 9)
                self.assertIn("llm view of", entry["llm_justification"])

    def test_enabled_path_with_failing_client_degrades_gracefully(self) -> None:
        client = FakeClient(raises=lj.LLMJudgeError("500 upstream"))
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            card = score.build_scorecard(
                skill_name="code-review",
                transcript_path=str(self._fixture_transcript(tmp)),
                rubric_dir=str(PROJECT_ROOT / "skills" / "judge" / "rubrics"),
                scores_dir=str(tmp / "scores"),
                config_path=str(self._config(tmp, enabled=True)),
                llm_client=client,
            )
            # Heuristic scores still present; LLM fields absent.
            for dim in card["dimensions"].values():
                self.assertIn("score", dim)
                self.assertNotIn("llm_score", dim)


if __name__ == "__main__":
    unittest.main()
