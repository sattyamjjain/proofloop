"""Inspect AI evaluation-log adapter (read-only).

Parses the evaluation logs produced by UK AISI's ``inspect_ai`` runner
(`inspect.aisi.org.uk`). Inspect writes its logs either as JSON
(``.json``) or the binary framed ``.eval`` format. Verdict only reads
the JSON form — the binary form is out of scope for stdlib ingestion.
Callers with ``.eval`` logs should first run ``inspect log dump`` to
produce JSON, then point Verdict at the result.

Version range
-------------
Verdict tracks the **Inspect AI 0.3.x** log shape. Tested against
0.3.180 through 0.3.214 (PyPI latest as of 2026-04-26). 0.4.x is
unreleased; once it ships, the log shape may change and this adapter
will need a parallel branch. The :data:`INSPECT_AI_SUPPORTED_RANGE`
constant pins the expected range, and :func:`_check_inspect_ai_version`
emits a one-shot stderr warning the first time ``extract_lines`` is
called against an environment where ``inspect_ai.__version__`` falls
outside the range. The check is best-effort: if ``inspect_ai`` isn't
installed (the adapter only needs the JSON file, never the runtime),
the warning is silently skipped.

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
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

FINGERPRINT_TOKENS = (
    '"eval": {"task":',
    '"samples":',
    '"inspect_ai"',
)

# The 0.3.x major-line. 0.4.0 is unreleased as of 2026-04-26.
INSPECT_AI_SUPPORTED_RANGE: str = ">=0.3.180,<0.4.0"
_INSPECT_AI_MIN: Tuple[int, int, int] = (0, 3, 180)
_INSPECT_AI_MAX_EXCLUSIVE: Tuple[int, int, int] = (0, 4, 0)

# Module-level guard so the version warning fires at most once per
# Verdict process. Tests that exercise the warning path can reset it.
_VERSION_WARNING_EMITTED: bool = False

_ROLE_PREFIX = {
    "assistant": "[assistant]",
    "model":     "[assistant]",
    "user":      "[user]",
    "system":    "[system]",
    "tool":      "[tool_result]",
}


def _parse_version_tuple(version: str) -> Optional[Tuple[int, int, int]]:
    """Parse ``X.Y.Z[.suffix]`` into a 3-tuple of ints, or None on failure."""
    if not isinstance(version, str):
        return None
    cleaned = version.split("+", 1)[0]
    parts = cleaned.split(".", 3)[:3]
    if len(parts) < 2:
        return None
    while len(parts) < 3:
        parts.append("0")
    try:
        return (int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, TypeError):
        return None


def _check_inspect_ai_version(version: Optional[str] = None) -> Optional[str]:
    """Return a warning string if ``inspect_ai.__version__`` is out of range.

    *version* is injectable for tests; when omitted, the function
    lazy-imports ``inspect_ai`` and reads ``__version__``. If the
    package isn't installed (the adapter never needs the runtime),
    returns ``None`` — Verdict only reads the JSON log.

    Returns ``None`` when:
    - the version is in :data:`INSPECT_AI_SUPPORTED_RANGE`, or
    - ``inspect_ai`` is not installed, or
    - the version string is unparseable.
    """
    if version is None:
        try:
            import inspect_ai  # noqa: F401  (lazy, may not be installed)
            version = getattr(inspect_ai, "__version__", None)
        except ImportError:
            return None
    parsed = _parse_version_tuple(version) if version else None
    if parsed is None:
        return None
    if _INSPECT_AI_MIN <= parsed < _INSPECT_AI_MAX_EXCLUSIVE:
        return None
    return (
        f"[verdict] inspect_ai version {version} is outside the tested "
        f"range {INSPECT_AI_SUPPORTED_RANGE}; log-shape parsing may drift. "
        f"Verdict 1.3.x tracks Inspect AI 0.3.x; 0.4.x is unreleased as of "
        f"2026-04-26."
    )


def _maybe_warn_inspect_ai_version() -> None:
    """One-shot stderr warning gate, idempotent within a process."""
    global _VERSION_WARNING_EMITTED
    if _VERSION_WARNING_EMITTED:
        return
    warning = _check_inspect_ai_version()
    if warning:
        print(warning, file=sys.stderr)
    _VERSION_WARNING_EMITTED = True


def _reset_version_warning_guard() -> None:
    """Test hook: reset the one-shot warning gate."""
    global _VERSION_WARNING_EMITTED
    _VERSION_WARNING_EMITTED = False


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


def detection_score(path: str, scan_bytes: int = 2048) -> float:
    """Confidence score for the dispatch registry (0.0–1.0).

    Scoring tiers:
    - 0.85 — explicit ``"inspect_ai"`` literal in head (unambiguous).
    - 0.70 — ``"eval": {"task":`` co-occurs with ``"samples":`` (the
      canonical Inspect log envelope).
    - 0.50 — ``"samples":`` alone (could be other ML eval formats too,
      so the ``mlflow_trace`` adapter at 0.95 wins on its schema
      literal when traces carry both shapes — see Issue #11).
    """
    target = Path(path)
    if not target.is_file():
        return 0.0
    try:
        with target.open("rb") as handle:
            head = handle.read(scan_bytes)
    except OSError:
        return 0.0
    text = head.decode("utf-8", errors="replace")
    if '"inspect_ai"' in text:
        return 0.85
    if '"eval": {"task":' in text and '"samples":' in text:
        return 0.70
    if '"samples":' in text:
        return 0.50
    return 0.0


def extract_lines(path: str) -> List[str]:
    """Flatten an Inspect AI JSON log into Verdict-flavoured turn lines."""
    _maybe_warn_inspect_ai_version()
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
