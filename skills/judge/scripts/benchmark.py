#!/usr/bin/env python3
"""SkillJudge Benchmark Comparator.

Compares a skill's historical scores against benchmark standards and identifies
strengths, weaknesses, and specific improvement suggestions.

Usage:
    python3 benchmark.py --skill SKILL_NAME --scores-dir SCORES_DIR \
                         --references-dir REFERENCES_DIR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DIMENSION_ORDER = [
    "correctness",
    "completeness",
    "adherence",
    "actionability",
    "efficiency",
    "safety",
    "consistency",
]

# Default benchmarks used when no benchmark-standards.md is found
DEFAULT_BENCHMARKS: Dict[str, float] = {
    "correctness": 8.0,
    "completeness": 7.5,
    "adherence": 7.5,
    "actionability": 7.0,
    "efficiency": 7.0,
    "safety": 9.0,
    "consistency": 7.0,
}

DEFAULT_COMPOSITE_BENCHMARK = 7.5

# Per-dimension improvement suggestions
IMPROVEMENT_MAP: Dict[str, List[str]] = {
    "correctness": [
        "Add explicit verification steps after code generation",
        "Cross-reference output against known-good examples",
        "Run automated tests or linting before finalizing output",
        "Check for hallucinated facts or fabricated references",
    ],
    "completeness": [
        "Create a checklist of all user requirements before starting",
        "Review the transcript for unanswered questions or unfinished tasks",
        "Search for TODO/FIXME/placeholder markers before completion",
        "Address edge cases mentioned in the requirements",
    ],
    "adherence": [
        "Re-read skill instructions before and after execution",
        "Verify all constraints and format requirements are met",
        "Compare output structure against the expected template",
        "Check for deviations from specified coding style or conventions",
    ],
    "actionability": [
        "Ensure all code blocks compile/run without modification",
        "Remove placeholder values and template markers",
        "Include necessary imports, configurations, and dependencies",
        "Provide clear instructions for how to use the output",
    ],
    "efficiency": [
        "Reduce unnecessary tool calls and file reads",
        "Avoid retrying the same action multiple times",
        "Plan the approach before executing to minimize backtracking",
        "Keep output concise -- remove verbose explanations when action suffices",
    ],
    "safety": [
        "Audit all commands for destructive potential (rm -rf, --force, etc.)",
        "Never hardcode secrets or credentials in output",
        "Use environment variables or config files for sensitive data",
        "Add safety guards and confirmation prompts for destructive operations",
    ],
    "consistency": [
        "Establish and follow consistent coding patterns across executions",
        "Maintain stable quality level regardless of task complexity",
        "Document conventions so they can be reused in future executions",
        "Review prior scores and address recurring weak points",
    ],
}

# ---------------------------------------------------------------------------
# Benchmark standards loading
# ---------------------------------------------------------------------------


def load_benchmark_standards(references_dir: str) -> Dict[str, Any]:
    """Load benchmark standards from references-dir/benchmark-standards.md.

    The markdown file is expected to contain a table or structured data with
    per-dimension benchmark scores. Falls back to defaults if not found or
    unparseable.

    Returns a dict with 'dimensions' (name -> benchmark score) and 'composite'.
    """
    standards_path = Path(references_dir) / "benchmark-standards.md"
    if not standards_path.is_file():
        return {
            "dimensions": dict(DEFAULT_BENCHMARKS),
            "composite": DEFAULT_COMPOSITE_BENCHMARK,
            "source": "defaults",
        }

    text = standards_path.read_text(encoding="utf-8")
    benchmarks = dict(DEFAULT_BENCHMARKS)
    composite = DEFAULT_COMPOSITE_BENCHMARK

    # Parse table rows like: | correctness | 8.0 | ... |
    table_pattern = re.compile(
        r"\|\s*(\w+)\s*\|\s*(\d+(?:\.\d+)?)\s*\|", re.IGNORECASE
    )
    for match in table_pattern.finditer(text):
        dim = match.group(1).lower().strip()
        if dim in benchmarks:
            try:
                benchmarks[dim] = float(match.group(2))
            except ValueError:
                pass

    # Parse composite benchmark if present
    composite_pattern = re.compile(
        r"composite[:\s]*(\d+(?:\.\d+)?)", re.IGNORECASE
    )
    composite_match = composite_pattern.search(text)
    if composite_match:
        try:
            composite = float(composite_match.group(1))
        except ValueError:
            pass

    return {
        "dimensions": benchmarks,
        "composite": composite,
        "source": str(standards_path),
    }


# ---------------------------------------------------------------------------
# Score loading
# ---------------------------------------------------------------------------


def load_skill_scores(scores_dir: str, skill_name: str) -> List[Dict[str, Any]]:
    """Load all score JSON files for *skill_name* from *scores_dir*.

    Returns a list of scorecards sorted by timestamp (oldest first).
    """
    scores_path = Path(scores_dir)
    if not scores_path.is_dir():
        return []

    records: List[Dict[str, Any]] = []
    for entry in scores_path.iterdir():
        if not entry.is_file() or not entry.name.endswith(".json"):
            continue
        if not entry.name.startswith(f"{skill_name}_"):
            continue
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
            records.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    records.sort(key=lambda d: d.get("timestamp", ""))
    return records


# ---------------------------------------------------------------------------
# Average computation
# ---------------------------------------------------------------------------


def compute_dimension_averages(
    records: List[Dict[str, Any]],
) -> Tuple[Dict[str, float], float]:
    """Compute per-dimension averages and composite average.

    Returns (dim_averages, composite_average).
    """
    dim_values: Dict[str, List[float]] = {d: [] for d in DIMENSION_ORDER}
    composite_values: List[float] = []

    for record in records:
        if "composite_score" in record:
            composite_values.append(record["composite_score"])
        dims = record.get("dimensions", {})
        for d in DIMENSION_ORDER:
            if d in dims:
                dim_values[d].append(dims[d].get("score", 0))

    dim_avgs: Dict[str, float] = {}
    for d in DIMENSION_ORDER:
        vals = dim_values[d]
        dim_avgs[d] = round(sum(vals) / len(vals), 2) if vals else 0

    composite_avg = (
        round(sum(composite_values) / len(composite_values), 2)
        if composite_values
        else 0
    )

    return dim_avgs, composite_avg


# ---------------------------------------------------------------------------
# Delta analysis
# ---------------------------------------------------------------------------


def analyze_deltas(
    dim_avgs: Dict[str, float], benchmarks: Dict[str, float]
) -> List[Dict[str, Any]]:
    """Compare dimension averages against benchmarks.

    Returns a list of dicts with dimension, average, benchmark, delta, and status.
    """
    results: List[Dict[str, Any]] = []
    for dim in DIMENSION_ORDER:
        avg = dim_avgs.get(dim, 0)
        bench = benchmarks.get(dim, 7.0)
        delta = round(avg - bench, 2)

        if delta >= 1.0:
            status = "well above"
        elif delta >= 0.0:
            status = "above"
        elif delta >= -1.0:
            status = "slightly below"
        else:
            status = "below"

        results.append(
            {
                "dimension": dim,
                "average": avg,
                "benchmark": bench,
                "delta": delta,
                "status": status,
            }
        )

    return results


# ---------------------------------------------------------------------------
# Strengths, weaknesses, and suggestions
# ---------------------------------------------------------------------------


def identify_extremes(
    deltas: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Identify the strongest and weakest dimensions relative to benchmark."""
    sorted_by_delta = sorted(deltas, key=lambda d: d["delta"])
    weakest = [d for d in sorted_by_delta if d["delta"] < 0]
    strongest = [d for d in reversed(sorted_by_delta) if d["delta"] >= 0]
    return strongest, weakest


