#!/usr/bin/env python3
"""Sandbox-capability declaration check for the self-score CI gate.

Claude Code v2.1.117 (Apr 2026) hardened its sandbox: ``bash`` and
file-write are now namespace-isolated. CI workflows that run Proofloop
under that sandbox declare the caps they intend to use via the
``CLAUDE_SANDBOX_CAPS`` env var. This script reads that var, parses
the cap list, and asserts the declaration is present.

**This is a declaration check, not a runtime sandbox enforcer.** The
script can verify the workflow advertised the caps it expected to
use; it cannot block a syscall the runner already permitted. Actual
isolation is provided by the Claude Code runtime (or whatever
sandbox the CI host configured). Run this script as part of the CI
flow to catch the case where the workflow forgot to declare its
caps and a future hardening would silently disable the job.

Schema for ``CLAUDE_SANDBOX_CAPS`` (verified 2026-04-26):

- Comma-separated list of ``<resource>:<mode>`` pairs.
- *resource* in {bash, fs, net, exec}.
- *mode* in {read, write, none}.
- Example: ``CLAUDE_SANDBOX_CAPS=bash:read,fs:read,net:none``.

Stdlib-only. Never imports anything outside the standard library.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, List, Set, Tuple

ENV_VAR: str = "CLAUDE_SANDBOX_CAPS"

VALID_RESOURCES: Set[str] = {"bash", "fs", "net", "exec"}
VALID_MODES: Set[str] = {"read", "write", "none"}

# Caps the self-score workflow expects to declare. Verifies the
# workflow file and the runtime env stay in sync.
EXPECTED_SELF_SCORE_CAPS: Tuple[Tuple[str, str], ...] = (
    ("bash", "read"),
    ("fs", "read"),
)


def parse_caps(value: str) -> List[Tuple[str, str]]:
    """Parse the env-var value into a list of ``(resource, mode)`` tuples.

    Empty values return ``[]`` (caller decides if that's an error).
    Tokens that don't match the ``resource:mode`` shape with valid
    enum values are silently skipped — bogus declarations should
    fail the check downstream rather than crash the parser.
    """
    if not value:
        return []
    out: List[Tuple[str, str]] = []
    for token in value.split(","):
        token = token.strip()
        if ":" not in token:
            continue
        resource, _, mode = token.partition(":")
        resource = resource.strip().lower()
        mode = mode.strip().lower()
        if resource in VALID_RESOURCES and mode in VALID_MODES:
            out.append((resource, mode))
    return out


def has_required_caps(
    declared: Iterable[Tuple[str, str]],
    required: Iterable[Tuple[str, str]],
) -> List[Tuple[str, str]]:
    """Return required caps that are NOT present in declared. Empty = pass."""
    declared_set = set(declared)
    return [cap for cap in required if cap not in declared_set]


def emit_rationale(
    declared: List[Tuple[str, str]],
    missing: List[Tuple[str, str]],
) -> str:
    """One-line scorecard-rationale string for the workflow log."""
    if not declared:
        return (
            "[sandbox] no CLAUDE_SANDBOX_CAPS declared — workflow may break "
            "under hardened Claude Code runtime; declare expected caps "
            "explicitly."
        )
    if missing:
        missing_str = ",".join(f"{r}:{m}" for r, m in missing)
        return (
            f"[sandbox] declared {len(declared)} caps but missing required: "
            f"{missing_str}. Update workflow CLAUDE_SANDBOX_CAPS."
        )
    declared_str = ",".join(f"{r}:{m}" for r, m in declared)
    return f"[sandbox] caps OK ({declared_str})"


def parse_args(argv: List[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="proofloop-sandbox-caps-check")
    parser.add_argument(
        "--require",
        action="append",
        default=[],
        help=(
            "Required capability in resource:mode form; may be repeated. "
            "Defaults to bash:read,fs:read for the self-score workflow."
        ),
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any required cap is missing.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> int:
    args = parse_args(argv)
    raw = os.environ.get(ENV_VAR, "")
    declared = parse_caps(raw)
    if args.require:
        required = []
        for token in args.require:
            parsed = parse_caps(token)
            if parsed:
                required.extend(parsed)
    else:
        required = list(EXPECTED_SELF_SCORE_CAPS)
    missing = has_required_caps(declared, required)
    rationale = emit_rationale(declared, missing)
    print(rationale)
    if missing and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
