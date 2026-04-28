#!/usr/bin/env python3
"""Ship-gate CLI — pass/fail a release scorecard against ship-readiness floors.

Reads a Verdict scorecard JSON (the shape ``score.build_scorecard``
produces and persists to ``scores/``) and decides whether the
candidate is safe to merge:

1. The scorecard's ``adjustments.ship_readiness.ship_ready`` flag
   must be ``true`` (i.e., every ship-readiness floor passed).
2. The composite score must be ≥ ``--floor`` (default 7.0).
3. If ``--baseline`` is supplied, the regression vs. that baseline
   must be ≤ ``--max-regression-pct`` (default 5%).

Returns ``0`` when all gates pass; non-zero otherwise. Optional
``--output sarif`` produces a SARIF v2.1.0 file the GitHub Actions
"security" tab consumes.

Stdlib-only. No third-party deps.

Usage::

    python3 skills/judge/scripts/ship_gate.py \\
        --scorecard skills/judge/scores/release_TIMESTAMP.json \\
        --floor 7.5 \\
        --baseline skills/judge/scores/release_PRIOR.json \\
        --max-regression-pct 0.05 \\
        --output sarif > ship-gate.sarif

Exit codes:

- 0 — gate passed.
- 1 — gate failed.
- 2 — invalid input (missing scorecard, malformed JSON, etc.).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_COMPOSITE_FLOOR: float = 7.0
DEFAULT_MAX_REGRESSION_PCT: float = 0.05
SARIF_VERSION: str = "2.1.0"
TOOL_NAME: str = "verdict-ship-gate"


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def load_scorecard(path: str) -> Dict[str, Any]:
    """Load a Verdict scorecard JSON file.

    Raises :class:`FileNotFoundError` or :class:`ValueError` for
    malformed inputs.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"scorecard not found: {path}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"scorecard is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("scorecard JSON must be an object")
    return data


def evaluate_gate(
    scorecard: Dict[str, Any],
    floor: float,
    baseline: Optional[Dict[str, Any]] = None,
    max_regression_pct: float = DEFAULT_MAX_REGRESSION_PCT,
) -> Dict[str, Any]:
    """Evaluate the three ship-gate checks against a scorecard.

    Returns a dict with:

    - ``passed`` (bool): True iff all checks pass.
    - ``failures`` (list[str]): one entry per failing check.
    - ``composite_score`` (float): the candidate's composite.
    - ``floor`` (float): the configured floor (echoed for audit).
    - ``ship_ready`` (bool): the scorecard's ship_ready flag.
    - ``failed_floors`` (list[str]): floors that failed in the
      scorecard's ship_readiness block.
    - ``composite_delta`` (Optional[float]): vs. baseline when
      provided; ``None`` otherwise.
    """
    failures: List[str] = []
    composite = float(scorecard.get("composite_score", 0.0))
    adjustments = scorecard.get("adjustments", {}) or {}
    ship_block = adjustments.get("ship_readiness", {}) or {}
    ship_ready = bool(ship_block.get("ship_ready", True))
    failed_floors = list(ship_block.get("failed_floors", []) or [])

    # Check 1: ship_readiness floors.
    if not ship_ready:
        failures.append(
            f"ship_readiness floors not met: {', '.join(failed_floors) or 'unknown'}"
        )

    # Check 2: composite floor.
    if composite < floor:
        failures.append(
            f"composite score {composite:.2f} below floor {floor:.2f}"
        )

    # Check 3: regression vs. baseline.
    composite_delta: Optional[float] = None
    if baseline is not None:
        base_composite = float(baseline.get("composite_score", 0.0))
        if base_composite > 0:
            composite_delta = round(composite - base_composite, 4)
            regression_pct = -composite_delta / base_composite
            if regression_pct > max_regression_pct:
                failures.append(
                    f"composite regressed by {regression_pct * 100:.1f}% vs. "
                    f"baseline (max {max_regression_pct * 100:.1f}%)"
                )

    return {
        "passed": not failures,
        "failures": failures,
        "composite_score": composite,
        "floor": floor,
        "ship_ready": ship_ready,
        "failed_floors": failed_floors,
        "composite_delta": composite_delta,
    }


