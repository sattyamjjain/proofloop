#!/usr/bin/env python3
"""Berkeley RDI benchmark-gaming detector.

Pure-stdlib detector that scans agent transcripts for the exploit
signatures published in
https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/
("How We Broke Top AI Agent Benchmarks", 2026-04-26).

The Berkeley RDI audit covered SWE-bench, WebArena, OSWorld, GAIA,
Terminal-Bench, FieldWorkArena, and CAR-bench. Their automated
scanning agent achieved near-perfect scores on every one without
solving a single task — by exploiting harness-level trust
boundaries rather than the underlying problem. The signatures
they published live in
``signatures/berkeley-rdi-2026-04-26.json`` next to this script.

Returns per-exploit findings keyed on:
- ``exploit_class``: signature label (e.g.,
  ``harness-trust-pytest-self-report``)
- ``confidence``: 0.0-1.0 from the signature pack
- ``evidence_span``: (line_index, snippet) tuple

See Issue O14 for signature drift; v1.4.3 will add a
``--signatures-from <url>`` flag so signature packs can be
refreshed without a Verdict release.

Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_SIGNATURE_PACK = "berkeley-rdi-2026-04-26"
SIGNATURES_DIR = Path(__file__).resolve().parent / "signatures"


def load_signature_pack(name: str = DEFAULT_SIGNATURE_PACK) -> Dict[str, Any]:
    """Load a signature pack JSON file from ``signatures/<name>.json``.

    Returns an empty pack ``{"signature_pack": name, "exploits": []}``
    when the file is missing or malformed. Callers should not crash
    on signature-pack failures — log + degrade.
    """
    path = SIGNATURES_DIR / f"{name}.json"
    if not path.is_file():
        return {"signature_pack": name, "exploits": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"signature_pack": name, "exploits": []}
    if not isinstance(data, dict):
        return {"signature_pack": name, "exploits": []}
    return data


def _count_reasoning_turns(transcript_lines: List[str]) -> int:
    """Heuristic count of reasoning turns.

    A "reasoning turn" is any line that:
    - has more than 30 non-whitespace characters,
    - is not a bare tag (starts with ``[`` and ends with ``]``),
    - is not a shell-only line (starts with ``echo``, ``$``, ``>``,
      ``cat``, ``tee``, ``sed``, etc.) — those are exploit-shaped,
      not reasoning,
    - and is not raw JSON.

    Tuned against the ``swe-bench-gaming-trace`` fixture so a clean
    multi-turn transcript counts ≥ 3 turns and a one-shot exploit
    counts 0.
    """
    shell_only_starts = (
        "echo ", "echo\t", "$ ", "> ", "cat ", "tee ", "sed ", "awk ",
        "rm ", "mv ", "cp ", "chmod ", "chown ", "exit ",
    )
    n = 0
    for line in transcript_lines:
        stripped = line.strip()
        if len(stripped) <= 30:
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            continue
        if stripped.startswith("{") or stripped.startswith('"'):
            continue
        lowered = stripped.lower()
        if any(lowered.startswith(prefix) for prefix in shell_only_starts):
            continue
        n += 1
    return n


def scan_transcript(
    transcript_lines: List[str],
    benchmark_name: str,
    signature_pack: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Scan a transcript for benchmark-gaming exploit signatures.

    Returns a dict with ``signature_pack`` and ``exploits`` (list of
    findings). Each finding carries ``exploit_class``, ``confidence``,
    and ``evidence_span``.
    """
    pack = signature_pack or load_signature_pack()
    findings: List[Dict[str, Any]] = []
    full_text = "\n".join(transcript_lines)
    for exploit in pack.get("exploits", []):
        applies = exploit.get("applies_to") or []
        if applies and benchmark_name not in applies:
            continue
        klass = exploit.get("exploit_class", "unknown")
        confidence = float(exploit.get("confidence_default", 0.5))
        # Pattern-based detection.
        for pattern_str in exploit.get("patterns", []):
            try:
                pattern = re.compile(pattern_str, re.IGNORECASE | re.MULTILINE)
            except re.error:
                continue
            for match in pattern.finditer(full_text):
                snippet = match.group(0)
                # Find the line index for the match start.
                line_index = full_text.count("\n", 0, match.start())
                findings.append({
                    "exploit_class": klass,
                    "confidence": confidence,
                    "evidence_span": [line_index, snippet[:120]],
                })
                # One finding per pattern is enough; keep iterating
                # other patterns within the same exploit class.
                break
        # Trajectory-length floor (short-circuit detection).
        min_turns = exploit.get("min_reasoning_turns")
        if isinstance(min_turns, int):
            actual = _count_reasoning_turns(transcript_lines)
            if actual < min_turns:
                findings.append({
                    "exploit_class": klass,
                    "confidence": confidence,
                    "evidence_span": [
                        0,
                        f"only {actual} reasoning turn(s); minimum {min_turns}",
                    ],
                })
        # Suspiciously-short total length.
        min_len = exploit.get("min_short_circuit_length")
        if isinstance(min_len, int) and len(full_text.strip()) < min_len:
            # Already covered by min_reasoning_turns when present;
            # only add a new finding if the patterns block would
            # have missed this on its own.
            pass
    # Deduplicate by exploit_class — a single class produces at most
    # one finding per scan (otherwise a trivial transcript with two
    # PASSED-shaped lines double-counts).
    seen: Dict[str, Dict[str, Any]] = {}
    for f in findings:
        klass = f["exploit_class"]
        if klass not in seen or f["confidence"] > seen[klass]["confidence"]:
            seen[klass] = f
    deduped = list(seen.values())
    return {
        "signature_pack": pack.get("signature_pack", DEFAULT_SIGNATURE_PACK),
        "benchmark": benchmark_name,
        "exploits": deduped,
    }


# ---------------------------------------------------------------------------
# CLI (informational; T2's bench_gaming_check.py is the user-facing wrapper)
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="benchmark_gaming_detector",
        description=(
            "Scan an agent transcript for Berkeley RDI exploit signatures."
        ),
    )
    parser.add_argument(
        "--transcript",
        required=True,
        help="Path to the JSONL transcript.",
    )
    parser.add_argument(
        "--benchmark",
        required=True,
        help="Benchmark name (swe-bench-pro, terminal-bench, browser-agent).",
    )
    parser.add_argument(
        "--signature-pack",
        default=DEFAULT_SIGNATURE_PACK,
        help="Signature-pack name (no path; resolved under signatures/).",
    )
    parser.add_argument(
        "--output",
        choices=("text", "json"),
        default="text",
    )
    return parser.parse_args(argv)


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


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    path = Path(args.transcript)
    if not path.is_file():
        print(
            f"benchmark_gaming_detector: transcript not found: {path}",
            file=sys.stderr,
        )
        return 2
    pack = load_signature_pack(args.signature_pack)
    lines = _load_lines(path)
    findings = scan_transcript(lines, args.benchmark, pack)
    if args.output == "json":
        print(json.dumps(findings, indent=2))
    else:
        if not findings["exploits"]:
            print(f"clean — no signatures from {findings['signature_pack']} matched.")
        else:
            print(
                f"FAIL — {len(findings['exploits'])} exploit signature(s) matched:"
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
