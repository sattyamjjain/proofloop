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

Adapter = Callable[[str], List[str]]

ADAPTERS: Dict[str, Adapter] = {
    "claude-code": _claude_code_extract,
    "cowork": _cowork_extract,
    "openai-compatible": _openai_compatible_extract,
    "codex": _codex_extract,
    "cursor": _openai_compatible_extract,
    "continue": _openai_compatible_extract,
}


def list_adapters() -> List[str]:
    """Return the registered adapter names in deterministic order."""
    return sorted(ADAPTERS)


def get_adapter(name: str) -> Adapter:
    """Return the adapter callable for *name* or raise KeyError."""
    return ADAPTERS[name]


__all__ = ["Adapter", "ADAPTERS", "list_adapters", "get_adapter"]
