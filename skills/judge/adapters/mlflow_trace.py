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
         {"name": "run",
          "attributes": {
            "gen_ai.request.model": "claude-opus-4-7",
            "gen_ai.usage.input_tokens": 120,
            "gen_ai.usage.output_tokens": 60,
            "gen_ai.response.finish_reasons": ["stop"]
          },
          "events": [
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

OpenTelemetry GenAI semconv (v1.3.0+, MLflow 3.11.1+)
-----------------------------------------------------
When a span carries OpenTelemetry GenAI semantic-convention
attributes, the adapter emits pseudo-turn lines for the model name,
token usage, and finish reason so downstream analyzers — especially
the model-aware efficiency threshold added in Verdict v1.1.0 — can
read them from the flattened line stream. The enrichment is
best-effort: spans without OTel attributes flow through unchanged.
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

# OpenTelemetry GenAI semconv attribute keys. Kept as constants so the
# adapter can be updated in lock-step when the otel-gen-ai spec evolves.
OTEL_GENAI_MODEL_KEY:           str = "gen_ai.request.model"
OTEL_GENAI_INPUT_TOKENS_KEY:    str = "gen_ai.usage.input_tokens"
OTEL_GENAI_OUTPUT_TOKENS_KEY:   str = "gen_ai.usage.output_tokens"
OTEL_GENAI_FINISH_REASONS_KEY:  str = "gen_ai.response.finish_reasons"


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


def _extract_otel_genai_attrs(span: Any) -> dict:
    """Return a dict of OpenTelemetry GenAI semconv attributes on *span*.

    Keys present in the returned dict:

    - ``model`` — string, from ``gen_ai.request.model`` (also accepts
      ``gen_ai.response.model`` as a fallback; OTel v1.3.0 uses the
      request key, some older exporters populated only the response
      key).
    - ``input_tokens`` — int, from ``gen_ai.usage.input_tokens``.
    - ``output_tokens`` — int, from ``gen_ai.usage.output_tokens``.
    - ``finish_reasons`` — list of strings, from
      ``gen_ai.response.finish_reasons``. Always a list, even when the
      span reports a single reason as a string.

    Missing / malformed attributes are silently dropped. The adapter's
    caller should treat an empty return as "no enrichment available"
    rather than "span is malformed".
    """
    if not isinstance(span, dict):
        return {}
    raw_attrs = span.get("attributes")
    if not isinstance(raw_attrs, dict):
        return {}
    out: dict = {}
    model = raw_attrs.get(OTEL_GENAI_MODEL_KEY)
    if not isinstance(model, str) or not model:
        model = raw_attrs.get("gen_ai.response.model")
    if isinstance(model, str) and model:
        out["model"] = model
    for key, out_key in (
        (OTEL_GENAI_INPUT_TOKENS_KEY, "input_tokens"),
        (OTEL_GENAI_OUTPUT_TOKENS_KEY, "output_tokens"),
    ):
        value = raw_attrs.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            out[out_key] = value
        elif isinstance(value, float) and value.is_integer():
            out[out_key] = int(value)
    reasons = raw_attrs.get(OTEL_GENAI_FINISH_REASONS_KEY)
    if isinstance(reasons, str) and reasons:
        out["finish_reasons"] = [reasons]
    elif isinstance(reasons, list):
        cleaned = [r for r in reasons if isinstance(r, str) and r]
        if cleaned:
            out["finish_reasons"] = cleaned
    return out


def _otel_genai_lines(span: Any) -> Iterable[str]:
    """Emit Verdict-flavoured pseudo-turns from a span's OTel GenAI attrs."""
    attrs = _extract_otel_genai_attrs(span)
    if not attrs:
        return
    model = attrs.get("model")
    if model:
        # The literal ``"model":"<id>"`` form is what
        # ``score.detect_model_from_transcript`` fingerprints on, so
        # embed it in JSON-ish shape on the line. This unlocks the
        # model-aware efficiency thresholds introduced in v1.1.0.
        yield f'[model] "model":"{model}"'
    input_tokens = attrs.get("input_tokens")
    output_tokens = attrs.get("output_tokens")
    if input_tokens is not None or output_tokens is not None:
        pieces: List[str] = []
        if input_tokens is not None:
            pieces.append(f"input_tokens={input_tokens}")
        if output_tokens is not None:
            pieces.append(f"output_tokens={output_tokens}")
        yield f"[usage] {' '.join(pieces)}"
    for reason in attrs.get("finish_reasons", []):
        yield f"[finish_reason] {reason}"


def _iter_spans(trace: dict) -> Iterable[Any]:
    """Yield the spans in a trace, preserving order."""
    data = trace.get("data")
    if not isinstance(data, dict):
        return
    spans = data.get("spans")
    if not isinstance(spans, list):
        return
    for span in spans:
        if isinstance(span, dict):
            yield span


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
        # OTel GenAI semconv enrichment: emit a pseudo-turn per span
        # that carries ``gen_ai.*`` attributes. Traversal order matches
        # _iter_events so per-span context lands just before the span's
        # own events.
        for span in _iter_spans(trace):
            for line in _otel_genai_lines(span):
                out.append(line)
            for event in span.get("events", []) or []:
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


def detection_score(path: str, scan_bytes: int = 2048) -> float:
    """Confidence score for the dispatch registry (0.0–1.0).

    The ``mlflow.entities.Trace`` schema literal is highly specific
    and earns the top tier (0.95). The OTel ``data.spans[]`` shape
    alone scores lower (0.60) because it can co-occur with Inspect AI
    logs that also carry ``gen_ai.*`` attributes — that collision
    motivated Issue #11. When both shapes appear, the schema literal
    wins.
    """
    target = Path(path)
    if not target.is_file():
        return 0.0
    try:
        with target.open("rb") as handle:
            head = handle.read(scan_bytes).decode("utf-8", errors="replace")
    except OSError:
        return 0.0
    if TRACE_FINGERPRINT in head:
        return 0.95
    has_spans = '"data"' in head and '"spans"' in head
    has_otel = "gen_ai." in head
    if has_spans and has_otel:
        return 0.60
    return 0.0
