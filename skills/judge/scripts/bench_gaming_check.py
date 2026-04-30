#!/usr/bin/env python3
"""verdict bench gaming-check — pre-publication benchmark-gaming linter.

Thin user-facing wrapper around the Berkeley RDI signature detector
(``benchmark_gaming_detector.py``). Intended to be invoked by
anyone publishing a SWE-bench / Terminal-Bench / browser-agent
benchmark result *before* they post the number — verifying that
the trajectory doesn't trip any of the published exploit
signatures.

Returns:

- ``0`` — clean. No exploit signatures matched.
- ``1`` — at least one exploit signature matched (or, with
  ``--strict``, the trajectory was suspiciously short).
- ``2`` — bad input.

``--strict`` mode adds a "minimum reasoning turns" floor (default
3): a benchmark whose stated solution requires multi-step work
shouldn't have a one-line trajectory.

Usage::

    python3 skills/judge/scripts/bench_gaming_check.py \\
        --transcript path/to/run.jsonl \\
        --benchmark swe-bench-pro \\
        --strict

Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

import benchmark_gaming_detector as bgd  # type: ignore[import-not-found]

DEFAULT_STRICT_MIN_TURNS: int = 3


def _load_lines(path: Path) -> List[str]:
    raw = path.read_text(encoding="utf-8").splitlines()
    out: List[str] = []
    for line in raw:
        stripped = line.strip()
        if not stripped:
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            out.append(stripped)
            continue
        if isinstance(record, dict):
            content = record.get("content")
            if isinstance(content, str):
                out.append(content)
                continue
        out.append(stripped)
    return out


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="bench_gaming_check",
        description=(
            "Lint a benchmark transcript for Berkeley RDI exploit "
            "signatures. Returns 0 on clean; 1 on exploit / short "
            "trajectory in --strict; 2 on bad input."
        ),
    )
    parser.add_argument("--transcript", required=True, help="Path to the JSONL transcript.")
    parser.add_argument("--benchmark", required=True, help="Benchmark name.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "In strict mode, fail on suspiciously short trajectories "
            f"(< {DEFAULT_STRICT_MIN_TURNS} reasoning turns)."
        ),
    )
    parser.add_argument(
        "--strict-min-turns",
        type=int,
        default=DEFAULT_STRICT_MIN_TURNS,
        help=f"Reasoning-turn floor for --strict (default {DEFAULT_STRICT_MIN_TURNS}).",
    )
    parser.add_argument("--output", choices=("text", "json"), default="text")
    parser.add_argument(
        "--signature-pack",
        default=bgd.DEFAULT_SIGNATURE_PACK,
        help="Signature pack name under signatures/.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    path = Path(args.transcript)
    if not path.is_file():
        print(
            f"bench_gaming_check: transcript not found: {path}",
            file=sys.stderr,
        )
        return 2
    pack = bgd.load_signature_pack(args.signature_pack)
    lines = _load_lines(path)
    findings = bgd.scan_transcript(lines, args.benchmark, pack)
    if args.strict:
        turns = bgd._count_reasoning_turns(lines)
        if turns < args.strict_min_turns:
            findings["exploits"].append({
                "exploit_class": "strict-min-turns",
                "confidence": 0.6,
                "evidence_span": [
                    0,
                    f"only {turns} reasoning turn(s); strict floor {args.strict_min_turns}",
                ],
            })
    if args.output == "json":
        print(json.dumps(findings, indent=2))
    else:
        if not findings["exploits"]:
            print(
                f"clean — {args.transcript} did not trip any "
                f"signatures from {findings['signature_pack']} "
                f"for benchmark={args.benchmark}."
            )
        else:
            print(
                f"FAIL — {len(findings['exploits'])} signature(s) tripped:"
            )
            for hit in findings["exploits"]:
                print(
                    f"  - {hit['exploit_class']} "
                    f"(confidence={hit['confidence']:.2f}); "
                    f"line {hit['evidence_span'][0]}: {hit['evidence_span'][1]}"
                )
    return 0 if not findings["exploits"] else 1


if __name__ == "__main__":
    sys.exit(main())
