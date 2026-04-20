#!/usr/bin/env python3
"""Compare two scorecards for the same skill (``/judge --compare-runs``).

Differs from ``against.py``:

- ``against.py`` is time-series-aware (``--baseline-index``); it picks
  scorecards by position.
- ``compare.py`` takes two **explicit** paths and prints a narrative
  geared at Auto Memory regression detection: it annotates when the
  memory block grew, composite dropped, and consistency dimension
  slid — the three signatures of memory pollution.

Stdlib only.

Usage:
    python3 skills/judge/scripts/compare.py \\
      --run-a scorecard_a.json --run-b scorecard_b.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DIMENSIONS: List[str] = [
    "correctness", "completeness", "adherence", "actionability",
    "efficiency", "safety", "consistency",
]

# Heuristic thresholds for the narrative layer. Tuned against scorecards
# from the shipped benchmark pack — nothing magic here, just "big enough
# to warrant a sentence in the output". Override via env vars in CI if
# you want the narrative to fire more/less aggressively.
COMPOSITE_REGRESSION_THRESHOLD: float = -0.3
MEMORY_BLOCK_GROWTH_BYTES: int = 4_000
CONSISTENCY_DROP_POINTS: int = 2


def _load(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"scorecard not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _dim_score(card: Dict[str, Any], dim: str) -> Optional[int]:
    entry = card.get("dimensions", {}).get(dim)
    if not isinstance(entry, dict):
        return None
    value = entry.get("score")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _memory_block_size_bytes(card: Dict[str, Any]) -> Optional[int]:
    """Best-effort inference of memory-block size from scorecard metadata.

    Scorecards don't carry the transcript verbatim, but they do record
    ``transcript_lines``; Auto Memory sessions typically show 2-5× the
    baseline line count. When both scorecards carry a ``transcript_lines``
    field we use the DIFFERENCE as a rough proxy for "memory grew".
    Absolute byte count isn't available offline, so we return a
    pseudo-byte estimate: ``lines × 80``.
    """
    lines = card.get("transcript_lines")
    if not isinstance(lines, (int, float)) or isinstance(lines, bool):
        return None
    return int(lines) * 80


def diff_dimensions(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Tuple[Optional[int], Optional[int], Optional[int]]]:
    """Return ``{dim: (a_score, b_score, delta)}`` for every dimension."""
    out: Dict[str, Tuple[Optional[int], Optional[int], Optional[int]]] = {}
    for dim in DIMENSIONS:
        a_score = _dim_score(a, dim)
        b_score = _dim_score(b, dim)
        if a_score is None or b_score is None:
            out[dim] = (a_score, b_score, None)
        else:
            out[dim] = (a_score, b_score, b_score - a_score)
    return out


def build_narrative(a: Dict[str, Any], b: Dict[str, Any]) -> List[str]:
    """Return a list of narrative lines explaining notable deltas."""
    notes: List[str] = []

    a_composite = float(a.get("composite_score", 0.0))
    b_composite = float(b.get("composite_score", 0.0))
    composite_delta = b_composite - a_composite

    if composite_delta <= COMPOSITE_REGRESSION_THRESHOLD:
        notes.append(
            f"composite dropped {composite_delta:+.2f} ({a_composite:.2f} → {b_composite:.2f}) — regression threshold {COMPOSITE_REGRESSION_THRESHOLD:.2f}"
        )

    # Memory-block growth heuristic: transcript_lines × 80 as a rough
    # byte count. If Auto Memory sessions stitched in more data between
    # runs, this delta will exceed the threshold.
    a_mem = _memory_block_size_bytes(a)
    b_mem = _memory_block_size_bytes(b)
    if a_mem is not None and b_mem is not None and (b_mem - a_mem) >= MEMORY_BLOCK_GROWTH_BYTES:
        notes.append(
            f"memory block grew ~{a_mem // 1_000}k → ~{b_mem // 1_000}k bytes — likely memory pollution"
        )

    a_consistency = _dim_score(a, "consistency")
    b_consistency = _dim_score(b, "consistency")
    if a_consistency is not None and b_consistency is not None:
        drop = a_consistency - b_consistency
        if drop >= CONSISTENCY_DROP_POINTS:
            notes.append(
                f"consistency slid {a_consistency} → {b_consistency} ({-drop:+d}) — suggests the skill is drifting"
            )

    # Per-dimension specific regressions (-3 or more)
    hard_drops: List[str] = []
    for dim, (a_s, b_s, delta) in diff_dimensions(a, b).items():
        if delta is not None and delta <= -3:
            hard_drops.append(f"{dim} {a_s} → {b_s} ({delta:+d})")
    if hard_drops:
        notes.append("hard regressions: " + "; ".join(hard_drops))

    if not notes:
        notes.append("no notable regressions — runs are within expected variance")

    return notes


def format_report(a: Dict[str, Any], b: Dict[str, Any]) -> str:
    """Render the Unicode comparison report (stdlib, no table lib)."""
    skill_a = a.get("skill", "?")
    skill_b = b.get("skill", "?")
    ts_a = a.get("timestamp", "?")
    ts_b = b.get("timestamp", "?")
    composite_a = float(a.get("composite_score", 0.0))
    composite_b = float(b.get("composite_score", 0.0))

    lines: List[str] = []
    lines.append("╭──────────────────────────────────────────────────────╮")
    lines.append(f"│ /judge --compare-runs · {skill_a} vs {skill_b:<15} │"[:56] + " │")
    lines.append("╰──────────────────────────────────────────────────────╯")
    lines.append(f"run A: {ts_a}  composite {composite_a:.2f} / {a.get('grade', '?')}")
    lines.append(f"run B: {ts_b}  composite {composite_b:.2f} / {b.get('grade', '?')}")
    lines.append("")
    lines.append(f"{'dimension':<15} {'A':>5} {'B':>5} {'Δ':>5}")
    lines.append("─" * 37)
    for dim, (a_s, b_s, delta) in diff_dimensions(a, b).items():
        left = "-" if a_s is None else str(a_s)
        right = "-" if b_s is None else str(b_s)
        arrow = "-" if delta is None else f"{delta:+d}"
        lines.append(f"{dim:<15} {left:>5} {right:>5} {arrow:>5}")
    lines.append("─" * 37)
    lines.append("")
    lines.append("narrative:")
    for note in build_narrative(a, b):
        lines.append(f"  - {note}")
    return "\n".join(lines)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="verdict-compare")
    parser.add_argument("--run-a", required=True, help="Path to the baseline scorecard JSON.")
    parser.add_argument("--run-b", required=True, help="Path to the target scorecard JSON.")
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text).",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    try:
        a = _load(Path(args.run_a))
        b = _load(Path(args.run_b))
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.format == "json":
        payload = {
            "run_a": {"path": args.run_a, "skill": a.get("skill"), "composite": a.get("composite_score")},
            "run_b": {"path": args.run_b, "skill": b.get("skill"), "composite": b.get("composite_score")},
            "dimensions": {
                dim: {"a": a_s, "b": b_s, "delta": delta}
                for dim, (a_s, b_s, delta) in diff_dimensions(a, b).items()
            },
            "narrative": build_narrative(a, b),
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(format_report(a, b))

    composite_delta = float(b.get("composite_score", 0.0)) - float(a.get("composite_score", 0.0))
    return 2 if composite_delta <= COMPOSITE_REGRESSION_THRESHOLD else 0


if __name__ == "__main__":
    sys.exit(main())
