"""MLflow trace ingestion adapter (read-only).

Parses the JSON exports produced by ``mlflow.autolog()`` +
``mlflow.genai.evaluate()`` runs without importing the ``mlflow``
runtime. This preserves Verdict's offline-first promise: users scoring
their MLflow traces never have to install MLflow as a Verdict dep.

Expected shape (2026-04-20 MLflow ``mlflow.entities.Trace``):

.. code-block:: json

   {
     "schema": "mlflow.entities.Trace",
     "info": {"request_id": "...", "trace_id": "...", "status": "OK"},
     "data": {
       "spans": [
         {"name": "run", "events": [
           {"name": "tool_call",   "attributes": {"name":"search","args":"{...}"}},
           {"name": "tool_result", "attributes": {"name":"search","result":"..."}},
           {"name": "assistant",   "attributes": {"content":"..."}},
           {"name": "user",        "attributes": {"content":"..."}}
         ]}
       ]
     }
   }

Real MLflow traces carry more metadata; the adapter is tolerant of
missing fields and only extracts the pieces Verdict scores against.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List

# Fingerprint string — when present in the first ~2 KB of a file the
# registry's auto-detection path picks this adapter.
TRACE_FINGERPRINT: str = "mlflow.entities.Trace"

_EVENT_PREFIX = {
    "tool_call":    "[tool_call]",
    "tool_use":     "[tool_call]",
    "tool_result":  "[tool_result]",
    "tool_return":  "[tool_result]",
    "assistant":    "[assistant]",
    "user":         "[user]",
    "system":       "[system]",
    "note":         "[note]",
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


def _event_to_line(event: Any) -> str:
    """Flatten a single span event into a prefix-tagged Verdict line."""
    if not isinstance(event, dict):
        return ""
    name = str(event.get("name", "event")).lower()
    prefix = _EVENT_PREFIX.get(name, f"[{name}]")
    raw_attrs = event.get("attributes")
    attrs: dict = raw_attrs if isinstance(raw_attrs, dict) else {}
    # Prefer a canonical text-bearing attribute; fall through to the
    # whole attributes dict when none present.
    for key in ("content", "text", "message", "result", "args", "arguments"):
        if key in attrs:
            return f"{prefix} {_stringify(attrs[key])}"
    return f"{prefix} {_stringify(attrs)}" if attrs else prefix


def _iter_events(trace: dict) -> Iterable[Any]:
    """Yield events from every span in a trace, preserving span order."""
    data = trace.get("data")
    if not isinstance(data, dict):
        return
    spans = data.get("spans")
    if not isinstance(spans, list):
        return
    for span in spans:
        if not isinstance(span, dict):
            continue
        events = span.get("events")
        if not isinstance(events, list):
            continue
        yield from events


def extract_lines(trace_path: str) -> List[str]:
    """Return a Verdict-flavoured line list for an MLflow trace JSON."""
    path = Path(trace_path)
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    if not isinstance(payload, dict):
        return []

    # Accept either a single Trace object or an MLflow-run envelope
    # ``{"traces": [...]}``.
    traces: List[dict]
    if isinstance(payload.get("traces"), list):
        traces = [t for t in payload["traces"] if isinstance(t, dict)]
    elif payload.get("schema") == TRACE_FINGERPRINT or "data" in payload:
        traces = [payload]
    else:
        return []

    out: List[str] = []
    for trace in traces:
        raw_info = trace.get("info")
        info: dict = raw_info if isinstance(raw_info, dict) else {}
        if info:
            request_id = info.get("request_id") or info.get("trace_id")
            if request_id:
                out.append(f"[trace_start] {request_id}")
        for event in _iter_events(trace):
            line = _event_to_line(event)
            if line:
                out.append(line)
        if info.get("status"):
            out.append(f"[trace_end] status={info['status']}")
    return out


def looks_like_mlflow_trace(path: str, scan_bytes: int = 2048) -> bool:
    """Heuristic autoloader: does *path* head contain ``mlflow.entities.Trace``?"""
    target = Path(path)
    if not target.is_file():
        return False
    try:
        with target.open("rb") as handle:
            head = handle.read(scan_bytes).decode("utf-8", errors="replace")
    except OSError:
        return False
    return TRACE_FINGERPRINT in head
