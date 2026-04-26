"""Transcript adapters.

Each ecosystem (Claude Code, Cowork, OpenAI Codex, Cursor, Continue,
Gemini CLI, Windsurf) emits session transcripts in a different shape.
The scoring engine consumes a flat ``List[str]`` of lines with one
assistant/tool/user utterance per line. Adapters convert from the
ecosystem-native format to that shape.

Selection order:
    1. ``--adapter <name>`` CLI flag
    2. Auto-detection from the file extension / first-line sniff
    3. Fallback to the Claude Code adapter (the native format)
"""
from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from .claude_code import extract_lines as _claude_code_extract
from .cowork import extract_lines as _cowork_extract
from .openai_compatible import extract_lines as _openai_compatible_extract
from .codex import extract_lines as _codex_extract
from .gemini_cli import extract_lines as _gemini_cli_extract
from .mlflow_trace import (
    extract_lines as _mlflow_trace_extract,
    looks_like_mlflow_trace as _mlflow_trace_fingerprint,
    detection_score as _mlflow_trace_score,
)
from .inspect_ai_log import (
    extract_lines as _inspect_ai_extract,
    looks_like_inspect_ai_log as _inspect_ai_fingerprint,
    detection_score as _inspect_ai_score,
)
from .terminal_bench import (
    extract_lines as _terminal_bench_extract,
    looks_like_terminal_bench as _terminal_bench_fingerprint,
    detection_score as _terminal_bench_score,
)
from .gemini_deep_research import (
    extract_lines as _gemini_deep_research_extract,
    looks_like_gemini_deep_research as _gemini_deep_research_fingerprint,
    detection_score as _gemini_deep_research_score,
)

Adapter = Callable[[str], List[str]]

ADAPTERS: Dict[str, Adapter] = {
    "claude-code": _claude_code_extract,
    "cowork": _cowork_extract,
    "openai-compatible": _openai_compatible_extract,
    "codex": _codex_extract,
    "cursor": _openai_compatible_extract,
    "continue": _openai_compatible_extract,
    "gemini-cli": _gemini_cli_extract,
    "gemini": _gemini_cli_extract,
    "mlflow-trace": _mlflow_trace_extract,
    "mlflow": _mlflow_trace_extract,
    "inspect-ai": _inspect_ai_extract,
    "inspect": _inspect_ai_extract,
    "terminal-bench": _terminal_bench_extract,
    "terminal": _terminal_bench_extract,
    "gemini-deep-research": _gemini_deep_research_extract,
    "gemini-deep": _gemini_deep_research_extract,
}


_DETECTION_SCORERS: List[Tuple[str, Callable[[str], float]]] = [
    ("gemini-deep-research", _gemini_deep_research_score),
    ("mlflow-trace", _mlflow_trace_score),
    ("inspect-ai", _inspect_ai_score),
    ("terminal-bench", _terminal_bench_score),
]


def detect_adapter(path: str) -> str:
    """Auto-detect the adapter name for *path* by confidence score.

    Each registered adapter exposes a ``detection_score(path) -> float``
    in the ``[0.0, 1.0]`` range. The dispatcher computes scores across
    all candidates and returns the highest-scoring adapter name; ties
    break by the registry order in :data:`_DETECTION_SCORERS`.

    Returns ``"claude-code"`` (the native format) when no adapter
    scores above ``0.0``.

    Issue #11 (the OTel-enriched MLflow trace + Inspect AI samples
    collision after Y6) motivated the switch from first-match-wins
    boolean fingerprints to score-based dispatch. The Trace schema
    literal scores 0.95 vs Inspect's 0.70, so a trace carrying both
    shapes resolves to MLflow correctly.
    """
    best_name = "claude-code"
    best_score = 0.0
    for name, scorer in _DETECTION_SCORERS:
        try:
            score = scorer(path)
        except Exception:
            score = 0.0
        if score > best_score:
            best_name = name
            best_score = score
    return best_name


def list_adapters() -> List[str]:
    """Return the registered adapter names in deterministic order."""
    return sorted(ADAPTERS)


def get_adapter(name: str) -> Adapter:
    """Return the adapter callable for *name* or raise KeyError."""
    return ADAPTERS[name]


__all__ = ["Adapter", "ADAPTERS", "list_adapters", "get_adapter", "detect_adapter"]
