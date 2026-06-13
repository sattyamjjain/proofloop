#!/usr/bin/env python3
"""Compare two Proofloop scorecards and render a delta report.

Powers ``/judge --against HEAD~1`` (and the more general
``--against <timestamp>``): picks two scorecards for the same skill and
prints a side-by-side Unicode table showing per-dimension deltas plus a
composite verdict (improved / regressed / flat).

Usage:
    python3 skills/judge/scripts/against.py \\
      --skill code-review \\
      --scores-dir skills/judge/scores \\
      [--baseline-index -2] [--target-index -1]

Baseline and target indices are resolved against the skill's scorecards
sorted by timestamp ascending; negative indices count from the end, so
``--baseline-index -2`` is the penultimate run and ``--target-index -1``
(the default) is the latest. Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DIMENSIONS = [
    "correctness", "completeness", "adherence", "actionability",
    "efficiency", "safety", "consistency",
]


def _load_history(scores_dir: Path, skill: str) -> List[Dict[str, Any]]:
    if not scores_dir.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    for path in sorted(scores_dir.glob(f"{skill}_*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    out.sort(key=lambda s: s.get("timestamp", ""))
    return out


def _arrow(delta: float) -> str:
    if delta > 0.05:
        return "↑"
    if delta < -0.05:
        return "↓"
    return "→"


def _pad(value: str, width: int) -> str:
    return value.ljust(width)[:width]


def render(baseline: Dict[str, Any], target: Dict[str, Any]) -> str:
    """Return a Unicode table summarising the delta between two scorecards."""
    lines: List[str] = []
    header = f"Proofloop delta: {target.get('skill', '?')}"
    lines.append("╭" + "─" * (len(header) + 2) + "╮")
    lines.append(f"│ {header} │")
    lines.append("╰" + "─" * (len(header) + 2) + "╯")
    lines.append(
        f"baseline: {baseline.get('timestamp', '?')}  composite {baseline.get('composite_score', 0):.2f}/{baseline.get('grade', '?')}"
    )
    lines.append(
        f"target:   {target.get('timestamp', '?')}  composite {target.get('composite_score', 0):.2f}/{target.get('grade', '?')}"
    )
    lines.append("")
    lines.append(f"{'dimension':<15} {'before':>7}  {'after':>7}  {'delta':>7}")
    lines.append("─" * 45)
    for dim in DIMENSIONS:
        before = baseline.get("dimensions", {}).get(dim, {}).get("score", 0)
        after = target.get("dimensions", {}).get(dim, {}).get("score", 0)
        delta = after - before
        lines.append(
            f"{_pad(dim, 15)} {before:>7}  {after:>7}  {delta:>+6.1f} {_arrow(delta)}"
        )
    lines.append("─" * 45)
    composite_delta = target.get("composite_score", 0) - baseline.get("composite_score", 0)
    lines.append(f"{_pad('composite', 15)} {baseline.get('composite_score', 0):>7.2f}  {target.get('composite_score', 0):>7.2f}  {composite_delta:>+6.2f} {_arrow(composite_delta)}")
    lines.append("")
    if composite_delta > 0.05:
        lines.append(f"Proofloop: IMPROVED (+{composite_delta:.2f})")
    elif composite_delta < -0.05:
        lines.append(f"Proofloop: REGRESSED ({composite_delta:+.2f})")
    else:
        lines.append("Proofloop: FLAT")
    return "\n".join(lines)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="verdict-against")
    p.add_argument("--skill", required=True, help="Skill to compare.")
    p.add_argument("--scores-dir", required=True, help="Directory of scorecard JSON files.")
    p.add_argument("--baseline-index", type=int, default=-2,
                   help="Index into sorted history for the baseline run (default -2 = penultimate).")
    p.add_argument("--target-index", type=int, default=-1,
                   help="Index into sorted history for the target run (default -1 = latest).")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    history = _load_history(Path(args.scores_dir), args.skill)
    if len(history) < 2:
        print(
            f"Need at least 2 scorecards for {args.skill}; found {len(history)}.",
            file=sys.stderr,
        )
        return 1
    try:
        baseline = history[args.baseline_index]
        target = history[args.target_index]
    except IndexError:
        print(
            f"Index out of range: --baseline-index {args.baseline_index} "
            f"/ --target-index {args.target_index} against history of {len(history)}.",
            file=sys.stderr,
        )
        return 1
    print(render(baseline, target))
    # Exit 2 on regression so CI can gate on it.
    composite_delta = target.get("composite_score", 0) - baseline.get("composite_score", 0)
    return 2 if composite_delta < -0.05 else 0


if __name__ == "__main__":
    sys.exit(main())
