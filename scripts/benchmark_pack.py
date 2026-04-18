#!/usr/bin/env python3
"""Run the curated transcript corpus through the scoring engine and
assert each case satisfies its expected bounds. Exits 1 on any failure.

Used by CI to catch heuristic regressions before they ship. Stdlib-only.

Usage:
    python3 scripts/benchmark_pack.py [manifest_path]

If omitted, defaults to ``benchmarks/manifest.json`` relative to the
project root.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCORE_PY = PROJECT_ROOT / "skills" / "judge" / "scripts" / "score.py"
RUBRICS_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"
CONFIG_PATH = PROJECT_ROOT / "judge-config.json"

sys.path.insert(0, str(SCORE_PY.parent))
import score  # noqa: E402  -- must follow sys.path manipulation

# A→F in descending order so "grade_min: B" accepts A-, A, A+ but not B-
GRADE_ORDER: List[str] = [
    "F", "D", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+",
]


def _rank(grade: str) -> int:
    try:
        return GRADE_ORDER.index(grade)
    except ValueError:
        return -1


def _score_case(case: Dict[str, Any], manifest_dir: Path, scores_dir: Path) -> Dict[str, Any]:
    transcript = (manifest_dir / case["transcript"]).resolve()
    return score.build_scorecard(
        skill_name=case["skill"],
        transcript_path=str(transcript),
        rubric_dir=str(RUBRICS_DIR),
        scores_dir=str(scores_dir),
        config_path=str(CONFIG_PATH) if CONFIG_PATH.is_file() else None,
        adapter=case.get("adapter"),
    )


def _check(case: Dict[str, Any], scorecard: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    composite = scorecard.get("composite_score", 0.0)
    grade = scorecard.get("grade", "F")

    if "expected_composite_min" in case:
        if composite < case["expected_composite_min"]:
            errors.append(
                f"composite {composite} < expected_min {case['expected_composite_min']}"
            )
    if "expected_composite_max" in case:
        if composite > case["expected_composite_max"]:
            errors.append(
                f"composite {composite} > expected_max {case['expected_composite_max']}"
            )
    if "expected_grade_min" in case:
        if _rank(grade) < _rank(case["expected_grade_min"]):
            errors.append(
                f"grade {grade} below expected_min {case['expected_grade_min']}"
            )
    for dim, minimum in case.get("expected_dimension_min", {}).items():
        actual = scorecard.get("dimensions", {}).get(dim, {}).get("score", 0)
        if actual < minimum:
            errors.append(f"dimension {dim}={actual} < expected_min {minimum}")
    for dim, maximum in case.get("expected_dimension_max", {}).items():
        actual = scorecard.get("dimensions", {}).get(dim, {}).get("score", 0)
        if actual > maximum:
            errors.append(f"dimension {dim}={actual} > expected_max {maximum}")

    return not errors, errors


def main(argv: List[str]) -> int:
    manifest_path = Path(argv[1]) if len(argv) > 1 else PROJECT_ROOT / "benchmarks" / "manifest.json"
    if not manifest_path.is_file():
        print(f"Error: manifest not found at {manifest_path}", file=sys.stderr)
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = manifest.get("cases", [])
    manifest_dir = manifest_path.parent

    with tempfile.TemporaryDirectory() as tmp:
        scores_dir = Path(tmp)
        all_ok = True
        print(f"Running {len(cases)} benchmark case(s)...")
        for case in cases:
            name = case.get("name", case.get("skill", "?"))
            try:
                card = _score_case(case, manifest_dir, scores_dir)
            except SystemExit:
                print(f"  ✗ {name}: scoring aborted")
                all_ok = False
                continue
            ok, errs = _check(case, card)
            composite = card.get("composite_score", 0.0)
            grade = card.get("grade", "F")
            if ok:
                print(f"  ✓ {name}: {composite}/{grade}")
            else:
                all_ok = False
                print(f"  ✗ {name}: {composite}/{grade} — {'; '.join(errs)}")
        return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
