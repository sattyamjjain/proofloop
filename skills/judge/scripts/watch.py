#!/usr/bin/env python3
"""Live re-scoring daemon.

Polls ``skills/judge/scores/`` (or any directory) every ``interval``
seconds via ``os.stat``. When a scorecard's mtime changes:

1. Re-read the scorecard JSON.
2. Compare each dimension against the previous snapshot.
3. Emit a single-line diff header + re-render Proofloop Studio to
   ``--output``.

Stdlib-only. No file-system watcher dep, no server loop, no threads
beyond the main one. Exits on SIGINT.

Usage:
    python3 skills/judge/scripts/watch.py \\
      --scores-dir skills/judge/scores \\
      --output proofloop-studio.html \\
      [--interval 2.0] [--once]

The ``--once`` flag runs a single pass (used by tests); omit it to
poll until Ctrl-C.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
import studio  # noqa: E402

# Seven dimensions Proofloop actually tracks.
DIMENSIONS: List[str] = [
    "correctness", "completeness", "adherence", "actionability",
    "efficiency", "safety", "consistency",
]


def _load_scorecards(scores_dir: Path) -> Dict[Path, Dict[str, Any]]:
    """Return every valid scorecard in ``scores_dir`` keyed by path."""
    out: Dict[Path, Dict[str, Any]] = {}
    if not scores_dir.is_dir():
        return out
    for path in sorted(scores_dir.glob("*.json")):
        try:
            out[path] = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def _mtime_map(scores_dir: Path) -> Dict[Path, float]:
    if not scores_dir.is_dir():
        return {}
    return {p: p.stat().st_mtime for p in scores_dir.glob("*.json")}


def _dimension_score(card: Dict[str, Any], dim: str) -> Optional[int]:
    """Extract an int dimension score or ``None`` if missing/malformed."""
    entry = card.get("dimensions", {}).get(dim)
    if not isinstance(entry, dict):
        return None
    value = entry.get("score")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def diff_scorecards(
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
) -> Tuple[int, int, int]:
    """Return ``(improved, regressed, unchanged)`` dimension counts."""
    if previous is None:
        return 0, 0, len(DIMENSIONS)
    improved = regressed = unchanged = 0
    for dim in DIMENSIONS:
        prev = _dimension_score(previous, dim)
        curr = _dimension_score(current, dim)
        if prev is None or curr is None:
            unchanged += 1
            continue
        if curr > prev:
            improved += 1
        elif curr < prev:
            regressed += 1
        else:
            unchanged += 1
    return improved, regressed, unchanged


def format_diff_header(
    skill: str,
    previous: Optional[Dict[str, Any]],
    current: Dict[str, Any],
) -> str:
    """Render the human-readable diff header printed on each change."""
    improved, regressed, unchanged = diff_scorecards(previous, current)
    prev_comp = previous.get("composite_score") if previous else None
    curr_comp = current.get("composite_score", 0.0)
    if prev_comp is None:
        delta_str = f"composite {curr_comp:.2f} (first run)"
    else:
        delta = curr_comp - prev_comp
        arrow = "↑" if delta > 0.05 else ("↓" if delta < -0.05 else "→")
        delta_str = f"composite {prev_comp:.2f} {arrow} {curr_comp:.2f} ({delta:+.2f})"
    return (
        f"[watch] {skill}: improved {improved}, regressed {regressed}, "
        f"unchanged {unchanged} since last run — {delta_str}"
    )


def run_pass(
    scores_dir: Path,
    output: Path,
    previous_snapshot: Dict[Path, Dict[str, Any]],
    generated_at: str,
) -> Tuple[Dict[Path, Dict[str, Any]], List[str]]:
    """Detect changed scorecards, emit diff headers, re-render Studio.

    Returns (new_snapshot, headers_emitted).
    """
    current_snapshot = _load_scorecards(scores_dir)
    headers: List[str] = []
    for path, card in current_snapshot.items():
        prev = previous_snapshot.get(path)
        if prev == card:
            continue
        skill = card.get("skill", path.stem)
        header = format_diff_header(skill, prev, card)
        headers.append(header)
    # Also note any file that vanished between passes.
    for path in sorted(set(previous_snapshot) - set(current_snapshot)):
        headers.append(f"[watch] removed: {path.name}")

    if headers:
        studio.generate(scores_dir, output, generated_at)
    return current_snapshot, headers


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="proofloop-watch")
    parser.add_argument(
        "--scores-dir", required=True,
        help="Directory of persisted scorecard JSON files to watch.",
    )
    parser.add_argument(
        "--output", required=True,
        help="Path to the Studio HTML file to re-render on every change.",
    )
    parser.add_argument(
        "--interval", type=float, default=2.0,
        help="Seconds between polls (default: 2.0). Minimum enforced: 0.05.",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Run a single pass and exit (used by tests).",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress diff headers on stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    from datetime import datetime, timezone
    args = parse_args(argv)
    scores_dir = Path(args.scores_dir)
    output = Path(args.output)
    interval = max(0.05, float(args.interval))

    def _now() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    previous_snapshot = _load_scorecards(scores_dir)
    previous_mtimes = _mtime_map(scores_dir)
    # Emit the initial Studio render so --output always exists after the
    # first pass, even if nothing has changed yet.
    studio.generate(scores_dir, output, _now())
    if not args.quiet:
        print(f"[watch] tracking {scores_dir} → {output} (every {interval:.2f}s)")

    if args.once:
        _snapshot, headers = run_pass(scores_dir, output, previous_snapshot, _now())
        if not args.quiet:
            for header in headers:
                print(header)
        return 0

    try:
        while True:
            time.sleep(interval)
            current_mtimes = _mtime_map(scores_dir)
            if current_mtimes == previous_mtimes:
                continue
            previous_mtimes = current_mtimes
            previous_snapshot, headers = run_pass(
                scores_dir, output, previous_snapshot, _now(),
            )
            if not args.quiet:
                for header in headers:
                    print(header)
    except KeyboardInterrupt:
        if not args.quiet:
            print("[watch] stopped")
        return 0


if __name__ == "__main__":
    sys.exit(main())
