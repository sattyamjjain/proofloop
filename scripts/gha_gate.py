#!/usr/bin/env python3
"""Emit a Proofloop scorecard result for GitHub Actions and gate on a threshold.

Reads the newest scorecard JSON from ``--scores-dir`` (as written by
``skills/judge/scripts/score.py``), prints a one-line summary, appends
``composite`` and ``grade`` to ``$GITHUB_OUTPUT`` when that env var is set,
and exits non-zero when a ``--threshold`` is given and the composite falls
below it. Stdlib only; powers the repo-root ``action.yml`` composite action.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------


def _newest_scorecard(scores_dir: str) -> Optional[Path]:
    """Return the most recently written ``*.json`` scorecard, or None."""
    files = sorted(Path(p) for p in glob.glob(os.path.join(scores_dir, "*.json")))
    return files[-1] if files else None


def _write_output(composite: object, grade: str) -> None:
    """Append ``composite``/``grade`` to the GitHub Actions output file."""
    gh_out = os.environ.get("GITHUB_OUTPUT")
    if not gh_out:
        return
    with open(gh_out, "a", encoding="utf-8") as fh:
        fh.write(f"composite={composite}\ngrade={grade}\n")


# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(prog="proofloop-gha-gate")
    parser.add_argument("--scores-dir", required=True, help="Directory score.py wrote to.")
    parser.add_argument(
        "--threshold",
        default="",
        help="Fail (exit 1) when the composite is below this value (1-10). Empty = report only.",
    )
    return parser.parse_args()


def main() -> int:
    """Render the result, export outputs, and enforce the optional gate."""
    args = parse_args()
    card_path = _newest_scorecard(args.scores_dir)
    if card_path is None:
        print("::error::Proofloop produced no scorecard", file=sys.stderr)
        return 1

    card = json.loads(card_path.read_text())
    composite = card.get("composite_score")
    grade = card.get("grade", "")
    one_liner = card.get("one_liner", "")
    print(f"Proofloop: {card.get('skill', '?')} -> {composite}/10 ({grade}) — {one_liner}")

    _write_output(composite, grade)

    threshold = str(args.threshold).strip()
    if threshold:
        try:
            if float(composite) < float(threshold):
                print(
                    f"::error::Proofloop composite {composite} is below threshold {threshold}",
                    file=sys.stderr,
                )
                return 1
        except (TypeError, ValueError):
            print(f"::warning::invalid threshold {threshold!r}; skipping gate", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
