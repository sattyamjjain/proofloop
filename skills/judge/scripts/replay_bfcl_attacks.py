#!/usr/bin/env python3
"""Function-hijacking attack-vector replay harness (offline-fixture mode).

The function-hijacking-robustness rubric (AA3) needs a numeric
attack-success rate (ASR) for its Efficiency dimension. This script
replays attack outcomes recorded in a fixture file and aggregates
the ASR.

**Modes:**

- ``--mode=offline-fixture`` (default) — reads pre-recorded
  ``{attack_pattern, agent_response, attack_succeeded}`` triples
  from a JSONL fixture. Produces a deterministic ASR for CI without
  LLM access. This is the **only** mode v1 implements (see Issue
  O5 for the live-replay rationale).
- ``--mode=live-replay`` — reserved for v1.4.x. Raises
  ``NotImplementedError`` in v1; intended to drive a callable agent
  through the attack patterns, requires CI secrets + opt-in.

**Stdlib only.** No network, no LLM call.

Usage:

    python3 skills/judge/scripts/replay_bfcl_attacks.py \\
        --fixture tests/fixtures/bfcl-attack-vectors.jsonl \\
        [--mode offline-fixture] \\
        [--out PATH]

Writes to stdout when ``--out`` is omitted; the format is a JSON
object with ``asr``, ``attack_count``, ``succeeded``, ``failed``,
and a per-pattern breakdown.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_fixture(path: Path) -> List[Dict[str, Any]]:
    """Load a JSONL fixture into a list of dicts. Skips malformed lines."""
    if not path.is_file():
        raise FileNotFoundError(f"fixture not found: {path}")
    out: List[Dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            out.append(record)
    return out


def aggregate_offline(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute ASR + per-pattern breakdown from fixture records."""
    total = len(records)
    if total == 0:
        return {
            "asr": 0.0,
            "attack_count": 0,
            "succeeded": 0,
            "failed": 0,
            "per_pattern": {},
        }
    succeeded = sum(1 for r in records if r.get("attack_succeeded") is True)
    per_pattern: Dict[str, Dict[str, int]] = {}
    for record in records:
        pattern = str(record.get("attack_pattern", "unknown"))
        slot = per_pattern.setdefault(
            pattern, {"count": 0, "succeeded": 0, "failed": 0}
        )
        slot["count"] += 1
        if record.get("attack_succeeded") is True:
            slot["succeeded"] += 1
        else:
            slot["failed"] += 1
    return {
        "asr": round(succeeded / total, 4),
        "attack_count": total,
        "succeeded": succeeded,
        "failed": total - succeeded,
        "per_pattern": per_pattern,
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="verdict-replay-bfcl-attacks")
    parser.add_argument(
        "--fixture", required=True,
        help="JSONL fixture of attack outcomes (offline-fixture mode).",
    )
    parser.add_argument(
        "--mode", choices=("offline-fixture", "live-replay"),
        default="offline-fixture",
        help="Replay mode. v1 only implements offline-fixture.",
    )
    parser.add_argument(
        "--out",
        help="Write JSON output to PATH. Default: stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    if args.mode == "live-replay":
        print(
            "[verdict] live-replay mode is reserved for v1.4.x. "
            "Use --mode=offline-fixture in v1; see Issue O5.",
            file=sys.stderr,
        )
        return 2
    try:
        records = load_fixture(Path(args.fixture))
    except FileNotFoundError as exc:
        print(f"verdict-replay-bfcl-attacks: {exc}", file=sys.stderr)
        return 2
    summary = aggregate_offline(records)
    rendered = json.dumps(summary, indent=2)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
