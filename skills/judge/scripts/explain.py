#!/usr/bin/env python3
"""Verdict scorecard rationale exporter.

Reads an existing scorecard JSON written by ``score.py`` and renders a
PR-comment-friendly Markdown explanation OR a stable-schema JSON
dump. Designed for two consumers:

- humans pasting the output into a pull-request review comment
  (``--format md``, the default)
- CI scripts that need a stable, machine-readable digest of a
  scorecard (``--format json``)

The Markdown format prioritises clarity over completeness — it pulls
the per-dimension table, the adjustments block, the LLM second-opinion
overlay (when present), critical issues, and recommendations into a
shape that lands cleanly inside a GitHub PR comment.

The JSON format is versioned by ``format_version: "explain.v1"`` so
future schema bumps can be detected by consumers.

Stdlib-only. No third-party deps.

Usage:

    python3 skills/judge/scripts/explain.py \\
        --scorecard skills/judge/scores/code-review_2026-04-25.json \\
        [--format md|json] [--out PATH]

Writes to stdout when ``--out`` is omitted.

Source signal: GitHub Discussions #43 — top adopter ask "explain my
scorecard" (https://github.com/sattyamjjain/verdict/discussions/43).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

EXPLAIN_FORMAT_VERSION: str = "explain.v1"

# Canonical dimension order — matches DIMENSIONS in score.py and
# llm_judge.py so the output is stable across all three.
DIMENSIONS: List[str] = [
    "correctness", "completeness", "adherence", "actionability",
    "efficiency", "safety", "consistency",
]


def load_scorecard(path: Path) -> Dict[str, Any]:
    """Load a scorecard JSON file. Raises ``ValueError`` on failure."""
    if not path.is_file():
        raise ValueError(f"scorecard not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read scorecard {path}: {exc}")


def _ordered_dimension_entries(card: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return per-dimension entries in canonical order with the name attached."""
    raw = card.get("dimensions", {}) if isinstance(card, dict) else {}
    if not isinstance(raw, dict):
        return []
    out: List[Dict[str, Any]] = []
    for name in DIMENSIONS:
        entry = raw.get(name)
        if isinstance(entry, dict):
            attached = {"name": name, **entry}
            out.append(attached)
    # Append any extra dims the rubric carries (custom rubrics may
    # extend the canonical seven — preserve order of appearance).
    for name, entry in raw.items():
        if name in DIMENSIONS or not isinstance(entry, dict):
            continue
        out.append({"name": name, **entry})
    return out


def _evidence_block(card: Dict[str, Any]) -> Dict[str, Any]:
    """Compute proxy evidence stats from scorecard fields.

    True evidence spans (the transcript lines that drove each score)
    aren't recorded by the heuristic scorer today; the scorecard only
    persists per-dimension justification strings. ``explain`` surfaces
    what is recorded — counts and matched-pattern names — so PR
    reviewers see the volume of signal behind the score.
    """
    return {
        "transcript_lines": card.get("transcript_lines"),
        "red_flag_count": len(card.get("red_flags", []) or []),
        "bonus_count": len(card.get("bonuses", []) or []),
    }


