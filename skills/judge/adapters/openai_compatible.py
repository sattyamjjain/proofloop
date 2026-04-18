"""OpenAI-compatible chat-transcript adapter.

Cursor, Continue, and a number of smaller ecosystems persist sessions
as a JSON array of ``{"role": "user"|"assistant"|"system", "content": "..."}``
messages, possibly with ``tool_calls`` and ``tool_call_id`` fields. This
adapter extracts the text portion of each message and flattens tool-call
arguments so the scoring heuristics (tool-call density, retries) still
fire.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List


def _coerce_content(content: Any) -> List[str]:
    """Normalise message ``content`` into a list of text lines."""
    if isinstance(content, str):
        return [content] if content else []
    if isinstance(content, list):
        out: List[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text") or part.get("content")
                if isinstance(text, str) and text:
                    out.append(text)
            elif isinstance(part, str) and part:
                out.append(part)
        return out
    return []


def _coerce_tool_calls(tool_calls: Any) -> List[str]:
    """Flatten tool_calls array into per-call text lines."""
    if not isinstance(tool_calls, list):
        return []
    lines: List[str] = []
    for call in tool_calls:
        if not isinstance(call, dict):
            continue
        function = call.get("function") or {}
        name = function.get("name") if isinstance(function, dict) else None
        args = function.get("arguments") if isinstance(function, dict) else None
        if name:
            args_s = args if isinstance(args, str) else json.dumps(args or {})
            lines.append(f"tool_use: {name}({args_s})")
    return lines


def _extract_from_messages(messages: List[Any]) -> List[str]:
    out: List[str] = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        out.extend(_coerce_content(msg.get("content")))
        out.extend(_coerce_tool_calls(msg.get("tool_calls")))
    return out


def extract_lines(path: str) -> List[str]:
    """Return lines from an OpenAI-compatible chat transcript.

    Accepts either:
      - a top-level JSON array of messages
      - an object with a ``messages`` array
      - JSONL with one message per line
    """
    source = Path(path)
    if not source.is_file():
        return []
    raw = source.read_text(encoding="utf-8")
    stripped = raw.lstrip()
    # Top-level JSON array or object
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            return _extract_from_messages(data)
        if isinstance(data, dict):
            messages = data.get("messages")
            if isinstance(messages, list):
                return _extract_from_messages(messages)
    # Fallback: JSONL, one message per line
    out: List[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        out.extend(_extract_from_messages([msg]))
    return out