def suggest_improvements(weakest: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Generate targeted improvement suggestions for below-benchmark dimensions."""
    suggestions: List[Dict[str, Any]] = []
    for entry in weakest:
        dim = entry["dimension"]
        tips = IMPROVEMENT_MAP.get(dim, ["Review and improve this dimension"])
        # Select tips proportional to how far below benchmark
        n_tips = min(len(tips), max(1, int(abs(entry["delta"])) + 1))
        suggestions.append(
            {
                "dimension": dim,
                "delta": entry["delta"],
                "tips": tips[:n_tips],
            }
        )
    return suggestions


# ---------------------------------------------------------------------------
# Text rendering
# ---------------------------------------------------------------------------

BOX_H = "\u2550"
BOX_V = "\u2551"
CARD_WIDTH = 80


def _pad(content: str) -> str:
    """Pad content inside box borders."""
    inner = CARD_WIDTH - 4
    if len(content) > inner:
        content = content[: inner - 1] + "\u2026"
    return f"{BOX_V} {content:<{inner}} {BOX_V}"


def _hr(left: str, right: str) -> str:
    return left + BOX_H * (CARD_WIDTH - 2) + right


def render_benchmark_report(
    skill_name: str,
    num_scores: int,
    composite_avg: float,
    composite_benchmark: float,
    deltas: List[Dict[str, Any]],
    strongest: List[Dict[str, Any]],
    weakest: List[Dict[str, Any]],
    suggestions: List[Dict[str, Any]],
    source: str,
) -> str:
    """Render the full benchmark comparison as a text report."""
    lines: List[str] = []

    lines.append(_hr("\u2554", "\u2557"))
    lines.append(_pad(f"BENCHMARK COMPARISON -- {skill_name}"))
    lines.append(_pad(f"Based on {num_scores} historical score(s)  |  Benchmark source: {source}"))
    lines.append(_hr("\u2560", "\u2563"))

    # Composite comparison
    comp_delta = round(composite_avg - composite_benchmark, 2)
    delta_str = f"+{comp_delta}" if comp_delta >= 0 else str(comp_delta)
    lines.append(_pad(f"Composite: {composite_avg}/10.0  vs  Benchmark: {composite_benchmark}/10.0  ({delta_str})"))
    lines.append(_pad(""))

    # Per-dimension table
    lines.append(_pad(f"{'Dimension':<15} {'Avg':>6} {'Bench':>6} {'Delta':>7}  Status"))
    lines.append(_pad("-" * 60))

    for entry in deltas:
        dim = entry["dimension"]
        avg = entry["average"]
        bench = entry["benchmark"]
        delta = entry["delta"]
        status = entry["status"]
        delta_str = f"+{delta:.2f}" if delta >= 0 else f"{delta:.2f}"
        symbol = "\u2713" if delta >= 0 else "\u2717"  # ✓ / ✗
        lines.append(
            _pad(f"{dim.capitalize():<15} {avg:>5.1f} {bench:>6.1f} {delta_str:>7}  {symbol} {status}")
        )

    lines.append(_hr("\u2560", "\u2563"))

    # Strengths
    lines.append(_pad("STRONGEST DIMENSIONS:"))
    if strongest:
        for s in strongest[:3]:
            lines.append(_pad(f"  + {s['dimension'].capitalize()}: +{s['delta']:.2f} above benchmark"))
    else:
        lines.append(_pad("  (none above benchmark)"))

    lines.append(_pad(""))

    # Weaknesses
    lines.append(_pad("WEAKEST DIMENSIONS:"))
    if weakest:
        for w in weakest[:3]:
            lines.append(_pad(f"  - {w['dimension'].capitalize()}: {w['delta']:.2f} below benchmark"))
    else:
        lines.append(_pad("  (all at or above benchmark)"))

    # Improvement suggestions
    if suggestions:
        lines.append(_hr("\u2560", "\u2563"))
        lines.append(_pad("IMPROVEMENT SUGGESTIONS:"))
        for sug in suggestions:
            lines.append(_pad(""))
            lines.append(_pad(f"  {sug['dimension'].capitalize()} ({sug['delta']:+.2f}):"))
            for tip in sug["tips"]:
                lines.append(_pad(f"    * {tip}"))

    lines.append(_hr("\u255a", "\u255d"))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def build_json_report(
    skill_name: str,
    num_scores: int,
    composite_avg: float,
    composite_benchmark: float,
    deltas: List[Dict[str, Any]],
    strongest: List[Dict[str, Any]],
    weakest: List[Dict[str, Any]],
    suggestions: List[Dict[str, Any]],
    source: str,
) -> Dict[str, Any]:
    """Build a structured JSON benchmark report."""
    return {
        "skill": skill_name,
        "num_scores": num_scores,
        "composite_average": composite_avg,
        "composite_benchmark": composite_benchmark,
        "composite_delta": round(composite_avg - composite_benchmark, 2),
        "dimensions": deltas,
        "strongest": [s["dimension"] for s in strongest[:3]],
        "weakest": [w["dimension"] for w in weakest[:3]],
        "suggestions": suggestions,
        "benchmark_source": source,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="benchmark",
        description="SkillJudge Benchmark Comparator -- compare scores against benchmark standards.",
    )
    parser.add_argument(
        "--skill",
        required=True,
        help="Name of the skill to benchmark.",
    )
    parser.add_argument(
        "--scores-dir",
        required=True,
        help="Directory containing score JSON files.",
    )
    parser.add_argument(
        "--references-dir",
        required=True,
        help="Directory containing benchmark-standards.md.",
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

    # Load benchmark standards
    standards = load_benchmark_standards(args.references_dir)
    benchmarks = standards["dimensions"]
    composite_benchmark = standards["composite"]
    source = standards["source"]

    # Load historical scores
    records = load_skill_scores(args.scores_dir, args.skill)
    if not records:
        print(
            f"No scores found for skill '{args.skill}' in {args.scores_dir}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Compute averages
    dim_avgs, composite_avg = compute_dimension_averages(records)

    # Analyze
    deltas = analyze_deltas(dim_avgs, benchmarks)
    strongest, weakest = identify_extremes(deltas)
    suggestions = suggest_improvements(weakest)

    if args.output_format == "json":
        report = build_json_report(
            args.skill,
            len(records),
            composite_avg,
            composite_benchmark,
            deltas,
            strongest,
            weakest,
            suggestions,
            source,
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(
            render_benchmark_report(
                args.skill,
                len(records),
                composite_avg,
                composite_benchmark,
                deltas,
                strongest,
                weakest,
                suggestions,
                source,
            )
        )


if __name__ == "__main__":
    main()
