"""OpenAI Codex CLI session adapter.

Codex writes sessions as markdown plus a JSON sidecar in ``~/.codex/sessions/``.
The markdown file already reads as lines; the JSON sidecar (when present)
may carry ``events`` or ``messages`` in a shape close to the OpenAI chat
format. This adapter handles both by delegating to the OpenAI-compatible
adapter for JSON inputs and falling through to plain-line reading for
markdown inputs.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

from .openai_compatible import extract_lines as _openai_extract


def extract_lines(path: str) -> List[str]:
    """Return lines from a Codex session markdown file or JSON sidecar."""
    source = Path(path)
    if not source.is_file():
        return []
    if source.suffix.lower() == ".json" or source.suffix.lower() == ".jsonl":
        return _openai_extract(str(source))
    # Markdown / plain text: one non-empty line per entry
    return [
        line.strip()
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