def render_sarif(
    scorecard: Dict[str, Any],
    gate: Dict[str, Any],
    scorecard_path: str,
    tool_version: str = "1.4.1",
) -> Dict[str, Any]:
    """Render the gate result as a SARIF v2.1.0 document.

    SARIF is the format the GitHub Actions "security" tab consumes;
    each failure becomes a rule + result entry. Returns a dict that
    can be ``json.dumps``'d into a ``.sarif`` file.
    """
    rules: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    for failure in gate["failures"]:
        rule_id = _rule_id_for_failure(failure)
        rules.append({
            "id": rule_id,
            "name": rule_id,
            "shortDescription": {"text": failure[:120]},
            "fullDescription": {"text": failure},
            "defaultConfiguration": {"level": "error"},
        })
        results.append({
            "ruleId": rule_id,
            "level": "error",
            "message": {"text": failure},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": scorecard_path},
                },
            }],
        })
    if not rules:
        # SARIF requires the rules array to exist; an empty list is
        # valid and signals "no findings".
        rules = []
    return {
        "version": SARIF_VERSION,
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {
                "driver": {
                    "name": TOOL_NAME,
                    "version": tool_version,
                    "informationUri": (
                        "https://github.com/sattyamjjain/verdict"
                    ),
                    "rules": rules,
                },
            },
            "results": results,
            "invocations": [{
                "executionSuccessful": gate["passed"],
                "endTimeUtc": datetime.now(timezone.utc).strftime(
                    "%Y-%m-%dT%H:%M:%SZ",
                ),
                "exitCode": 0 if gate["passed"] else 1,
            }],
            "properties": {
                "skill": scorecard.get("skill", "unknown"),
                "composite_score": gate["composite_score"],
                "floor": gate["floor"],
                "composite_delta": gate["composite_delta"],
            },
        }],
    }


def _rule_id_for_failure(failure: str) -> str:
    """Map a failure string to a stable SARIF rule id."""
    if "ship_readiness" in failure:
        return "VERDICT-SHIP-001"
    if "composite score" in failure and "below floor" in failure:
        return "VERDICT-SHIP-002"
    if "regressed" in failure:
        return "VERDICT-SHIP-003"
    return "VERDICT-SHIP-000"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="ship_gate",
        description=(
            "Pass/fail a Verdict scorecard against ship-readiness floors. "
            "Returns 0 on pass, 1 on fail, 2 on bad input."
        ),
    )
    parser.add_argument(
        "--scorecard",
        required=True,
        help="Path to the candidate scorecard JSON.",
    )
    parser.add_argument(
        "--floor",
        type=float,
        default=DEFAULT_COMPOSITE_FLOOR,
        help=f"Composite-score floor (default {DEFAULT_COMPOSITE_FLOOR}).",
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help="Optional path to a baseline scorecard for regression check.",
    )
    parser.add_argument(
        "--max-regression-pct",
        type=float,
        default=DEFAULT_MAX_REGRESSION_PCT,
        help=(
            "Max tolerated composite-score regression as a fraction "
            f"(default {DEFAULT_MAX_REGRESSION_PCT})."
        ),
    )
    parser.add_argument(
        "--output",
        choices=("text", "json", "sarif"),
        default="text",
        help="Output format.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point. Returns the gate exit code."""
    args = parse_args(argv)
    try:
        scorecard = load_scorecard(args.scorecard)
        baseline = (
            load_scorecard(args.baseline) if args.baseline else None
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"ship_gate: {exc}", file=sys.stderr)
        return 2

    gate = evaluate_gate(
        scorecard=scorecard,
        floor=args.floor,
        baseline=baseline,
        max_regression_pct=args.max_regression_pct,
    )

    if args.output == "sarif":
        sarif = render_sarif(scorecard, gate, args.scorecard)
        print(json.dumps(sarif, indent=2))
    elif args.output == "json":
        print(json.dumps(gate, indent=2))
    else:
        if gate["passed"]:
            print(f"PASS — composite {gate['composite_score']:.2f} "
                  f"≥ floor {gate['floor']:.2f}; ship_ready=true.")
        else:
            print("FAIL — ship gate blocked the release:")
            for f in gate["failures"]:
                print(f"  - {f}")
    return 0 if gate["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