def render_json(card: Dict[str, Any]) -> str:
    """Render the scorecard as a stable-schema explain.v1 JSON document."""
    dims_out: List[Dict[str, Any]] = []
    for entry in _ordered_dimension_entries(card):
        out_entry: Dict[str, Any] = {
            "name": entry["name"],
            "score": entry.get("score"),
            "weight": entry.get("weight"),
            "weighted": entry.get("weighted"),
            "justification": entry.get("justification", ""),
        }
        if "llm_score" in entry:
            out_entry["llm_score"] = entry["llm_score"]
        if "llm_justification" in entry:
            out_entry["llm_justification"] = entry["llm_justification"]
        dims_out.append(out_entry)

    adjustments_in = card.get("adjustments", {}) or {}
    adjustments_out: Dict[str, Any] = {
        "deduction": adjustments_in.get("deduction", 0.0),
        "bonus": adjustments_in.get("bonus", 0.0),
        "red_flags": list(card.get("red_flags", []) or []),
        "bonuses": list(card.get("bonuses", []) or []),
    }
    # Contamination only appears for rubrics that activated the
    # SWE-bench Pro scanner; surface it when set.
    contamination = adjustments_in.get("contamination")
    if contamination is not None:
        adjustments_out["contamination"] = contamination

    payload: Dict[str, Any] = {
        "format_version": EXPLAIN_FORMAT_VERSION,
        "skill": card.get("skill"),
        "timestamp": card.get("timestamp"),
        "rubric": card.get("rubric_used"),
        "model": card.get("model"),
        "tokenizer_baseline": card.get("tokenizer_baseline"),
        "composite": card.get("composite_score"),
        "raw_composite": card.get("raw_composite"),
        "grade": card.get("grade"),
        "grade_label": card.get("grade_label"),
        "summary": card.get("summary", ""),
        "one_liner": card.get("one_liner", ""),
        "dimensions": dims_out,
        "adjustments": adjustments_out,
        "critical_issues": list(card.get("critical_issues", []) or []),
        "recommendations": list(card.get("recommendations", []) or []),
        "evidence": _evidence_block(card),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _md_dimension_table(entries: List[Dict[str, Any]]) -> str:
    rows = ["| Dimension | Score | Weight | Weighted | Justification |",
            "|-----------|-------|--------|----------|---------------|"]
    for entry in entries:
        score = entry.get("score", "?")
        weight = entry.get("weight", "?")
        weighted = entry.get("weighted", "?")
        justification = (entry.get("justification") or "").replace("|", "\\|").strip()
        if len(justification) > 140:
            justification = justification[:137] + "..."
        rows.append(
            f"| {entry['name']} | {score}/10 | {weight} | {weighted} | "
            f"{justification or '—'} |"
        )
    return "\n".join(rows)


def _md_llm_overlay(entries: List[Dict[str, Any]]) -> str:
    has_llm = any("llm_score" in e for e in entries)
    if not has_llm:
        return ""
    bullets: List[str] = []
    for entry in entries:
        if "llm_score" not in entry:
            continue
        justification = (entry.get("llm_justification") or "").strip()
        bullets.append(
            f"- **{entry['name']}**: {entry['llm_score']}/10 — "
            f"{justification or '_(no justification recorded)_'}"
        )
    return "### LLM second opinion\n\n" + "\n".join(bullets)


def render_markdown(card: Dict[str, Any]) -> str:
    """Render a PR-comment-friendly Markdown explanation."""
    skill = card.get("skill", "?")
    grade = card.get("grade", "?")
    grade_label = card.get("grade_label", "")
    composite = card.get("composite_score", "?")
    rubric = card.get("rubric_used", "?")
    model = card.get("model") or "_unknown_"
    timestamp = card.get("timestamp", "?")
    summary = card.get("summary", "").strip()

    header = (
        f"# Verdict Scorecard — `{skill}`\n\n"
        f"**Composite:** {composite}/10 — **Grade:** {grade}"
        f"{(' (' + grade_label + ')') if grade_label else ''}  \n"
        f"**Rubric:** `{rubric}` · **Model:** `{model}` · "
        f"**Timestamp:** `{timestamp}`"
    )
    one_liner = card.get("one_liner")
    if one_liner:
        header += f"\n\n> {one_liner.strip()}"
    if summary:
        header += f"\n\n_{summary}_"

    entries = _ordered_dimension_entries(card)
    sections: List[str] = [header, "## Per-dimension breakdown",
                           _md_dimension_table(entries)]

    overlay = _md_llm_overlay(entries)
    if overlay:
        sections.append(overlay)

    adjustments = card.get("adjustments", {}) or {}
    red_flags = list(card.get("red_flags", []) or [])
    bonuses = list(card.get("bonuses", []) or [])
    contamination = adjustments.get("contamination", 0.0) or 0.0
    if red_flags or bonuses or contamination:
        adj_lines: List[str] = ["## Adjustments", ""]
        if red_flags:
            adj_lines.append(
                f"- **Red flags** (−{adjustments.get('deduction', 0.0)}): "
                f"{', '.join(red_flags)}"
            )
        if bonuses:
            adj_lines.append(
                f"- **Bonuses** (+{adjustments.get('bonus', 0.0)}): "
                f"{', '.join(bonuses)}"
            )
        if contamination:
            adj_lines.append(
                f"- **Contamination penalty** (−{contamination}): "
                "transcript referenced SWE-bench Verified literals"
            )
        sections.append("\n".join(adj_lines))

    critical = list(card.get("critical_issues", []) or [])
    if critical:
        sections.append(
            "## Critical issues\n\n" + "\n".join(f"- {c}" for c in critical)
        )

    recs = list(card.get("recommendations", []) or [])
    if recs:
        sections.append(
            "## Recommendations\n\n" + "\n".join(f"- {r}" for r in recs)
        )

    evidence = _evidence_block(card)
    sections.append(
        "## Evidence\n\n"
        f"- {evidence['transcript_lines']} transcript lines analysed\n"
        f"- {evidence['red_flag_count']} red-flag patterns matched\n"
        f"- {evidence['bonus_count']} bonus signals matched"
    )

    return "\n\n".join(sections) + "\n"


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="verdict-explain",
        description="Render a Verdict scorecard JSON as Markdown or JSON.",
    )
    parser.add_argument(
        "--scorecard", required=True,
        help="Path to a scorecard JSON file written by score.py.",
    )
    parser.add_argument(
        "--format", choices=("md", "json"), default="md",
        help="Output format. Default: md (PR-comment-friendly).",
    )
    parser.add_argument(
        "--out",
        help="Write output to PATH. Default: stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        card = load_scorecard(Path(args.scorecard))
    except ValueError as exc:
        print(f"verdict-explain: {exc}", file=sys.stderr)
        return 2
    rendered = render_markdown(card) if args.format == "md" else render_json(card)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
        if not rendered.endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
