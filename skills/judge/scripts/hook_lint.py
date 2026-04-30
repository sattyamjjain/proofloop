#!/usr/bin/env python3
"""verdict hook lint — static analyzer for PostToolUse hook scripts.

Lints a hook script (``.sh`` / ``.py`` / ``.js``) that targets the
Claude Code v2.1.121 ``PostToolUse`` lifecycle and may emit
``hookSpecificOutput.updatedToolOutput``. Pairs with the CC1
``tool-output-rewrite`` rubric — the rubric scores transcripts on
the *output* shape; this lint scores the *hook source* on whether
it produces that shape.

Findings:

- **F1 — undisclosed-mutation** — the hook writes
  ``updatedToolOutput`` but never emits a ``[hook-rewrote: <tool>]``
  marker. Adopters running the CC1 rubric will fail their
  transcripts.
- **F2 — missing-source-tag** — the hook emits
  ``[hook-rewrote: ...]`` but no ``[hook-source: <path>]`` so the
  CC1 audit-link dimension caps at ≤ 5.0.
- **F3 — error-suppression-without-justification** — the hook
  flips ``error: true`` → ``error: false`` without an
  ``[error-suppressed-by-design: <reason>]`` marker.
- **F4 — credential-leak-in-output** — the hook embeds a literal
  secret-shaped string in the rewritten output (defensive; rare
  but high-severity).

Returns:

- ``0`` — clean.
- ``1`` — at least one finding.
- ``2`` — bad input (missing file, unsupported extension).

Stdlib-only.

Usage::

    python3 skills/judge/scripts/hook_lint.py path/to/hook.sh
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SUPPORTED_EXTS = frozenset({".sh", ".bash", ".py", ".js", ".mjs", ".ts"})

_UPDATED_TOOL_OUTPUT_RE = re.compile(
    r"updatedToolOutput", re.IGNORECASE,
)
_HOOK_REWROTE_RE = re.compile(
    r"\[hook-rewrote:", re.IGNORECASE,
)
_HOOK_SOURCE_RE = re.compile(
    r"\[hook-source:", re.IGNORECASE,
)
_ERROR_TRUE_RE = re.compile(r'"?error"?\s*:\s*true', re.IGNORECASE)
_ERROR_FALSE_RE = re.compile(r'"?error"?\s*:\s*false', re.IGNORECASE)
_ERROR_SUPPRESSED_RE = re.compile(
    r"\[error-suppressed-by-design", re.IGNORECASE,
)
_SECRET_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
]


def _has_any(text: str, pattern: re.Pattern) -> bool:
    return bool(pattern.search(text))


def _strip_comments(source: str) -> str:
    """Strip comment-only lines so signals in commentary don't confuse lint.

    Handles ``#``, ``//``, and shebang lines. Doesn't try to handle
    inline trailing comments — flagging is meant to be conservative.
    """
    out: List[str] = []
    for raw in source.splitlines():
        stripped = raw.lstrip()
        if stripped.startswith("#") or stripped.startswith("//"):
            out.append("")  # preserve line numbers
            continue
        out.append(raw)
    return "\n".join(out)


def lint_source(source: str) -> List[Dict[str, Any]]:
    """Lint a hook source string. Returns a list of findings.

    Each finding is ``{"rule_id", "line", "snippet", "message"}``.
    Pure function — no I/O.
    """
    code = _strip_comments(source)
    findings: List[Dict[str, Any]] = []
    has_updated = _has_any(code, _UPDATED_TOOL_OUTPUT_RE)
    has_rewrote = _has_any(code, _HOOK_REWROTE_RE)
    has_source = _has_any(code, _HOOK_SOURCE_RE)
    has_err_true = _has_any(code, _ERROR_TRUE_RE)
    has_err_false = _has_any(code, _ERROR_FALSE_RE)
    has_err_suppressed = _has_any(code, _ERROR_SUPPRESSED_RE)

    # F1 — undisclosed mutation (mutates output but never tags it).
    if has_updated and not has_rewrote:
        # Find the first updatedToolOutput line for evidence.
        for idx, line in enumerate(code.splitlines(), start=1):
            if _UPDATED_TOOL_OUTPUT_RE.search(line):
                findings.append({
                    "rule_id": "F1",
                    "line": idx,
                    "snippet": line.strip()[:120],
                    "message": (
                        "hook writes updatedToolOutput but never emits a "
                        "[hook-rewrote: <tool>] disclosure marker. CC1 "
                        "rubric will flag transcripts as undisclosed."
                    ),
                })
                break

    # F2 — missing source tag (discloses but doesn't link to source).
    if has_rewrote and not has_source:
        for idx, line in enumerate(code.splitlines(), start=1):
            if _HOOK_REWROTE_RE.search(line):
                findings.append({
                    "rule_id": "F2",
                    "line": idx,
                    "snippet": line.strip()[:120],
                    "message": (
                        "hook discloses rewrites but never emits "
                        "[hook-source: <path>]. CC1 audit-link "
                        "dimension caps at <= 5.0."
                    ),
                })
                break

    # F3 — error suppression without justification.
    if has_err_true and has_err_false and not has_err_suppressed:
        for idx, line in enumerate(code.splitlines(), start=1):
            if _ERROR_FALSE_RE.search(line):
                findings.append({
                    "rule_id": "F3",
                    "line": idx,
                    "snippet": line.strip()[:120],
                    "message": (
                        "hook flips error:true -> error:false without an "
                        "[error-suppressed-by-design: <reason>] marker. "
                        "CC1 rubber-stamp red flag will fire."
                    ),
                })
                break

    # F4 — literal credential in source (defensive).
    for pattern in _SECRET_PATTERNS:
        for idx, line in enumerate(code.splitlines(), start=1):
            match = pattern.search(line)
            if match:
                findings.append({
                    "rule_id": "F4",
                    "line": idx,
                    "snippet": "<<credential redacted>>",
                    "message": (
                        f"hook source contains a credential-shaped literal "
                        f"({pattern.pattern!r}); rewrite output may inject "
                        "credentials at runtime."
                    ),
                })
                break
    return findings


def lint_file(path: Path) -> Tuple[int, List[Dict[str, Any]]]:
    """Lint a hook file. Returns ``(rc, findings)``.

    ``rc`` is 0 on clean, 1 on findings, 2 on bad input.
    """
    if not path.is_file():
        return 2, [{
            "rule_id": "E1",
            "line": 0,
            "snippet": "",
            "message": f"file not found: {path}",
        }]
    if path.suffix.lower() not in SUPPORTED_EXTS:
        return 2, [{
            "rule_id": "E2",
            "line": 0,
            "snippet": "",
            "message": (
                f"unsupported extension {path.suffix!r}; "
                f"supported: {sorted(SUPPORTED_EXTS)}"
            ),
        }]
    source = path.read_text(encoding="utf-8")
    findings = lint_source(source)
    return (1 if findings else 0), findings


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="hook_lint",
        description=(
            "Lint a Claude Code PostToolUse hook script for "
            "tool-output-rewrite hygiene (CC1)."
        ),
    )
    parser.add_argument("hook_path", help="Path to the hook script.")
    parser.add_argument("--output", choices=("text", "json"), default="text")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    path = Path(args.hook_path)
    rc, findings = lint_file(path)
    if rc == 2:
        for f in findings:
            print(f"hook_lint: {f['message']}", file=sys.stderr)
        return rc
    if args.output == "json":
        import json as _json
        print(_json.dumps({"path": str(path), "findings": findings}, indent=2))
    else:
        if not findings:
            print(f"clean — {path} passes CC1 hook-lint.")
        else:
            print(f"FAIL — {len(findings)} finding(s) in {path}:")
            for f in findings:
                print(
                    f"  - [{f['rule_id']}] line {f['line']}: {f['message']}"
                )
                if f["snippet"]:
                    print(f"      {f['snippet']}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
