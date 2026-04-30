#!/usr/bin/env python3
"""EU AI Act audit-trail CSV exporter.

Pure stdlib helper that converts a Verdict scorecard + transcript
pair into a deliberately-neutral CSV suitable for a DPO's auditor
dump:

    timestamp, agent_id, decision, reason, source_url,
    retention_window, human_in_loop

Each row corresponds to one consequential decision turn extracted
from the transcript. The exporter does NOT determine compliance —
it bundles evidence into a regulator-neutral shape.

> ⚠️ NOT LEGAL ADVICE. Output is not a substitute for counsel
> review or a regulatory attestation. See the rubric markdown for
> the full disclaimer.

Usage::

    python3 skills/judge/scripts/eu_audit_export.py \\
        --scorecard skills/judge/scores/eu-audit_TIMESTAMP.json \\
        --transcript path/to/transcript.jsonl \\
        --out audit-rows.csv

Stdlib-only.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Reuse the same evidence-marker regexes as score.py — but redefined
# here so this script remains importable on its own without dragging
# in score.py's module-level state.
_REASON_RE = re.compile(r"\[reason:\s*([^\]]+)\]", re.IGNORECASE)
_SOURCE_RE = re.compile(
    r"\[source:\s*(https?://[^\s\]]+)(?:\s+retrieved-at:\s*\d{4}-\d{2}-\d{2})?\]",
    re.IGNORECASE,
)
_AGENT_RE = re.compile(r"\[agent:\s*([A-Za-z0-9_.-]+)\]", re.IGNORECASE)
_RETENTION_RE = re.compile(
    r"\[retention:\s*(\d+)\s*d\+?\]", re.IGNORECASE,
)
_HUMAN_IN_LOOP_RE = re.compile(
    r"\[human-in-loop\b[^\]]*\]", re.IGNORECASE,
)
_DECISION_VERBS = re.compile(
    r"\b(approving|approved|denying|denied|recommending|recommended|"
    r"flagging|flagged|escalating|escalated|deciding|decided)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL file into a list of records (skip blanks/non-JSON)."""
    if not path.is_file():
        raise FileNotFoundError(f"file not found: {path}")
    out: List[Dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def extract_audit_rows(
    transcript_lines: List[str],
    scorecard: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Walk the transcript and emit one audit row per decision turn.

    A "decision turn" is any line that either:
    - carries a `[reason: ...]` marker, OR
    - matches a decision-verb regex (approve / deny / flag / etc).

    Each row is keyed by the canonical seven-column schema so a
    DPO can ingest it into a spreadsheet without re-shaping.
    """
    out: List[Dict[str, str]] = []
    # Resolve transcript-level retention + agent up-front; per-row
    # markers can override.
    retention_default = ""
    agent_default = ""
    for line in transcript_lines:
        if not retention_default:
            match = _RETENTION_RE.search(line)
            if match:
                retention_default = f"{match.group(1)}d"
        if not agent_default:
            match = _AGENT_RE.search(line)
            if match:
                agent_default = match.group(1)
        if retention_default and agent_default:
            break
    timestamp = ""
    if scorecard:
        ts = scorecard.get("timestamp")
        if isinstance(ts, str):
            timestamp = ts
    for idx, line in enumerate(transcript_lines):
        reason = _REASON_RE.search(line)
        decision_match = _DECISION_VERBS.search(line)
        if not reason and not decision_match:
            continue
        source = _SOURCE_RE.search(line)
        agent = _AGENT_RE.search(line)
        # Look at the next 2 lines for a paired human-in-loop turn.
        window_end = min(len(transcript_lines), idx + 3)
        human_in_loop = any(
            _HUMAN_IN_LOOP_RE.search(transcript_lines[j])
            for j in range(idx, window_end)
        )
        decision_text = decision_match.group(0) if decision_match else (
            reason.group(0)[:60] if reason else line[:60]
        )
        out.append({
            "timestamp": timestamp,
            "agent_id": agent.group(1) if agent else agent_default,
            "decision": decision_text.strip(),
            "reason": reason.group(1).strip() if reason else "",
            "source_url": source.group(1) if source else "",
            "retention_window": retention_default,
            "human_in_loop": "true" if human_in_loop else "false",
        })
    return out


def write_audit_csv(rows: List[Dict[str, str]], out_path: Path) -> int:
    """Write the audit rows to *out_path* as CSV. Returns row count."""
    fieldnames = [
        "timestamp",
        "agent_id",
        "decision",
        "reason",
        "source_url",
        "retention_window",
        "human_in_loop",
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return len(rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="eu_audit_export",
        description=(
            "Export EU AI Act Articles 19/26 audit rows from a Verdict "
            "scorecard + transcript pair to CSV. NOT LEGAL ADVICE."
        ),
    )
    parser.add_argument(
        "--scorecard",
        required=False,
        help="Optional Verdict scorecard JSON (used for the timestamp column).",
    )
    parser.add_argument(
        "--transcript",
        required=True,
        help="Path to the JSONL transcript to mine for audit rows.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output CSV path.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    transcript_path = Path(args.transcript)
    if not transcript_path.is_file():
        print(f"eu_audit_export: transcript not found: {transcript_path}", file=sys.stderr)
        return 2
    records = _load_jsonl(transcript_path)
    transcript_lines = [
        r.get("content", "")
        if isinstance(r.get("content"), str)
        else json.dumps(r)
        for r in records
    ]
    scorecard: Optional[Dict[str, Any]] = None
    if args.scorecard:
        sp = Path(args.scorecard)
        if not sp.is_file():
            print(f"eu_audit_export: scorecard not found: {sp}", file=sys.stderr)
            return 2
        try:
            scorecard = json.loads(sp.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"eu_audit_export: bad scorecard JSON: {exc}", file=sys.stderr)
            return 2
    rows = extract_audit_rows(transcript_lines, scorecard)
    n = write_audit_csv(rows, Path(args.out))
    print(
        f"eu_audit_export: wrote {n} audit rows to {args.out}. "
        "NOT LEGAL ADVICE — review with counsel before any regulatory use."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
