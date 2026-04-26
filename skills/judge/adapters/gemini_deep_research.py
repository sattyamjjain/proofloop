"""Gemini 3.1 Pro Deep Research adapter (read-only).

Deep Research / Deep Research Max sessions emit a multi-source-
synthesis transcript shape that the standard ``gemini_cli`` adapter
(parts[] + functionCall + content/text) discards. The Deep Research
shape adds three top-level blocks the synthesis run depends on:

- ``research_plan`` — the agent's pre-search plan, an ordered list of
  ``{step, query}`` entries.
- ``citations`` — every URL the agent retrieved, plus the section of
  the synthesis it grounds. Each entry carries a ``retrieved_at``
  timestamp so downstream rubrics can dock for stale sources.
- ``verifier_notes`` — the verifier sub-agent's per-claim audit notes.
- ``assistant_synthesis`` — the final synthesised answer (distinct
  from a normal assistant turn — it's the post-verification render).

This adapter flattens those blocks into prefix-tagged turns so the
heuristic scorer + rubrics that grade research quality (citation
grounding, verifier coverage) can read them in one pass.

Tag emission order:

- ``[plan_step] <step>: <query>``
- ``[citation:<url>] retrieved_at=<iso8601>`` for each citation
- ``[verifier_note] <text>``
- ``[assistant] <synthesis text>``

The adapter never imports ``google-generativeai``; ingestion stays
offline-first. Missing / malformed fields degrade to fewer lines
rather than raising.

Market signal: `blog.google — Deep Research Max (2026-04-22)
<https://blog.google/products/gemini/google-gemini-deep-research-max/>`_.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List

FINGERPRINT_TOKENS = (
    '"deep_research_mode": true',
    '"deep_research_mode":true',
    '"research_plan"',
    '"verifier_notes"',
    '"assistant_synthesis"',
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


def _plan_lines(payload: Any) -> Iterable[str]:
    plan = payload.get("research_plan") if isinstance(payload, dict) else None
    if not isinstance(plan, list):
        return
    for entry in plan:
        if isinstance(entry, dict):
            step = entry.get("step")
            query = entry.get("query") or entry.get("search") or ""
            if step is not None:
                yield f"[plan_step] {step}: {_stringify(query)}"
            else:
                yield f"[plan_step] {_stringify(query) or _stringify(entry)}"
        else:
            yield f"[plan_step] {_stringify(entry)}"


def _citation_lines(payload: Any) -> Iterable[str]:
    citations = payload.get("citations") if isinstance(payload, dict) else None
    if not isinstance(citations, list):
        return
    for entry in citations:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url") or entry.get("href")
        if not isinstance(url, str) or not url:
            continue
        retrieved = entry.get("retrieved_at") or entry.get("retrievedAt")
        suffix = f" retrieved_at={retrieved}" if isinstance(retrieved, str) and retrieved else ""
        # Optional grounded-section pointer — useful for rubrics that
        # check whether each synthesis claim has a backing citation.
        section = entry.get("section") or entry.get("anchors")
        if section:
            suffix += f" section={_stringify(section)}"
        yield f"[citation:{url}]{suffix}"


def _verifier_lines(payload: Any) -> Iterable[str]:
    notes = payload.get("verifier_notes") if isinstance(payload, dict) else None
    if not isinstance(notes, list):
        return
    for note in notes:
        if isinstance(note, dict):
            yield f"[verifier_note] {_stringify(note.get('text') or note)}"
        elif isinstance(note, str) and note:
            yield f"[verifier_note] {note}"


def _synthesis_lines(payload: Any) -> Iterable[str]:
    synthesis = payload.get("assistant_synthesis") if isinstance(payload, dict) else None
    if isinstance(synthesis, str) and synthesis:
        yield f"[assistant] {synthesis}"
    elif isinstance(synthesis, list):
        # Some Deep Research traces split synthesis into sectioned blocks.
        for block in synthesis:
            text = (
                block.get("text") if isinstance(block, dict) else None
            ) or (block if isinstance(block, str) else None)
            if isinstance(text, str) and text:
                yield f"[assistant] {text}"


def detect(head: bytes) -> bool:
    """Fingerprint the first bytes of a Gemini Deep Research session."""
    if not head:
        return False
    try:
        text = head.decode("utf-8", errors="replace")
    except AttributeError:
        return False
    return any(token in text for token in FINGERPRINT_TOKENS)


def looks_like_gemini_deep_research(path: str, scan_bytes: int = 4096) -> bool:
    """Heuristic autoloader: does *path* head look like Deep Research?"""
    target = Path(path)
    if not target.is_file():
        return False
    try:
        with target.open("rb") as handle:
            head = handle.read(scan_bytes)
    except OSError:
        return False
    return detect(head)


def detection_score(path: str, scan_bytes: int = 4096) -> float:
    """Confidence score for the dispatch registry (0.0–1.0).

    Returns 0.9 when the explicit ``deep_research_mode: true`` flag is
    present (unambiguous). Drops to 0.6 when only the structural
    markers (``research_plan`` / ``verifier_notes``) match — those
    can in principle co-occur with other shapes. The registry compares
    scores across adapters and picks the highest match.
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
    if '"deep_research_mode": true' in text or '"deep_research_mode":true' in text:
        return 0.9
    structural = sum(
        token in text for token in (
            '"research_plan"', '"verifier_notes"', '"assistant_synthesis"',
        )
    )
    if structural >= 2:
        return 0.7
    if structural == 1:
        return 0.5
    return 0.0


def extract_lines(path: str) -> List[str]:
    """Flatten a Gemini Deep Research session into Verdict-flavoured turns."""
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
    if payload.get("model"):
        out.append(f"[model] {_stringify(payload['model'])}")
    if payload.get("topic") or payload.get("query"):
        topic = payload.get("topic") or payload.get("query")
        out.append(f"[topic] {_stringify(topic)}")
    out.extend(_plan_lines(payload))
    out.extend(_citation_lines(payload))
    out.extend(_verifier_lines(payload))
    out.extend(_synthesis_lines(payload))
    return out
