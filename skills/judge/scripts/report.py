#!/usr/bin/env python3
"""SkillJudge Score Reporter.

Reads persisted score JSON files and produces visual scorecards with
Unicode bar charts, trend indicators, and historical averages.

Usage:
    python3 report.py --scores-dir SCORES_DIR [--skill SKILL_NAME] \
                      [--last N] [--format text|json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BAR_FULL = "\u2588"  # █
BAR_EMPTY = "\u2591"  # ░
BAR_WIDTH = 10

TREND_UP = "\u2191"      # ↑
TREND_DOWN = "\u2193"    # ↓
TREND_STABLE = "\u2192"  # →

DIMENSION_ORDER = [
    "correctness",
    "completeness",
    "adherence",
    "actionability",
    "efficiency",
    "safety",
    "consistency",
]

BOX_TL = "\u2554"  # ╔
BOX_TR = "\u2557"  # ╗
BOX_BL = "\u255a"  # ╚
BOX_BR = "\u255d"  # ╝
BOX_H = "\u2550"   # ═
BOX_V = "\u2551"   # ║
BOX_ML = "\u2560"  # ╠
BOX_MR = "\u2563"  # ╣

CARD_WIDTH = 78

# ---------------------------------------------------------------------------
# Score loading
# ---------------------------------------------------------------------------


def load_scores(
    scores_dir: str,
    skill_name: Optional[str] = None,
    last_n: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Load score JSON files from *scores_dir*.

    Optionally filter by *skill_name* and limit to *last_n* most recent.
    Returns a list of scorecards sorted by timestamp (oldest first).
    """
    scores_path = Path(scores_dir)
    if not scores_path.is_dir():
        print(f"Error: Scores directory not found: {scores_dir}", file=sys.stderr)
        sys.exit(1)

    records: List[Dict[str, Any]] = []
    for entry in scores_path.iterdir():
        if not entry.is_file() or not entry.name.endswith(".json"):
            continue
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        if skill_name and data.get("skill") != skill_name:
            continue
        records.append(data)

    # Sort by timestamp ascending
    records.sort(key=lambda d: d.get("timestamp", ""))

    if last_n is not None and last_n > 0:
        records = records[-last_n:]

    return records


# ---------------------------------------------------------------------------
# Trend computation
# ---------------------------------------------------------------------------


def _compute_trend(values: List[float]) -> str:
    """Return a trend indicator based on the last few values."""
    if len(values) < 2:
        return TREND_STABLE
    recent = values[-3:]  # Look at last 3 data points
    if len(recent) < 2:
        return TREND_STABLE
    delta = recent[-1] - recent[0]
    if delta > 0.5:
        return TREND_UP
    elif delta < -0.5:
        return TREND_DOWN
    return TREND_STABLE


# ---------------------------------------------------------------------------
# Bar chart rendering
# ---------------------------------------------------------------------------


def _render_bar(score: float, width: int = BAR_WIDTH) -> str:
    """Render a Unicode bar for a 0-10 score."""
    filled = round(score / 10 * width)
    filled = max(0, min(width, filled))
    return BAR_FULL * filled + BAR_EMPTY * (width - filled)


# ---------------------------------------------------------------------------
# Text scorecard
# ---------------------------------------------------------------------------


def _pad_line(content: str, width: int = CARD_WIDTH) -> str:
    """Pad a line to fit inside the box (between ║ markers)."""
    inner = width - 4  # 2 chars for ║ + space on each side
    if len(content) > inner:
        content = content[: inner - 1] + "\u2026"  # …
    return f"{BOX_V} {content:<{inner}} {BOX_V}"


def _horizontal_rule(left: str, right: str, width: int = CARD_WIDTH) -> str:
    """Draw a horizontal rule."""
    return left + BOX_H * (width - 2) + right


