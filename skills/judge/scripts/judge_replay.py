#!/usr/bin/env python3
"""Judge-version replay — re-score a transcript with two judge versions
and assert per-dimension stability within a configured tolerance.

Use this to validate that a Verdict release doesn't silently move
scores on previously-judged transcripts. The flow:

1. Score the transcript using the *current* installed Verdict
   (whatever version of ``score.build_scorecard`` is on
   ``sys.path``).
2. Compare against a frozen baseline scorecard JSON file (the
   shape ``score.build_scorecard`` persists).
3. Assert that the absolute per-dimension delta is ≤
   ``--tolerance`` (default 0.5) and the composite delta is ≤
   ``--composite-tolerance`` (default 0.3).

Stdlib-only. No network, no LLM calls beyond what
``score.build_scorecard`` itself does (which is off by default).

Returns ``0`` when both gates pass; non-zero otherwise.

Usage::

    python3 skills/judge/scripts/judge_replay.py \\
        --transcript path/to/canonical.jsonl \\
        --baseline-scorecard skills/judge/scores/canonical_v1.4.0.json \\
        --skill code-review \\
        --rubric-dir skills/judge/rubrics \\
        --tolerance 0.5 \\
        --composite-tolerance 0.3

Exit codes:

- 0 — replay deltas within tolerance.
- 1 — at least one dimension or the composite drifted beyond
  tolerance. Stderr lists the offenders.
- 2 — invalid input.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import score  # type: ignore[import-not-found]

DEFAULT_TOLERANCE: float = 0.5
DEFAULT_COMPOSITE_TOLERANCE: float = 0.3


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def load_scorecard(path: str) -> Dict[str, Any]:
    """Load a Verdict scorecard JSON file."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"baseline scorecard not found: {path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"baseline is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("baseline must be a JSON object")
    return data


def diff_scorecards(
    candidate: Dict[str, Any],
    baseline: Dict[str, Any],
    tolerance: float,
    composite_tolerance: float,
) -> Dict[str, Any]:
    """Compute per-dimension and composite deltas, flag breaches.

    Returns a dict with:

    - ``per_dimension`` — ``{dim: {baseline, candidate, delta, breach}}``
    - ``composite_delta`` (float)
    - ``composite_breach`` (bool)
    - ``breached_dimensions`` (list[str])
    - ``passed`` (bool)
    """
    cand_dims = candidate.get("dimensions", {}) or {}
    base_dims = baseline.get("dimensions", {}) or {}
    per_dimension: Dict[str, Dict[str, Any]] = {}
    breached: List[str] = []
    for dim in sorted(set(cand_dims) | set(base_dims)):
        c = cand_dims.get(dim, {})
        b = base_dims.get(dim, {})
        c_score = c.get("score") if isinstance(c, dict) else None
        b_score = b.get("score") if isinstance(b, dict) else None
        if not isinstance(c_score, (int, float)):
            continue
        if not isinstance(b_score, (int, float)):
            continue
        delta = round(float(c_score) - float(b_score), 2)
        breach = abs(delta) > tolerance
        per_dimension[dim] = {
            "baseline": float(b_score),
            "candidate": float(c_score),
            "delta": delta,
            "breach": breach,
        }
        if breach:
            breached.append(dim)
    composite_delta = round(
        float(candidate.get("composite_score", 0.0))
        - float(baseline.get("composite_score", 0.0)),
        2,
    )
    composite_breach = abs(composite_delta) > composite_tolerance
    return {
        "per_dimension": per_dimension,
        "composite_delta": composite_delta,
        "composite_breach": composite_breach,
        "breached_dimensions": breached,
        "passed": not breached and not composite_breach,
        "tolerance": tolerance,
        "composite_tolerance": composite_tolerance,
    }


# ---------------------------------------------------------------------------
# Replay execution
# ---------------------------------------------------------------------------


def replay(
    transcript_path: str,
    skill: str,
    rubric_dir: str,
    baseline_scorecard_path: str,
    tolerance: float = DEFAULT_TOLERANCE,
    composite_tolerance: float = DEFAULT_COMPOSITE_TOLERANCE,
    config_path: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Run a replay and return ``(diff, candidate_scorecard)``.

    Re-scores *transcript_path* with the currently-installed Verdict
    and diffs against the persisted baseline scorecard. Uses a
    throwaway temporary directory for the candidate's scores file
    so the replay doesn't pollute the live ``scores/`` tree.
    """
    baseline = load_scorecard(baseline_scorecard_path)
    with tempfile.TemporaryDirectory() as t:
        candidate = score.build_scorecard(
            skill_name=skill,
            transcript_path=transcript_path,
            rubric_dir=rubric_dir,
            scores_dir=str(Path(t) / "replay_scores"),
            config_path=config_path,
        )
    diff = diff_scorecards(
        candidate, baseline, tolerance, composite_tolerance,
    )
    return diff, candidate


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="judge_replay",
        description=(
            "Re-score a transcript with the current Verdict and assert "
            "per-dimension stability vs. a baseline scorecard."
        ),
    )
    parser.add_argument(
        "--transcript",
        required=True,
        help="Path to the transcript file (JSON-lines or plain text).",
    )
    parser.add_argument(
        "--skill",
        required=True,
        help="Name of the skill being replayed (selects the rubric).",
    )
    parser.add_argument(
        "--rubric-dir",
        required=True,
        help="Directory containing rubric .md files.",
    )
    parser.add_argument(
        "--baseline-scorecard",
        required=True,
        help="Path to the persisted baseline scorecard JSON.",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=(
            "Per-dimension absolute delta tolerance "
            f"(default {DEFAULT_TOLERANCE})."
        ),
    )
    parser.add_argument(
        "--composite-tolerance",
        type=float,
        default=DEFAULT_COMPOSITE_TOLERANCE,
        help=(
            "Composite-score absolute delta tolerance "
            f"(default {DEFAULT_COMPOSITE_TOLERANCE})."
        ),
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to judge-config.json (optional).",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns 0 on within-tolerance, 1 on breach, 2 on bad input."""
    args = parse_args(argv)
    try:
        diff, _ = replay(
            transcript_path=args.transcript,
            skill=args.skill,
            rubric_dir=args.rubric_dir,
            baseline_scorecard_path=args.baseline_scorecard,
            tolerance=args.tolerance,
            composite_tolerance=args.composite_tolerance,
            config_path=args.config,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"judge_replay: {exc}", file=sys.stderr)
        return 2

    if args.output == "json":
        print(json.dumps(diff, indent=2))
    else:
        if diff["passed"]:
            print(
                f"PASS — all {len(diff['per_dimension'])} dimensions within "
                f"±{args.tolerance:.2f}; composite delta "
                f"{diff['composite_delta']:+.2f} within "
                f"±{args.composite_tolerance:.2f}."
            )
        else:
            print("FAIL — replay drifted beyond tolerance:")
            if diff["composite_breach"]:
                print(
                    f"  * composite delta {diff['composite_delta']:+.2f} "
                    f"exceeds ±{args.composite_tolerance:.2f}"
                )
            for dim in diff["breached_dimensions"]:
                vals = diff["per_dimension"][dim]
                print(
                    f"  * {dim}: {vals['baseline']:.2f} → "
                    f"{vals['candidate']:.2f} "
                    f"(delta {vals['delta']:+.2f})"
                )
    return 0 if diff["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
