#!/usr/bin/env python3
"""verdict audit-export — DPO-ready CSV bundler for EU AI Act dossiers.

Bundles a fleet of Verdict scorecards into a regulator-handover zip:

- ``manifest.csv`` — one row per scorecard with Article 19/26 binary
  flags pulled from ``adjustments.eu_ai_act_audit``.
- ``scorecards/<name>.json`` — raw evidence (verbatim copies).
- ``transcripts-redacted/<name>.jsonl`` — best-effort PII-redacted
  transcript copies.
- ``methodology.md`` — short note on which evidence signals map to
  which Article.

> ⚠️ **NOT LEGAL ADVICE.** The output of this CLI is **not** a
> compliance attestation and is **not** a substitute for counsel
> review. Issue O13 — counsel review pending.

> ⚠️ **PII redaction is best-effort regex.** It is **NOT**
> sufficient for high-risk health / financial PII. Per Issue O16,
> this CLI **refuses** to bundle transcripts whose rubric is
> ``clinical-agentic-workflow`` until a hardened redactor lands
> in v1.4.3.

Usage::

    python3 skills/judge/scripts/audit_export.py \\
        --scores-dir skills/judge/scores \\
        --since 2025-11-01 \\
        --until 2026-04-29 \\
        --rubric eu-ai-act-audit-trail \\
        --out audit-bundle-2026-04-29.zip

Stdlib-only.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REFUSAL_RUBRICS = frozenset({"clinical-agentic-workflow"})  # O16

# Regex pass for best-effort PII redaction. NOT sufficient for
# high-risk PII. See Issue O16.
_PII_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Order matters: highly-specific patterns (API keys, AWS keys) run
    # first so they don't get partially eaten by the broader phone /
    # SSN regexes (e.g. "sk-1234567890..." has a digit run that
    # otherwise looks like a phone fragment).
    (re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"), "<API_KEY>"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "<AWS_KEY>"),
    (re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"), "<GH_TOKEN>"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "<EMAIL>"),
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "<SSN>"),
    (re.compile(r"\+?\d{1,3}[-.\s]?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{4}"), "<PHONE>"),
]


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _parse_iso_date(s: str) -> datetime:
    """Parse YYYY-MM-DD into a timezone-aware UTC datetime at midnight."""
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _scorecard_in_window(
    scorecard: Dict[str, Any],
    since: Optional[datetime],
    until: Optional[datetime],
) -> bool:
    ts = scorecard.get("timestamp")
    if not isinstance(ts, str):
        return True  # be permissive on missing timestamp
    try:
        dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc,
        )
    except ValueError:
        return True
    if since and dt < since:
        return False
    if until and dt > until:
        return False
    return True


def collect_scorecards(
    scores_dir: Path,
    rubric: Optional[str],
    since: Optional[datetime],
    until: Optional[datetime],
) -> List[Tuple[Path, Dict[str, Any]]]:
    """Walk the scores directory and return matching scorecard files."""
    out: List[Tuple[Path, Dict[str, Any]]] = []
    if not scores_dir.is_dir():
        return out
    for path in sorted(scores_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(data, dict):
            continue
        if rubric and data.get("rubric_used") != rubric:
            continue
        if not _scorecard_in_window(data, since, until):
            continue
        out.append((path, data))
    return out


def manifest_row(scorecard: Dict[str, Any]) -> Dict[str, str]:
    """Build a manifest row from a scorecard's eu_ai_act_audit block."""
    audit = (scorecard.get("adjustments") or {}).get("eu_ai_act_audit") or {}
    return {
        "scorecard_name": scorecard.get("skill", "") + "_"
            + (scorecard.get("timestamp", "")).replace(":", "-"),
        "skill": scorecard.get("skill", ""),
        "timestamp": scorecard.get("timestamp", ""),
        "composite_score": str(scorecard.get("composite_score", "")),
        "rubric_used": scorecard.get("rubric_used", ""),
        "log_retention_attestation": str(audit.get("log_retention_attestation", False)).lower(),
        "decision_logic_grounding": str(audit.get("decision_logic_grounding", False)).lower(),
        "human_intervention_points": str(audit.get("human_intervention_points", False)).lower(),
        "data_source_provenance": str(audit.get("data_source_provenance", False)).lower(),
        "tool_use_attribution": str(audit.get("tool_use_attribution", False)).lower(),
        "no_shadow_decisioning": str(audit.get("no_shadow_decisioning", False)).lower(),
        "refusal_on_out_of_scope_data": str(audit.get("refusal_on_out_of_scope_data", False)).lower(),
        "audit_trail_complete": str(audit.get("audit_trail_complete", False)).lower(),
        "retention_days_declared": str(audit.get("retention_days_declared", 0)),
    }


def redact_transcript_line(line: str) -> str:
    """Apply the best-effort PII redaction pass."""
    out = line
    for pattern, replacement in _PII_PATTERNS:
        out = pattern.sub(replacement, out)
    return out


