"""Claude Code native transcript adapter.

Claude Code and Cowork write transcripts as JSONL, one record per line.
Records include ``{"role": "...", "content": "..."}`` for user /
assistant turns and ``{"type": "tool_use", ...}`` or similar for tool
calls. This is Verdict's reference format — extraction is a lightweight
re-expression of ``score.load_transcript`` that stays adapter-agnostic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List


def extract_lines(path: str) -> List[str]:
    """Return one text line per meaningful record in a Claude Code transcript."""
    source = Path(path)
    if not source.is_file():
        return []
    out: List[str] = []
    for raw in source.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue
        if not stripped.startswith("{"):
            out.append(stripped)
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            out.append(stripped)
            continue
        for key in ("content", "text", "message", "output", "data"):
            value = record.get(key)
            if isinstance(value, str) and value:
                out.append(value)
                break
            if isinstance(value, list):
                # Claude Code blocks: [{"type":"text","text":"..."}, ...]
                for block in value:
                    if isinstance(block, dict):
                        if isinstance(block.get("text"), str):
                            out.append(block["text"])
                        elif isinstance(block.get("content"), str):
                            out.append(block["content"])
                break
        else:
            out.append(stripped)
    return out
