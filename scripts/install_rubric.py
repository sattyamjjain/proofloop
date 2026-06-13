#!/usr/bin/env python3
"""Install a community rubric from a URL.

Fetches a rubric markdown file (and optional ``.weights.json`` sidecar)
from a GitHub raw URL or any HTTPS URL, validates it looks like a Proofloop
rubric, and drops it into ``skills/judge/rubrics/``. Stdlib-only.

Usage:
    python3 scripts/install_rubric.py <url> [--name NAME] [--rubric-dir DIR]

The rubric file must contain the Proofloop dimension table (``### Correctness``,
etc.) — any document missing that structure is rejected. If the URL's
directory also contains ``<name>.weights.json``, it is fetched and
validated via ``score.load_rubric_weights``.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RUBRIC_DIR = PROJECT_ROOT / "skills" / "judge" / "rubrics"

REQUIRED_HEADINGS = [
    "### Correctness",
    "### Completeness",
    "### Adherence",
]


def _fetch(url: str, timeout: int = 10) -> Optional[bytes]:
    """Return the bytes at *url* or None on any failure (logged to stderr)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "verdict-install-rubric/1.1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                print(f"Error: {url} returned HTTP {resp.status}", file=sys.stderr)
                return None
            return resp.read()
    except Exception as exc:  # urllib raises a broad tree; surface to stderr
        print(f"Error: could not fetch {url} ({exc})", file=sys.stderr)
        return None


def _validate_rubric_text(text: str) -> Optional[str]:
    """Return an error message if *text* is not a Proofloop rubric, else None."""
    missing = [h for h in REQUIRED_HEADINGS if h not in text]
    if missing:
        return f"rubric is missing required headings: {missing}"
    return None


def _derive_name(url: str, override: Optional[str]) -> str:
    if override:
        return override
    filename = Path(urllib.parse.urlparse(url).path).name
    if filename.endswith(".md"):
        filename = filename[:-3]
    return filename or "custom"


def install_rubric(url: str, rubric_dir: Path, name: Optional[str] = None) -> int:
    """Download, validate, and write a rubric. Returns an exit code."""
    rubric_bytes = _fetch(url)
    if rubric_bytes is None:
        return 1
    try:
        rubric_text = rubric_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        print(f"Error: rubric is not UTF-8 ({exc})", file=sys.stderr)
        return 1
    err = _validate_rubric_text(rubric_text)
    if err:
        print(f"Error: {err}", file=sys.stderr)
        return 1

    target_name = _derive_name(url, name)
    rubric_dir.mkdir(parents=True, exist_ok=True)
    target = rubric_dir / f"{target_name}.md"
    target.write_text(rubric_text, encoding="utf-8")
    print(f"Installed rubric to {target}")

    # Optional .weights.json sidecar beside the rubric on the server
    sidecar_url = url.rsplit("/", 1)[0] + f"/{target_name}.weights.json"
    sidecar_bytes = _fetch(sidecar_url, timeout=5)
    if sidecar_bytes is None:
        return 0
    try:
        weights = json.loads(sidecar_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        print(f"Warning: sidecar at {sidecar_url} is malformed ({exc}); skipping.", file=sys.stderr)
        return 0
    if not isinstance(weights, dict):
        print(f"Warning: sidecar at {sidecar_url} is not an object; skipping.", file=sys.stderr)
        return 0
    total = 0.0
    try:
        total = sum(float(v) for v in weights.values())
    except (TypeError, ValueError) as exc:
        print(f"Warning: sidecar has non-numeric weights ({exc}); skipping.", file=sys.stderr)
        return 0
    if abs(total - 1.0) > 1e-6:
        print(
            f"Warning: sidecar weights sum to {total:.4f}, not 1.0; skipping install.",
            file=sys.stderr,
        )
        return 0
    sidecar_target = rubric_dir / f"{target_name}.weights.json"
    sidecar_target.write_text(sidecar_bytes.decode("utf-8"), encoding="utf-8")
    print(f"Installed weight overrides to {sidecar_target}")
    return 0


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(prog="install-rubric")
    parser.add_argument("url", help="HTTPS URL to the rubric .md file")
    parser.add_argument("--name", default=None, help="Override the installed rubric filename")
    parser.add_argument(
        "--rubric-dir",
        default=str(DEFAULT_RUBRIC_DIR),
        help=f"Target directory (default: {DEFAULT_RUBRIC_DIR})",
    )
    args = parser.parse_args(argv)
    return install_rubric(args.url, Path(args.rubric_dir), args.name)


if __name__ == "__main__":
    sys.exit(main())
