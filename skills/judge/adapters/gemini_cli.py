"""Gemini CLI session adapter.

The Gemini CLI (v0.38+) emits sessions as JSONL, one turn per line,
with shape roughly:

    {"role": "user"|"model"|"tool", "parts": [{"text": "..."}, ...], ...}

Older Gemini CLI builds and some community forks flatten ``parts`` to
``{"content": "..."}``. Occasional tool invocations land as
``{"functionCall": {"name": "...", "args": {...}}}`` siblings of
``parts``.  The adapter handles all three shapes plus a plain-text
fallback.

References (retrieved 2026-04-19):

- Gemini CLI session format is intentionally OpenAI-chat-adjacent but
  names the assistant turn ``"model"`` rather than ``"assistant"``.
  See the Gemini CLI docs' "Saved conversations" section.
- Function calls follow the Gemini API's ``functionCall`` / ``functionResponse``
  surface, not OpenAI's ``tool_calls`` envelope.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List


def _extract_parts(parts: Any) -> List[str]:
    """Gemini messages carry a ``parts`` array of typed parts."""
    if not isinstance(parts, list):
        return []
    out: List[str] = []
    for part in parts:
        if isinstance(part, dict):
            text = part.get("text")
            if isinstance(text, str) and text:
                out.append(text)
            # Newer Gemini builds nest function calls inside parts too.
            fn = part.get("functionCall") or part.get("function_call")
            if isinstance(fn, dict):
                name = fn.get("name")
                args = fn.get("args") if "args" in fn else fn.get("arguments")
                if name:
                    args_s = args if isinstance(args, str) else json.dumps(args or {})
                    out.append(f"tool_use: {name}({args_s})")
        elif isinstance(part, str) and part:
            out.append(part)
    return out


def _extract_message(msg: Any) -> List[str]:
    if not isinstance(msg, dict):
        return []
    out: List[str] = []

    # Shape A: newer — {"role": "...", "parts": [...]}
    if isinstance(msg.get("parts"), list):
        out.extend(_extract_parts(msg["parts"]))

    # Shape B: older/flattened — {"role": "...", "content": "..."}
    content = msg.get("content")
    if isinstance(content, str) and content:
        out.append(content)
    elif isinstance(content, list):
        out.extend(_extract_parts(content))

    # Shape C: top-level functionCall beside parts/content
    for fn_key in ("functionCall", "function_call"):
        fn = msg.get(fn_key)
        if isinstance(fn, dict):
            name = fn.get("name")
            args = fn.get("args") if "args" in fn else fn.get("arguments")
            if name:
                args_s = args if isinstance(args, str) else json.dumps(args or {})
                out.append(f"tool_use: {name}({args_s})")

    # functionResponse from the tool
    fr = msg.get("functionResponse") or msg.get("function_response")
    if isinstance(fr, dict):
        response = fr.get("response")
        if isinstance(response, (dict, list)):
            out.append(json.dumps(response))
        elif isinstance(response, str) and response:
            out.append(response)

    return out


def extract_lines(path: str) -> List[str]:
    """Return lines from a Gemini CLI session transcript.

    Accepts JSONL (one message per line), a top-level JSON array of
    messages, or an object with ``messages`` / ``turns`` arrays.
    Plain-text files are passed through as-is.
    """
    source = Path(path)
    if not source.is_file():
        return []
    raw = source.read_text(encoding="utf-8")

    stripped = raw.lstrip()
    if stripped.startswith("[") or stripped.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, list):
            out: List[str] = []
            for msg in data:
                out.extend(_extract_message(msg))
            return out
        if isinstance(data, dict):
            messages = data.get("messages") or data.get("turns")
            if isinstance(messages, list):
                out: List[str] = []
                for msg in messages:
                    out.extend(_extract_message(msg))
                return out

    # JSONL: one message per line
    jsonl_out: List[str] = []
    saw_json = False
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("{"):
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            saw_json = True
            jsonl_out.extend(_extract_message(msg))
    if saw_json:
        return jsonl_out

    # Plain text fallback
    return [
        line.strip()
        for line in raw.splitlines()
        if line.strip()
    ]
