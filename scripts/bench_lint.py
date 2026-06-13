#!/usr/bin/env python3
"""Benchmark task-hygiene lint for the Proofloop regression-gate corpus.

Adapts the Auto Benchmark Audit (ABA) framework (Wang et al. 2026,
arXiv:2605.26079, "Automated Benchmark Auditing for AI Agents and
Large Language Models", v1 2026-05-25) to Proofloop's transcript-
regression manifest. ABA was designed for *task* benchmarks with
ground-truth outputs; Proofloop's benchmark pack scores transcripts
against expected score bounds rather than tasks against expected
answers. The four ABA issue classes map by analogy:

    VBL001  SpecificationGap      -- missing name/skill, or no expected_*
                                     assertion of any kind (case asserts
                                     nothing about the score it produces)
    VBL002  EnvironmentCoupling   -- transcript path absolute, escapes the
                                     manifest dir via "..", missing on disk,
                                     or adapter/extension mismatch
    VBL003  BrittleGrading        -- single-point composite/grade/dim bounds
                                     (min == max), or composite range < 0.5
    VBL004  MissingGroundTruth    -- transcript file is 0-bytes or contains
                                     zero non-blank lines

Output: text (default), JSON (``--json``), or SARIF v2.1.0
(``--sarif PATH``). Aggregate ``bench_hygiene_score`` =
``1 - flagged_cases / total_cases``.

Exit codes:
    0  hygiene score >= threshold (default 0.85)
    1  hygiene score below threshold
    2  argument / IO error

Stdlib-only. No LLM call -- the offline heuristic is the moat.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MANIFEST = PROJECT_ROOT / "benchmarks" / "manifest.json"
DEFAULT_THRESHOLD = 0.85
TOOL_NAME = "verdict-bench-lint"
TOOL_VERSION = "2.0.3"
TOOL_URI = "https://github.com/sattyamjjain/proofloop"

# Adapter -> set of allowed file suffixes. Used by VBL002 to flag
# obvious mismatches such as adapter "openai-compatible" pointing at a
# .jsonl file. Suffixes match how the existing corpus is laid out.
ADAPTER_SUFFIXES: Dict[str, Tuple[str, ...]] = {
    "claude-code": (".jsonl",),
    "cowork": (".jsonl",),
    "codex": (".jsonl", ".json"),
    "openai-compatible": (".json",),
}

# Help text per rule -- echoed into SARIF rules[] and into text output.
RULES: Dict[str, Dict[str, str]] = {
    "VBL001": {
        "name": "SpecificationGap",
        "short": "Benchmark case lacks a clear spec or any score assertion.",
        "help": (
            "Each case should declare a non-empty 'name', a 'skill', "
            "and at least one expected_* bound. A case with no bounds "
            "asserts nothing -- it cannot detect a regression."
        ),
    },
    "VBL002": {
        "name": "EnvironmentCoupling",
        "short": "Transcript path leaks the host environment or is unreachable.",
        "help": (
            "Transcript paths should be relative to the manifest and "
            "stay inside the manifest directory. Absolute paths or "
            "paths escaping via '..' make the bench environment-coupled. "
            "Files must exist; declared adapter must match the suffix."
        ),
    },
    "VBL003": {
        "name": "BrittleGrading",
        "short": "Grading bound is so tight that any heuristic drift fails it.",
        "help": (
            "Single-point bounds (min == max) and ultra-narrow composite "
            "ranges (< 0.5) force exact-match grading where semantic match "
            "is needed. Prefer wider bounds anchored on the dimension that "
            "actually carries signal."
        ),
    },
    "VBL004": {
        "name": "MissingGroundTruth",
        "short": "Transcript file is empty -- there is nothing to score.",
        "help": (
            "A zero-byte transcript or one with only blank lines provides "
            "no ground truth for the scoring engine. Either delete the "
            "case or supply a real transcript."
        ),
    },
}


# ---------------------------------------------------------------------------
# Rule implementations
# ---------------------------------------------------------------------------

_EXPECTED_KEYS = (
    "expected_grade_min",
    "expected_grade_max",
    "expected_composite_min",
    "expected_composite_max",
    "expected_dimension_min",
    "expected_dimension_max",
)


def _has_any_expected(case: Dict[str, Any]) -> bool:
    """Return True if the case declares at least one expected_* bound."""
    return any(k in case for k in _EXPECTED_KEYS)


def _check_spec_gap(case: Dict[str, Any]) -> List[str]:
    """VBL001 -- specification gaps."""
    issues: List[str] = []
    name = (case.get("name") or "").strip()
    skill = (case.get("skill") or "").strip()
    if not name:
        issues.append("missing or empty 'name'")
    if not skill:
        issues.append("missing or empty 'skill'")
    if not _has_any_expected(case):
        issues.append("no expected_* bound declared (case asserts nothing)")
    return issues


def _check_env_coupling(
    case: Dict[str, Any], manifest_dir: Path
) -> Tuple[List[str], Optional[Path]]:
    """VBL002 -- environment coupling. Returns (issues, resolved_path)."""
    issues: List[str] = []
    raw = case.get("transcript")
    if not raw:
        issues.append("missing 'transcript'")
        return issues, None
    raw_path = Path(raw)
    if raw_path.is_absolute():
        issues.append(f"transcript path is absolute: {raw}")
    # Resolve and confirm it stays inside the manifest dir.
    try:
        resolved = (manifest_dir / raw_path).resolve()
        manifest_root = manifest_dir.resolve()
        # Path.is_relative_to is 3.9+, but commitment is 3.9+, so use it.
        if not resolved.is_relative_to(manifest_root):
            issues.append(
                f"transcript escapes manifest dir: {raw} -> {resolved}"
            )
    except (OSError, RuntimeError) as exc:
        issues.append(f"could not resolve transcript path: {exc}")
        return issues, None
    if not resolved.is_file():
        issues.append(f"transcript file does not exist: {resolved}")
    adapter = case.get("adapter")
    if adapter:
        allowed = ADAPTER_SUFFIXES.get(adapter)
        if allowed and resolved.suffix not in allowed:
            issues.append(
                f"adapter '{adapter}' does not match suffix '{resolved.suffix}' "
                f"(expected one of {list(allowed)})"
            )
    return issues, resolved


def _check_brittle_grading(case: Dict[str, Any]) -> List[str]:
    """VBL003 -- brittle / exact-match grading."""
    issues: List[str] = []
    cmin = case.get("expected_composite_min")
    cmax = case.get("expected_composite_max")
    if isinstance(cmin, (int, float)) and isinstance(cmax, (int, float)):
        if cmin == cmax:
            issues.append(
                f"composite bounds pin a single point ({cmin}); "
                f"any heuristic drift will fail this case"
            )
        elif (cmax - cmin) < 0.5:
            issues.append(
                f"composite range too narrow "
                f"({cmin} <= composite <= {cmax}, width={cmax - cmin:.2f})"
            )
    gmin = case.get("expected_grade_min")
    gmax = case.get("expected_grade_max")
    if isinstance(gmin, str) and isinstance(gmax, str) and gmin == gmax:
        issues.append(f"grade bounds pin a single letter ({gmin})")
    dmin = case.get("expected_dimension_min") or {}
    dmax = case.get("expected_dimension_max") or {}
    if isinstance(dmin, dict) and isinstance(dmax, dict):
        shared = set(dmin.keys()) & set(dmax.keys())
        for dim in sorted(shared):
            if dmin[dim] == dmax[dim]:
                issues.append(
                    f"dimension '{dim}' bounds pin a single value "
                    f"({dmin[dim]})"
                )
    return issues


def _check_missing_ground_truth(transcript: Optional[Path]) -> List[str]:
    """VBL004 -- missing or empty transcript."""
    if transcript is None or not transcript.is_file():
        # VBL002 already flagged this; don't double-flag here.
        return []
    issues: List[str] = []
    try:
        size = transcript.stat().st_size
    except OSError as exc:
        return [f"could not stat transcript: {exc}"]
    if size == 0:
        return ["transcript file is 0 bytes"]
    try:
        text = transcript.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [f"could not read transcript: {exc}"]
    non_blank = [ln for ln in text.splitlines() if ln.strip()]
    if not non_blank:
        issues.append("transcript has no non-blank lines")
    return issues


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def lint_case(
    case: Dict[str, Any], case_index: int, manifest_dir: Path
) -> List[Dict[str, Any]]:
    """Run all four hygiene checks against a single case.

    Returns a list of finding dicts (possibly empty). Each finding has
    ``case_index``, ``case_name``, ``rule_id``, ``rule_name``,
    ``severity``, and ``message`` keys.
    """
    findings: List[Dict[str, Any]] = []
    name = (case.get("name") or f"<case #{case_index}>").strip() or f"<case #{case_index}>"

    def _emit(rule_id: str, msg: str) -> None:
        findings.append(
            {
                "case_index": case_index,
                "case_name": name,
                "rule_id": rule_id,
                "rule_name": RULES[rule_id]["name"],
                "severity": "warning",
                "message": msg,
            }
        )

    for msg in _check_spec_gap(case):
        _emit("VBL001", msg)
    env_issues, resolved = _check_env_coupling(case, manifest_dir)
    for msg in env_issues:
        _emit("VBL002", msg)
    for msg in _check_brittle_grading(case):
        _emit("VBL003", msg)
    for msg in _check_missing_ground_truth(resolved):
        _emit("VBL004", msg)
    return findings


def lint_manifest(manifest_path: Path) -> Dict[str, Any]:
    """Lint every case in the manifest and return an aggregate report.

    Report shape:
        {
          "manifest": "<path>",
          "total_cases": int,
          "flagged_cases": int,
          "bench_hygiene_score": float,   # 0.0 - 1.0
          "findings": [ {case_index, case_name, rule_id, ...}, ... ]
        }
    """
    text = manifest_path.read_text(encoding="utf-8")
    manifest = json.loads(text)
    cases = manifest.get("cases", []) or []
    manifest_dir = manifest_path.parent
    all_findings: List[Dict[str, Any]] = []
    flagged_indices: set = set()
    for idx, case in enumerate(cases):
        case_findings = lint_case(case, idx, manifest_dir)
        if case_findings:
            flagged_indices.add(idx)
        all_findings.extend(case_findings)
    total = len(cases)
    flagged = len(flagged_indices)
    score = 1.0 if total == 0 else 1.0 - (flagged / total)
    return {
        "manifest": str(manifest_path),
        "total_cases": total,
        "flagged_cases": flagged,
        "bench_hygiene_score": round(score, 4),
        "findings": all_findings,
    }


# ---------------------------------------------------------------------------
# Output renderers
# ---------------------------------------------------------------------------


def render_text(report: Dict[str, Any], threshold: float) -> str:
    """Render a Unicode-box text report matching the project's house style."""
    width = 70

    def row(s: str) -> str:
        # Truncate if too long, pad otherwise.
        s = s[:width] if len(s) > width else s
        return "│" + s.ljust(width) + "│"

    lines: List[str] = []
    score = report["bench_hygiene_score"]
    total = report["total_cases"]
    flagged = report["flagged_cases"]
    verdict = "PASS" if score >= threshold else "FAIL"
    lines.append("┌" + "─" * width + "┐")
    lines.append(row("  PROOFLOOP BENCH-LINT (ABA-anchored, arXiv:2605.26079)"))
    lines.append("├" + "─" * width + "┤")
    lines.append(row(f"  Manifest: {Path(report['manifest']).name}"))
    lines.append(row(f"  Cases:    {total} total, {flagged} flagged"))
    lines.append(
        row(
            f"  Score:    bench_hygiene_score = {score:.4f}  "
            f"(threshold {threshold:.2f}) -> {verdict}"
        )
    )
    lines.append("└" + "─" * width + "┘")
    if report["findings"]:
        lines.append("")
        lines.append("Findings:")
        last_case = None
        for f in report["findings"]:
            if f["case_name"] != last_case:
                lines.append(f"  [{f['case_name']}]")
                last_case = f["case_name"]
            lines.append(
                f"    {f['rule_id']} {f['rule_name']}: {f['message']}"
            )
    return "\n".join(lines)


