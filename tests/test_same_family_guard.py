#!/usr/bin/env python3
"""Tests for the same-family self-preference judge guard.

The guard lives in ``skills/judge/analyzers/llm_judge.py`` and is wired
into ``score._maybe_llm_second_opinion`` /
``score.build_scorecard``. It compares the model that produced the
transcript against the configured second-opinion judge model; when they
share a vendor family the second opinion is self-preference-biased
upward, so the guard flags ``self_preference_risk`` and (when a
cross-family alternate is configured) auto-prefers it.

All tests are offline — the LLM path is exercised through a mock client
so no network call happens. Stdlib-only.
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge"))
sys.path.insert(0, str(PROJECT_ROOT / "skills" / "judge" / "scripts"))

from analyzers import llm_judge as lj  # noqa: E402
import score  # noqa: E402


class FakeClient:
    """In-memory LLMClient that records which model it was asked to call."""

    def __init__(self, score_per_dim: int = 8) -> None:
        self.score_per_dim = score_per_dim
        self.calls: List[Dict[str, Any]] = []

    def messages_create(self, model: str, system: str, prompt: str, max_tokens: int) -> str:
        self.calls.append({"model": model, "system": system, "prompt": prompt})
        return json.dumps({
            dim: {"score": self.score_per_dim, "justification": f"view of {dim}"}
            for dim in lj.DIMENSIONS
        })

    @property
    def last_model(self) -> Optional[str]:
        return self.calls[-1]["model"] if self.calls else None


# ---------------------------------------------------------------------------
# model_family bucketing
# ---------------------------------------------------------------------------


class TestModelFamily(unittest.TestCase):
    def test_anthropic_prefixes(self) -> None:
        for mid in ("claude-haiku-4-5", "claude-opus-4-8", "anthropic/claude-sonnet-4-6"):
            self.assertEqual(lj.model_family(mid), "anthropic", mid)

    def test_openai_prefixes(self) -> None:
        for mid in ("gpt-4o", "gpt-5", "o3-mini", "o1-preview", "chatgpt-4o-latest"):
            self.assertEqual(lj.model_family(mid), "openai", mid)

    def test_google_prefixes(self) -> None:
        for mid in ("gemini-2.5-pro", "gemini-1.5-flash", "gemma-2-27b"):
            self.assertEqual(lj.model_family(mid), "google", mid)

    def test_meta_prefixes(self) -> None:
        for mid in ("llama-3.1-70b", "codellama-34b", "meta-llama-3"):
            self.assertEqual(lj.model_family(mid), "meta", mid)

    def test_unknown_and_empty(self) -> None:
        for mid in ("mystery-7b", "", None, "  "):
            self.assertIsNone(lj.model_family(mid), mid)

    def test_case_insensitive_and_vendor_slug(self) -> None:
        self.assertEqual(lj.model_family("CLAUDE-OPUS-4-8"), "anthropic")
        self.assertEqual(lj.model_family("openai:gpt-4o"), "openai")


# ---------------------------------------------------------------------------
# same_family_guard
# ---------------------------------------------------------------------------


class TestSameFamilyGuard(unittest.TestCase):
    def test_same_family_flags_risk_with_citation(self) -> None:
        g = lj.same_family_guard("claude-opus-4-8", "claude-haiku-4-5")
        self.assertTrue(g["self_preference_risk"])
        self.assertEqual(g["executing_family"], "anthropic")
        self.assertEqual(g["judge_family"], "anthropic")
        # The reason cites the measured self-preference effect.
        self.assertIn("self-preference", g["reason"])
        self.assertIn("self-win-rate", g["reason"])
        self.assertFalse(g["auto_preferred"])
        self.assertIsNone(g["preferred_model"])

    def test_cross_family_clears_risk(self) -> None:
        g = lj.same_family_guard("claude-opus-4-8", "gpt-4o")
        self.assertFalse(g["self_preference_risk"])
        self.assertEqual(g["reason"], "")
        self.assertFalse(g["auto_preferred"])

    def test_unknown_executing_model_asserts_no_risk(self) -> None:
        # Can't substantiate a clash against an unrecognised model.
        g = lj.same_family_guard("mystery-7b", "claude-haiku-4-5")
        self.assertFalse(g["self_preference_risk"])
        self.assertIsNone(g["executing_family"])

    def test_auto_prefer_picks_first_cross_family_alternate(self) -> None:
        g = lj.same_family_guard(
            "claude-opus-4-8", "claude-haiku-4-5",
            alternate_judge_models=["claude-sonnet-4-6", "gpt-4o", "gemini-2.5-pro"],
        )
        self.assertTrue(g["self_preference_risk"])
        self.assertTrue(g["auto_preferred"])
        # claude-sonnet-4-6 is same-family (skipped); gpt-4o is the first
        # cross-family entry.
        self.assertEqual(g["preferred_model"], "gpt-4o")

    def test_auto_prefer_noop_when_all_alternates_same_family(self) -> None:
        g = lj.same_family_guard(
            "claude-opus-4-8", "claude-haiku-4-5",
            alternate_judge_models=["claude-sonnet-4-6", "claude-opus-4-7"],
        )
        self.assertTrue(g["self_preference_risk"])
        self.assertFalse(g["auto_preferred"])
        self.assertIsNone(g["preferred_model"])


# ---------------------------------------------------------------------------
# build_prompt / SYSTEM_PROMPT must never use first-person framing
# ---------------------------------------------------------------------------


class TestNoFirstPersonFraming(unittest.TestCase):
    """The judge is framed as a third-party reviewer, never the author.

    First-person framing ("your work") is exactly the role-relabel
    vector that swings scores +23-93pp (arXiv:2606.05976), so the
    rendered prompt and system prompt must avoid it.
    """

    FORBIDDEN = ("you wrote", "your work", "your output", "you produced", "your code")

    def _render(self) -> str:
        rubric = {
            "name": "code-review",
            "criteria": {dim: f"criteria for {dim}" for dim in lj.DIMENSIONS},
        }
        transcript = ["did the work", "verified the output against the spec"]
        return lj.build_prompt(transcript, rubric)

    def test_build_prompt_has_no_first_person(self) -> None:
        rendered = self._render().lower()
        for phrase in self.FORBIDDEN:
            self.assertNotIn(phrase, rendered, f"build_prompt leaked first-person: {phrase!r}")

    def test_system_prompt_has_no_first_person(self) -> None:
        system = lj.SYSTEM_PROMPT.lower()
        for phrase in self.FORBIDDEN:
            self.assertNotIn(phrase, system, f"SYSTEM_PROMPT leaked first-person: {phrase!r}")
        # Positive: the third-party framing is intact.
        self.assertIn("second-opinion judge", lj.SYSTEM_PROMPT)


# ---------------------------------------------------------------------------
# Integration through score.build_scorecard
# ---------------------------------------------------------------------------


class TestGuardIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.scores = self.tmp / "scores"
        self.rubric_dir = str(PROJECT_ROOT / "skills" / "judge" / "rubrics")
        # Transcript whose embedded executing model is Claude.
        self.transcript = self.tmp / "t.jsonl"
        self.transcript.write_text(
            '{"model":"claude-opus-4-8"}\n'
            '{"role":"assistant","content":"completed the task; verified output"}\n',
            encoding="utf-8",
        )

    def _config(self, **llm_extra: Any) -> str:
        cfg = {
            "llm_second_opinion": {
                "enabled": True, "model": "claude-haiku-4-5", **llm_extra,
            }
        }
        path = self.tmp / f"cfg_{len(llm_extra)}_{id(llm_extra)}.json"
        path.write_text(json.dumps(cfg), encoding="utf-8")
        return str(path)

    def test_same_family_sets_flag_and_warns(self) -> None:
        client = FakeClient()
        buf = io.StringIO()
        with redirect_stderr(buf):
            sc = score.build_scorecard(
                "code-review", str(self.transcript), self.rubric_dir,
                str(self.scores), config_path=self._config(), llm_client=client,
            )
        self.assertTrue(sc["self_preference_risk"])
        self.assertEqual(sc["same_family_guard"]["executing_family"], "anthropic")
        self.assertEqual(sc["same_family_guard"]["judge_family"], "anthropic")
        self.assertFalse(sc["same_family_guard"]["auto_preferred"])
        self.assertIn("Verdict WARNING", buf.getvalue())
        # No alternate → judge model unchanged.
        self.assertEqual(client.last_model, "claude-haiku-4-5")

    def test_cross_family_alternate_is_auto_preferred(self) -> None:
        client = FakeClient()
        buf = io.StringIO()
        with redirect_stderr(buf):
            sc = score.build_scorecard(
                "code-review", str(self.transcript), self.rubric_dir,
                str(self.scores),
                config_path=self._config(alternate_judge_models=["gpt-4o"]),
                llm_client=client,
            )
        self.assertTrue(sc["self_preference_risk"])
        self.assertTrue(sc["same_family_guard"]["auto_preferred"])
        self.assertEqual(sc["same_family_guard"]["preferred_model"], "gpt-4o")
        # The judge actually invoked switched to the cross-family model.
        self.assertEqual(client.last_model, "gpt-4o")
        self.assertIn("auto-preferring", buf.getvalue())

    def test_disabled_second_opinion_omits_flag(self) -> None:
        # When the LLM second opinion is off (default), the guard never
        # runs and the scorecard carries no self_preference_risk key.
        cfg = self.tmp / "cfg_off.json"
        cfg.write_text(json.dumps({"llm_second_opinion": {"enabled": False}}), encoding="utf-8")
        sc = score.build_scorecard(
            "code-review", str(self.transcript), self.rubric_dir,
            str(self.scores), config_path=str(cfg),
        )
        self.assertNotIn("self_preference_risk", sc)
        self.assertNotIn("same_family_guard", sc)


if __name__ == "__main__":
    unittest.main()
