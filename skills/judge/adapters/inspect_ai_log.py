"""Inspect AI evaluation-log adapter (read-only).

Parses the evaluation logs produced by UK AISI's ``inspect_ai`` runner
(`inspect.aisi.org.uk`, 2026-04-20 stable release 0.3). Inspect writes
its logs either as JSON (``.json``) or the binary framed ``.eval``
format. Verdict only reads the JSON form — the binary form is out of
scope for stdlib ingestion. Callers with ``.eval`` logs should first
run ``inspect log dump`` to produce JSON, then point Verdict at the
result.

Canonical shape (v0.3, verified 2026-04-24):

.. code-block:: json

   {
     "version": 2,
     "eval": {"task": "security_bench/path_traversal", "model": "openai/gpt-4o"},
     "samples": [
       {
         "id": "sample-1",
         "input": "...",
         "target": "...",
         "messages": [
           {"role": "user",      "content": "..."},
           {"role": "assistant", "content": "...",
            "tool_calls": [
              {"function": {"name": "read_file", "arguments": "{...}"}}
             ]
           },
           {"role": "tool", "tool_call_id": "...", "content": "..."}
         ],
         "scores": [{"name": "match", "value": 1.0, "answer": "..."}]
       }
     ]
   }

Verdict emits one prefix-tagged line per turn, in the order Inspect
traversed them:

- ``[assistant] <content>`` for model turns.
- ``[tool_call] <name>(<args>)`` for each tool invocation on an assistant turn.
- ``[tool_result] <content>`` for tool-role messages.
- ``[user] <content>`` for user / input turns.
- ``[ground_truth_score] <name>=<value>`` for scorer verdicts — preserved
  so Verdict's correctness/adherence analyzers can read them as sentinels.

The adapter never imports ``inspect_ai`` itself; ingestion stays
offline-first. Missing / malformed fields degrade to an empty list
rather than raising.

Market signal: `UKGovernmentBEIS/inspect_ai <https://github.com/UKGovernmentBEIS/inspect_ai>`_.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

FINGERPRINT_TOKENS = (
    '"eval": {"task":',
    '"samples":',
    '"inspect_ai"',
)

_ROLE_PREFIX = {
    "assistant": "[assistant]",
    "model":     "[assistant]",
    "user":      "[user]",
    "system":    "[system]",
    "tool":      "[tool_result]",
}


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _flatten_content(content: Any) -> str:
    """Collapse Inspect's content-block list shape into a single string."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return _stringify(content)


def _tool_calls(message: Dict[str, Any]) -> Iterable[str]:
    """Yield `[tool_call] name(args)` lines for every tool call on a turn."""
    raw = message.get("tool_calls")
    if not isinstance(raw, list):
        return
    for call in raw:
        if not isinstance(call, dict):
            continue
        fn = call.get("function") if isinstance(call.get("function"), dict) else call
        name = fn.get("name", "tool") if isinstance(fn, dict) else "tool"
        args = fn.get("arguments") if isinstance(fn, dict) else None
        yield f"[tool_call] {name}({_stringify(args)})"


def _scorer_lines(sample: Dict[str, Any]) -> Iterable[str]:
    """Flatten Inspect scorer verdicts into ``[ground_truth_score]`` sentinels."""
    raw = sample.get("scores")
    if not isinstance(raw, list):
        return
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        name = entry.get("name") or entry.get("scorer") or "score"
        value = entry.get("value")
        if value is None:
            value = entry.get("score")
        if value is None:
            continue
        yield f"[ground_truth_score] {name}={_stringify(value)}"


def _message_lines(message: Any) -> Iterable[str]:
    if not isinstance(message, dict):
        return
    role = str(message.get("role", "")).lower()
    prefix = _ROLE_PREFIX.get(role, f"[{role}]" if role else "[assistant]")
    content = _flatten_content(message.get("content"))
    if content:
        yield f"{prefix} {content}"
    if role in ("assistant", "model"):
        yield from _tool_calls(message)


def _sample_lines(sample: Any) -> Iterable[str]:
    if not isinstance(sample, dict):
        return
    sample_id = sample.get("id") or sample.get("sample_id")
    if sample_id:
        yield f"[sample_start] {sample_id}"
    messages = sample.get("messages")
    if isinstance(messages, list):
        for message in messages:
            yield from _message_lines(message)
    yield from _scorer_lines(sample)


def detect(head: bytes) -> bool:
    """Fingerprint the first bytes of an Inspect AI JSON log."""
    if not head:
        return False
    try:
        text = head.decode("utf-8", errors="replace")
    except AttributeError:
        return False
    return any(token in text for token in FINGERPRINT_TOKENS)


def looks_like_inspect_ai_log(path: str, scan_bytes: int = 2048) -> bool:
    """Heuristic autoloader: does *path* head look like an Inspect AI log?"""
    target = Path(path)
    if not target.is_file():
        return False
    try:
        with target.open("rb") as handle:
            head = handle.read(scan_bytes)
    except OSError:
        return False
    return detect(head)


def extract_lines(path: str) -> List[str]:
    """Flatten an Inspect AI JSON log into Verdict-flavoured turn lines."""
    source = Path(path)
    if not source.is_file():
        return []
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(payload, dict):
        return []

    out: List[str] = []
    eval_meta = payload.get("eval")
    if isinstance(eval_meta, dict):
        task = eval_meta.get("task")
        if task:
            out.append(f"[task] {task}")
        model = eval_meta.get("model")
        if model:
            out.append(f"[model] {model}")

    samples = payload.get("samples")
    if isinstance(samples, list):
        for sample in samples:
            out.extend(_sample_lines(sample))
    return out
