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

from typing import Callable, Dict, List

from .claude_code import extract_lines as _claude_code_extract
from .cowork import extract_lines as _cowork_extract
from .openai_compatible import extract_lines as _openai_compatible_extract
from .codex import extract_lines as _codex_extract
from .gemini_cli import extract_lines as _gemini_cli_extract
from .mlflow_trace import (
    extract_lines as _mlflow_trace_extract,
    looks_like_mlflow_trace as _mlflow_trace_fingerprint,
)
from .inspect_ai_log import (
    extract_lines as _inspect_ai_extract,
    looks_like_inspect_ai_log as _inspect_ai_fingerprint,
)
from .terminal_bench import (
    extract_lines as _terminal_bench_extract,
    looks_like_terminal_bench as _terminal_bench_fingerprint,
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
}


def detect_adapter(path: str) -> str:
    """Auto-detect the adapter name for *path* by file-head sniff.

    Returns the adapter name; falls back to ``"claude-code"`` when
    nothing else matches. v1.3.0 detects MLflow traces and Inspect AI
    evaluation logs; the other ecosystems don't carry a stable
    fingerprint we can rely on without parsing the whole file.
    """
    if _inspect_ai_fingerprint(path):
        return "inspect-ai"
    if _mlflow_trace_fingerprint(path):
        return "mlflow-trace"
    if _terminal_bench_fingerprint(path):
        return "terminal-bench"
    return "claude-code"


def list_adapters() -> List[str]:
    """Return the registered adapter names in deterministic order."""
    return sorted(ADAPTERS)


def get_adapter(name: str) -> Adapter:
    """Return the adapter callable for *name* or raise KeyError."""
    return ADAPTERS[name]


__all__ = ["Adapter", "ADAPTERS", "list_adapters", "get_adapter", "detect_adapter"]
