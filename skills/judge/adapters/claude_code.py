"""Claude Code native transcript adapter.

Claude Code and Cowork write transcripts as JSONL, one record per line.
Records include ``{"role": "...", "content": "..."}`` for user /
assistant turns and ``{"type": "tool_use", ...}`` or similar for tool
calls. This is Verdict's reference format — extraction is a lightweight
re-expression of ``score.load_transcript`` that stays adapter-agnostic.

Auto Memory (Opus 4.7, 2026-04-17+)
-----------------------------------
A single "transcript" may span many ``~/.claude/history/*.jsonl`` files
plus a memory preamble that Claude Code injects at the top of every
new session. To handle that, ``extract_lines`` accepts EITHER a file
path OR a directory:

- **File**: behaviour identical to pre-1.2 Verdict.
- **Directory**: enumerate ``*.jsonl`` sorted by mtime (oldest first),
  concatenate the extracted lines, and inject a ``--- session break ---``
  marker between files so downstream heuristics can attribute signals
  to the right session.

Memory preambles are recognised by any of these tokens at the top of
the first session's payload: ``memory_block``, ``<memory>``,
``auto-memory``, ``claude_memory``. Lines inside a memory block are
prefixed with ``[system-memory]`` so ``score.py`` can choose to treat
them as system context rather than user-turn output.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List

SESSION_BREAK_MARKER: str = "--- session break ---"
MEMORY_PREFIX: str = "[system-memory] "

_MEMORY_TOKENS = ("memory_block", "<memory>", "auto-memory", "claude_memory")


def _is_memory_marker(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in _MEMORY_TOKENS)


def _extract_from_record(record: dict, raw_line: str, in_memory: bool) -> List[str]:
    """Pull readable text out of a single JSONL record.

    ``raw_line`` is the stripped input line, used as the fallback when
    no known text field is present — preserves pre-v1.2 byte-for-byte
    behaviour for the no-match branch.
    """
    out: List[str] = []
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
        out.append(raw_line)
    if in_memory:
        out = [MEMORY_PREFIX + line for line in out]
    return out


def _extract_lines_from_file(path: Path) -> List[str]:
    """Return one readable line per meaningful JSONL record in *path*."""
    if not path.is_file():
        return []
    out: List[str] = []
    in_memory = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue

        # Detect a memory preamble block on entry. Memory blocks end at
        # the first record that does NOT look like a memory marker and
        # carries a recognised role (user/assistant/system/tool). This
        # heuristic is deliberately loose — false positives only mean
        # the line gets a ``[system-memory]`` tag, they don't change
        # the heuristic scorer's pass/fail behaviour.
        if not stripped.startswith("{"):
            out.append(stripped)
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            out.append(stripped)
            continue

        role = record.get("role") if isinstance(record, dict) else None
        raw_text = json.dumps(record, separators=(",", ":")) if isinstance(record, dict) else stripped

        if not in_memory and _is_memory_marker(raw_text):
            in_memory = True
        # A user turn ends any active memory block.
        if role in ("user",):
            in_memory = False
        elif role in ("assistant", "tool") and in_memory and not _is_memory_marker(raw_text):
            # Once we see an assistant/tool turn that's no longer
            # marker-tagged, close the block.
            in_memory = False

        out.extend(_extract_from_record(
            record if isinstance(record, dict) else {},
            stripped,
            in_memory,
        ))
    return out


def extract_lines(path: str) -> List[str]:
    """Return one text line per meaningful record in a Claude Code transcript.

    Accepts either a regular file path or a directory of ``*.jsonl``
    session files (Auto Memory layout). Returned lines are flat; session
    boundaries in multi-file input are denoted by the
    :data:`SESSION_BREAK_MARKER` line. Memory-preamble lines are
    prefixed with :data:`MEMORY_PREFIX`.
    """
    source = Path(path)
    if source.is_dir():
        session_files = sorted(
            (p for p in source.glob("*.jsonl") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
        )
        if not session_files:
            return []
        combined: List[str] = []
        for index, session_path in enumerate(session_files):
            if index > 0:
                combined.append(SESSION_BREAK_MARKER)
            combined.extend(_extract_lines_from_file(session_path))
        return combined
    return _extract_lines_from_file(source)
