"""Claude Cowork transcript adapter.

Cowork session transcripts follow the same JSONL shape as Claude Code.
They differ operationally (cloud-managed, routine-triggered runs include
a ``routine_id`` marker) but the text-extraction logic is identical. We
delegate to the Claude Code adapter and expose a dedicated entry point
so the adapter registry and documentation remain explicit about the
ecosystem.
"""
from __future__ import annotations

from typing import List

from .claude_code import extract_lines as _claude_code_extract


def extract_lines(path: str) -> List[str]:
    """Return lines for a Cowork transcript."""
    return _claude_code_extract(path)