def methodology_text() -> str:
    return (
        "# Methodology\n\n"
        "**NOT LEGAL ADVICE — NOT COUNSEL-REVIEWED.** This bundle is\n"
        "evidence packaging, not a compliance attestation. Issue O13.\n\n"
        "## Signal-to-Article mapping\n\n"
        "| Verdict signal                       | EU AI Act Article |\n"
        "| ------------------------------------ | ----------------- |\n"
        "| log_retention_attestation            | Article 19, 26    |\n"
        "| decision_logic_grounding             | Article 26(11)    |\n"
        "| human_intervention_points            | Article 26(2)     |\n"
        "| data_source_provenance               | Article 26(7)     |\n"
        "| tool_use_attribution                 | Article 12        |\n"
        "| no_shadow_decisioning                | Article 26(7)     |\n"
        "| refusal_on_out_of_scope_data         | Article 26(2)     |\n\n"
        "## PII redaction caveat\n\n"
        "Transcripts under `transcripts-redacted/` carry a best-effort\n"
        "regex-based redaction pass (emails, phone numbers, SSN-shapes,\n"
        "API keys, AWS keys, GitHub tokens). This is **NOT** sufficient\n"
        "for high-risk health or financial PII. Issue O16. Bundling\n"
        "transcripts whose rubric is `clinical-agentic-workflow` is\n"
        "refused by the CLI; a hardened redactor is queued for v1.4.3.\n\n"
        "## Sources\n\n"
        "- https://artificialintelligenceact.eu/article/19/\n"
        "- https://artificialintelligenceact.eu/article/26/\n"
        "- https://www.helpnetsecurity.com/2026/04/16/eu-ai-act-logging-requirements/\n"
    )


def build_bundle(
    scorecards: List[Tuple[Path, Dict[str, Any]]],
    out_zip: Path,
    transcripts_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Assemble the audit bundle zip from a list of scorecards.

    Returns ``{"scorecard_count", "rows_written", "refused_rubrics"}``.
    """
    refused: List[str] = []
    rows: List[Dict[str, str]] = []
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("methodology.md", methodology_text())
        for path, sc in scorecards:
            rubric = sc.get("rubric_used", "")
            if rubric in REFUSAL_RUBRICS:
                refused.append(rubric)
                continue
            row = manifest_row(sc)
            rows.append(row)
            zf.writestr(f"scorecards/{path.name}", path.read_text(encoding="utf-8"))
            # Best-effort transcript redaction.
            transcript_relpath = sc.get("transcript_path") or sc.get("transcript")
            if transcript_relpath and transcripts_root:
                tx_path = transcripts_root / transcript_relpath
                if tx_path.is_file():
                    redacted_lines = [
                        redact_transcript_line(line)
                        for line in tx_path.read_text(encoding="utf-8").splitlines()
                    ]
                    zf.writestr(
                        f"transcripts-redacted/{tx_path.name}",
                        "\n".join(redacted_lines) + "\n",
                    )
        # manifest.csv last so it sees the final row count.
        if rows:
            csv_buf = io.StringIO()
            writer = csv.DictWriter(csv_buf, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
            zf.writestr("manifest.csv", csv_buf.getvalue())
        else:
            zf.writestr(
                "manifest.csv",
                "scorecard_name,skill,timestamp,composite_score,rubric_used\n",
            )
    return {
        "scorecard_count": len(scorecards),
        "rows_written": len(rows),
        "refused_rubrics": refused,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="audit_export",
        description=(
            "Bundle Verdict scorecards into a DPO-ready audit zip. "
            "NOT LEGAL ADVICE."
        ),
    )
    parser.add_argument("--scores-dir", required=True, help="Directory of scorecard JSONs.")
    parser.add_argument("--since", default=None, help="ISO date YYYY-MM-DD (inclusive).")
    parser.add_argument("--until", default=None, help="ISO date YYYY-MM-DD (inclusive).")
    parser.add_argument("--rubric", default=None, help="Filter to one rubric_used value.")
    parser.add_argument("--out", required=True, help="Output zip path.")
    parser.add_argument(
        "--transcripts-root", default=None,
        help="Optional root for transcript paths in scorecards (best-effort PII redaction).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    scores_dir = Path(args.scores_dir)
    if not scores_dir.is_dir():
        print(f"audit_export: scores dir not found: {scores_dir}", file=sys.stderr)
        return 2
    since = _parse_iso_date(args.since) if args.since else None
    until = _parse_iso_date(args.until) if args.until else None
    cards = collect_scorecards(scores_dir, args.rubric, since, until)
    transcripts_root = Path(args.transcripts_root) if args.transcripts_root else None
    out_zip = Path(args.out)
    summary = build_bundle(cards, out_zip, transcripts_root)
    print(
        f"audit_export: bundled {summary['rows_written']} scorecard(s) into {out_zip}. "
        f"Refused (O16): {len(summary['refused_rubrics'])}. "
        "NOT LEGAL ADVICE — review with counsel."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
