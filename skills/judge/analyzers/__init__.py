"""Pluggable scoring analyzers beyond the heuristic engine.

v1.2.0+ adds ``llm_judge``, an opt-in second-opinion path that calls
Claude (default ``claude-haiku-4-5``) to produce dimension scores
alongside the default heuristic output. Gated by
``judge-config.json.llm_second_opinion.enabled`` — off by default so
Proofloop's offline-first promise is preserved.
"""
from __future__ import annotations

from .llm_judge import (
    AnthropicClient,
    LLMJudgeError,
    score_with_llm,
)

__all__ = ["AnthropicClient", "LLMJudgeError", "score_with_llm"]
