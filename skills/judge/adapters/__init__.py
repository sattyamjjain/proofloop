"""Transcript adapters.

Each ecosystem (Claude Code, Cowork, OpenAI Codex, OpenAI-compatible
clients) emits session transcripts in a different shape. The scoring
engine consumes a flat ``List[str]`` of lines with one
assistant/tool/user utterance per line. Adapters convert from the
ecosystem-native format to that shape.

Per the v4.3 scope contract (CLAUDE.md §v4.3 Scope Contract), only
plugin-domain adapters are in-scope. Cross-ecosystem benches
(Gemini, MLflow, Inspect-AI, Terminal-Bench, browser-harness) were
removed in v2.0.0.

Selection order:
    1. ``--adapter <name>`` CLI flag
    2. Fallback to the Claude Code adapter (the native format)
"""
from __future__ import annotations

from typing import Callable, Dict, List

from .claude_code import extract_lines as _claude_code_extract
from .codex import extract_lines as _codex_extract
from .cowork import extract_lines as _cowork_extract
from .openai_compatible import extract_lines as _openai_compatible_extract

Adapter = Callable[[str], List[str]]

ADAPTERS: Dict[str, Adapter] = {
    "claude-code": _claude_code_extract,
    "codex": _codex_extract,
    "cowork": _cowork_extract,
    "openai-compatible": _openai_compatible_extract,
    "cursor": _openai_compatible_extract,
    "continue": _openai_compatible_extract,
}


def detect_adapter(path: str) -> str:
    """Return the default adapter name.

    The v4.3 scope reset removed the cross-ecosystem detection
    scorers (MLflow, Inspect-AI, Terminal-Bench, browser-harness,
    Gemini Deep Research). Callers that previously depended on
    auto-detection now fall through to the Claude Code adapter,
    which is the native plugin format. Pass ``--adapter <name>``
    explicitly for the OpenAI-compatible / Codex / Cowork shapes.
    """
    return "claude-code"


def list_adapters() -> List[str]:
    """Return the registered adapter names in deterministic order."""
    return sorted(ADAPTERS)


def get_adapter(name: str) -> Adapter:
    """Return the adapter callable for *name* or raise KeyError."""
    return ADAPTERS[name]


__all__ = [
    "Adapter",
    "ADAPTERS",
    "list_adapters",
    "get_adapter",
    "detect_adapter",
]
