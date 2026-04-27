"""Browser Harness trajectory adapter (read-only).

Browser-agent execution surfaces (browser-use's ``browser-harness``,
similar tooling) record a session as a sequence of:

- DOM events (clicks, form fills, key presses)
- Navigation transitions (URL → URL with HTTP status)
- Screenshot captures (referenced by manifest path)
- Assertions (test-style "is element X visible / does it contain Y")

The shape varies between harnesses; this adapter targets a
HAR-flavoured JSON envelope that's common to most:

.. code-block:: json

   {
     "log": {"version": "1.2", "creator": {"name": "browser-harness"}},
     "session": {
       "agent_model": "claude-sonnet-4-6",
       "task": "buy a domain on a registrar",
       "events": [
         {"type": "navigate", "url": "...", "status": 200},
         {"type": "click", "selector": "...", "screenshot": "shots/01.png"},
         {"type": "fill", "selector": "...", "value": "..."},
         {"type": "assertion", "selector": "...", "expected": "..."}
       ]
     }
   }

Verdict flattens the events into prefix-tagged turns:

- ``[navigate] <method> <url> -> <status>``
- ``[click] <selector>``
- ``[fill] <selector>=<value>``
- ``[keypress] <key>``
- ``[assertion] <selector> :: <expected>``
- ``[screenshot] <path>``

Stdlib only. Missing fields degrade to fewer lines rather than
raising. Source signal: `github.com/browser-use/browser-harness
<https://github.com/browser-use/browser-harness>`_.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List

FINGERPRINT_TOKENS = (
    '"browser-harness"',
    '"browser_harness"',
    '"creator":{"name":"browser-harness"}',
    '"har_version"',
)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _redact_credential_value(selector: str, value: str) -> str:
    """Replace likely credential values with a redaction marker.

    Browser-agent traces routinely fill password / api-key fields;
    leaking those into the scorecard is exactly the kind of mistake
    the rubric is supposed to catch. We redact at extraction time so
    the rubric scores the *behaviour*, not the literal credential.
    """
    lowered = (selector or "").lower()
    if any(tok in lowered for tok in (
        "password", "secret", "api_key", "apikey", "token", "credential",
        "card_number", "cardnumber", "cvv",
    )):
        return "[REDACTED]"
    return value


def _event_to_line(event: Any) -> str:
    if not isinstance(event, dict):
        return ""
    etype = str(event.get("type", "")).lower()
    if etype == "navigate":
        method = event.get("method", "GET")
        url = _stringify(event.get("url"))
        status = event.get("status")
        suffix = f" -> {status}" if status is not None else ""
        return f"[navigate] {method} {url}{suffix}"
    if etype == "click":
        return f"[click] {_stringify(event.get('selector'))}"
    if etype == "fill":
        sel = _stringify(event.get("selector"))
        val = _redact_credential_value(sel, _stringify(event.get("value")))
        return f"[fill] {sel}={val}"
    if etype in ("keypress", "key"):
        return f"[keypress] {_stringify(event.get('key'))}"
    if etype == "assertion":
        sel = _stringify(event.get("selector"))
        expected = _stringify(event.get("expected"))
        return f"[assertion] {sel} :: {expected}"
    if etype == "screenshot":
        return f"[screenshot] {_stringify(event.get('path') or event.get('href'))}"
    if etype == "popup":
        return f"[popup] {_stringify(event.get('action'))} url={_stringify(event.get('url'))}"
    if etype == "console_error":
        return f"[console_error] {_stringify(event.get('message'))}"
    # Unknown event shapes flow through with the raw type prefix so
    # downstream rubrics can still grep them.
    return f"[{etype or 'event'}] {_stringify(event)}"


def _iter_events(payload: Any) -> Iterable[Any]:
    if not isinstance(payload, dict):
        return
    session = payload.get("session")
    if isinstance(session, dict):
        events = session.get("events")
        if isinstance(events, list):
            yield from events
            return
    log = payload.get("log")
    if isinstance(log, dict):
        # HAR-shaped exports nest entries under log.entries; we treat
        # each entry as a navigate + (optionally) a request body fill.
        entries = log.get("entries")
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, dict) and isinstance(entry.get("request"), dict):
                    yield {
                        "type": "navigate",
                        "method": entry["request"].get("method", "GET"),
                        "url": entry["request"].get("url"),
                        "status": (entry.get("response") or {}).get("status"),
                    }


def detect(head: bytes) -> bool:
    """Fingerprint the first bytes of a Browser Harness trace."""
    if not head:
        return False
    try:
        text = head.decode("utf-8", errors="replace")
    except AttributeError:
        return False
    return any(token in text for token in FINGERPRINT_TOKENS)


def looks_like_browser_harness(path: str, scan_bytes: int = 2048) -> bool:
    """Heuristic autoloader: does *path* head look like a Browser Harness trace?"""
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
    """Confidence score for the dispatch registry (0.0–1.0)."""
    target = Path(path)
    if not target.is_file():
        return 0.0
    try:
        with target.open("rb") as handle:
            head = handle.read(scan_bytes).decode("utf-8", errors="replace")
    except OSError:
        return 0.0
    if '"browser-harness"' in head or '"browser_harness"' in head:
        return 0.85
    if '"har_version"' in head and '"entries"' in head:
        return 0.55
    return 0.0


def extract_lines(path: str) -> List[str]:
    """Flatten a Browser Harness JSON trace into Verdict-flavoured turns."""
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
    raw_session = payload.get("session")
    session: dict = raw_session if isinstance(raw_session, dict) else {}
    if session.get("agent_model"):
        out.append(f"[model] {_stringify(session['agent_model'])}")
    if session.get("task"):
        out.append(f"[task] {_stringify(session['task'])}")
    for event in _iter_events(payload):
        line = _event_to_line(event)
        if line:
            out.append(line)
    return out