def to_sarif(report: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a report to a SARIF v2.1.0 log."""
    manifest_uri = Path(report["manifest"]).name
    rules = []
    for rid, meta in sorted(RULES.items()):
        rules.append(
            {
                "id": rid,
                "name": meta["name"],
                "shortDescription": {"text": meta["short"]},
                "fullDescription": {"text": meta["help"]},
                "helpUri": TOOL_URI,
                "defaultConfiguration": {"level": "warning"},
            }
        )
    results = []
    for f in report["findings"]:
        results.append(
            {
                "ruleId": f["rule_id"],
                "level": f["severity"],
                "message": {
                    "text": f"[{f['case_name']}] {f['message']}"
                },
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": manifest_uri},
                        },
                        "logicalLocations": [
                            {
                                "name": f["case_name"],
                                "kind": "object",
                                "fullyQualifiedName": f"cases[{f['case_index']}]",
                            }
                        ],
                    }
                ],
                "properties": {
                    "bench_hygiene_score": report["bench_hygiene_score"],
                },
            }
        )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": TOOL_NAME,
                        "version": TOOL_VERSION,
                        "informationUri": TOOL_URI,
                        "rules": rules,
                    }
                },
                "results": results,
                "properties": {
                    "manifest": report["manifest"],
                    "total_cases": report["total_cases"],
                    "flagged_cases": report["flagged_cases"],
                    "bench_hygiene_score": report["bench_hygiene_score"],
                },
            }
        ],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: List[str]) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        prog="bench_lint",
        description=(
            "ABA-anchored task-hygiene lint for Proofloop's benchmark pack. "
            "Offline, stdlib-only, no LLM call."
        ),
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        default=str(DEFAULT_MANIFEST),
        help="Path to manifest.json (default: benchmarks/manifest.json)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"Pass bench_hygiene_score (default {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--json",
        dest="emit_json",
        action="store_true",
        help="Emit the full report as JSON to stdout instead of text.",
    )
    parser.add_argument(
        "--sarif",
        metavar="PATH",
        help="Write SARIF v2.1.0 output to PATH (text summary still printed).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress text output (useful in CI when --sarif is set).",
    )
    return parser.parse_args(argv[1:])


def main(argv: List[str]) -> int:
    """Run the lint and return an exit code."""
    args = parse_args(argv)
    manifest_path = Path(args.manifest)
    if not manifest_path.is_file():
        print(f"Error: manifest not found at {manifest_path}", file=sys.stderr)
        return 2
    try:
        report = lint_manifest(manifest_path)
    except json.JSONDecodeError as exc:
        print(f"Error: manifest is not valid JSON: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Error: could not read manifest: {exc}", file=sys.stderr)
        return 2

    if args.sarif:
        sarif = to_sarif(report)
        try:
            Path(args.sarif).write_text(
                json.dumps(sarif, indent=2) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            print(f"Error: could not write SARIF to {args.sarif}: {exc}", file=sys.stderr)
            return 2

    if args.emit_json:
        print(json.dumps(report, indent=2))
    elif not args.quiet:
        print(render_text(report, args.threshold))

    return 0 if report["bench_hygiene_score"] >= args.threshold else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