def render_text_scorecard(record: Dict[str, Any], history: List[Dict[str, Any]]) -> str:
    """Render a single scorecard as a visual Unicode box."""
    lines: List[str] = []
    skill = record.get("skill", "unknown")
    grade = record.get("grade", "?")
    grade_label = record.get("grade_label", "")
    composite = record.get("composite_score", 0.0)
    timestamp = record.get("timestamp", "")
    summary = record.get("one_liner", record.get("summary", ""))

    # Top border
    lines.append(_horizontal_rule(BOX_TL, BOX_TR))

    # Header
    header = f"SKILLJUDGE SCORECARD -- {skill}"
    lines.append(_pad_line(header))
    lines.append(_pad_line(f"Grade: {grade} ({grade_label})  |  Composite: {composite}/10.0  |  {timestamp}"))
    lines.append(_horizontal_rule(BOX_ML, BOX_MR))

    # Dimension scores
    dimensions = record.get("dimensions", {})

    # Build per-dimension history for trends
    dim_history: Dict[str, List[float]] = {d: [] for d in DIMENSION_ORDER}
    for past in history:
        past_dims = past.get("dimensions", {})
        for d in DIMENSION_ORDER:
            if d in past_dims:
                dim_history[d].append(past_dims[d].get("score", 5))

    for dim in DIMENSION_ORDER:
        data = dimensions.get(dim, {})
        score = data.get("score", 0)
        weight = data.get("weight", 0)
        justification = data.get("justification", "")
        bar = _render_bar(score)
        trend = _compute_trend(dim_history.get(dim, []))

        dim_label = f"{dim.capitalize():<15}"
        score_str = f"{score:>4.1f}/10"
        weight_str = f"(w={weight:.2f})"

        # Truncate justification to fit
        max_just = CARD_WIDTH - 4 - 15 - len(bar) - 2 - 8 - 9 - 4 - 2
        if len(justification) > max_just:
            justification = justification[: max_just - 1] + "\u2026"

        line = f"{dim_label}{bar}  {score_str} {weight_str} {trend} {justification}"
        lines.append(_pad_line(line))

    lines.append(_horizontal_rule(BOX_ML, BOX_MR))

    # Summary
    lines.append(_pad_line(f"Summary: {summary}"))

    # Critical issues
    issues = record.get("critical_issues", [])
    if issues:
        lines.append(_pad_line(""))
        lines.append(_pad_line("CRITICAL ISSUES:"))
        for issue in issues:
            lines.append(_pad_line(f"  ! {issue}"))

    # Recommendations
    recs = record.get("recommendations", [])
    if recs:
        lines.append(_pad_line(""))
        lines.append(_pad_line("RECOMMENDATIONS:"))
        for rec in recs:
            lines.append(_pad_line(f"  * {rec}"))

    # Bottom border
    lines.append(_horizontal_rule(BOX_BL, BOX_BR))

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Averages
# ---------------------------------------------------------------------------


def compute_averages(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute average scores across a set of records."""
    if not records:
        return {}

    composite_values: List[float] = []
    dim_values: Dict[str, List[float]] = {d: [] for d in DIMENSION_ORDER}

    for record in records:
        if "composite_score" in record:
            composite_values.append(record["composite_score"])
        dims = record.get("dimensions", {})
        for d in DIMENSION_ORDER:
            if d in dims:
                dim_values[d].append(dims[d].get("score", 0))

    averages: Dict[str, Any] = {
        "count": len(records),
        "composite_avg": round(sum(composite_values) / len(composite_values), 2) if composite_values else 0,
    }

    dim_avgs: Dict[str, float] = {}
    for d in DIMENSION_ORDER:
        vals = dim_values[d]
        dim_avgs[d] = round(sum(vals) / len(vals), 2) if vals else 0
    averages["dimension_averages"] = dim_avgs

    return averages


def render_averages_text(averages: Dict[str, Any]) -> str:
    """Render averages as a text block."""
    if not averages:
        return "No data available for averages."

    lines: List[str] = []
    lines.append("")
    lines.append(_horizontal_rule(BOX_TL, BOX_TR))
    lines.append(_pad_line(f"HISTORICAL AVERAGES ({averages.get('count', 0)} scores)"))
    lines.append(_horizontal_rule(BOX_ML, BOX_MR))
    lines.append(_pad_line(f"Composite Average: {averages.get('composite_avg', 0)}/10.0"))
    lines.append(_pad_line(""))

    dim_avgs = averages.get("dimension_averages", {})
    for dim in DIMENSION_ORDER:
        avg = dim_avgs.get(dim, 0)
        bar = _render_bar(avg)
        lines.append(_pad_line(f"  {dim.capitalize():<15}{bar}  {avg:>4.1f}/10"))

    lines.append(_horizontal_rule(BOX_BL, BOX_BR))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def render_json_output(records: List[Dict[str, Any]], averages: Dict[str, Any]) -> str:
    """Render records and averages as JSON."""
    output = {
        "scores": records,
        "averages": averages,
    }
    return json.dumps(output, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="report",
        description="SkillJudge Score Reporter -- view scorecards, trends, and averages.",
    )
    parser.add_argument(
        "--scores-dir",
        required=True,
        help="Directory containing score JSON files.",
    )
    parser.add_argument(
        "--skill",
        default=None,
        help="Filter by skill name (optional).",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=None,
        help="Show only the last N scores.",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        dest="output_format",
        help="Output format (default: text).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    """Entry point for CLI invocation."""
    args = parse_args(argv)

    records = load_scores(
        scores_dir=args.scores_dir,
        skill_name=args.skill,
        last_n=args.last,
    )

    if not records:
        skill_msg = f" for skill '{args.skill}'" if args.skill else ""
        print(f"No scores found{skill_msg} in {args.scores_dir}", file=sys.stderr)
        sys.exit(0)

    averages = compute_averages(records)

    if args.output_format == "json":
        print(render_json_output(records, averages))
    else:
        # Text mode: render each scorecard + averages
        for i, record in enumerate(records):
            # Pass full history up to this point for trend computation
            history_so_far = records[:i]
            print(render_text_scorecard(record, history_so_far))
            if i < len(records) - 1:
                print()  # Blank line between cards

        # Show averages if more than one record
        if len(records) > 1:
            print(render_averages_text(averages))


if __name__ == "__main__":
    main()
