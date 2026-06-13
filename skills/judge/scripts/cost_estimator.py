#!/usr/bin/env python3
"""Local-only per-scorecard cost estimator (R4).

Estimates the USD cost of running Proofloop's opt-in LLM second-opinion
analyzer for a given scorecard, based on a stdlib-only per-model
pricing table. **Local-only** — no SaaS coupling, no telemetry leaves
the host. Pricing is a starting point; adopters override via
``--pricing-file PATH``.

Usage:

    python3 skills/judge/scripts/cost_estimator.py \\
        --input-tokens 1000 --output-tokens 500 \\
        --model claude-haiku-4-5 \\
        [--pricing-file pricing.json]

Or:

    python3 skills/judge/scripts/cost_estimator.py \\
        --scorecard skills/judge/scores/<file>.json

The scorecard path mode reads ``adjustments.brier_calibration`` /
``model`` / ``transcript_lines`` and an optional embedded
``llm_usage`` block; cost is reported per-scorecard.

Stdlib-only. No third-party deps. The pricing table reflects
April 2026 published rates for the most common models Proofloop's
LLM-judge path uses; figures are USD per 1M tokens.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# USD per 1M tokens, verified against vendor pricing pages 2026-04.
# Adopters override via --pricing-file when the table drifts.
DEFAULT_PRICING_USD_PER_MTOK: Dict[str, Dict[str, float]] = {
    "claude-opus-4-7":     {"input": 15.0,  "output": 75.0},
    "claude-sonnet-4-6":   {"input": 3.0,   "output": 15.0},
    "claude-haiku-4-5":    {"input": 1.0,   "output": 5.0},
    "gpt-5-5":             {"input": 5.0,   "output": 30.0},
    "gpt-5-5-pro":         {"input": 30.0,  "output": 180.0},
    "gemini-3-1-pro":      {"input": 7.0,   "output": 21.0},
    # Fallback when the model isn't in the table — chosen to be
    # high enough that an unknown model triggers attention rather
    # than silently understating cost.
    "default":             {"input": 10.0,  "output": 30.0},
}


def load_pricing(path: Optional[str]) -> Dict[str, Dict[str, float]]:
    """Load a pricing override file, or return the default table."""
    if not path:
        return dict(DEFAULT_PRICING_USD_PER_MTOK)
    target = Path(path)
    if not target.is_file():
        raise FileNotFoundError(f"pricing file not found: {target}")
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not parse pricing file: {exc}")
    if not isinstance(data, dict):
        raise ValueError("pricing file must be a JSON object")
    coerced: Dict[str, Dict[str, float]] = {}
    for model, rates in data.items():
        if not isinstance(rates, dict):
            continue
        try:
            coerced[str(model)] = {
                "input": float(rates.get("input", 0)),
                "output": float(rates.get("output", 0)),
            }
        except (TypeError, ValueError):
            continue
    if not coerced:
        raise ValueError("pricing file contained no usable entries")
    if "default" not in coerced:
        coerced["default"] = DEFAULT_PRICING_USD_PER_MTOK["default"]
    return coerced


def estimate_usd(
    input_tokens: int,
    output_tokens: int,
    model: str,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Estimate USD cost for *input_tokens* + *output_tokens* on *model*.

    Returns a dict with:
    - ``model_used`` — the model key actually applied (might be
      ``"default"`` when *model* isn't in the pricing table).
    - ``model_lookup`` — the model key requested.
    - ``input_usd`` — USD cost of input tokens.
    - ``output_usd`` — USD cost of output tokens.
    - ``total_usd`` — sum, rounded to 6 decimal places.
    - ``input_tokens``, ``output_tokens`` — echoed for the caller.
    """
    if input_tokens < 0 or output_tokens < 0:
        raise ValueError("token counts must be non-negative")
    table = pricing if pricing is not None else DEFAULT_PRICING_USD_PER_MTOK
    rates = table.get(model)
    model_used = model
    if rates is None:
        rates = table.get("default", DEFAULT_PRICING_USD_PER_MTOK["default"])
        model_used = "default"
    input_usd = (input_tokens / 1_000_000) * rates["input"]
    output_usd = (output_tokens / 1_000_000) * rates["output"]
    return {
        "model_used": model_used,
        "model_lookup": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_usd": round(input_usd, 6),
        "output_usd": round(output_usd, 6),
        "total_usd": round(input_usd + output_usd, 6),
    }


def estimate_from_scorecard(
    scorecard_path: str,
    pricing: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    """Estimate cost for an existing scorecard JSON file.

    Reads:
    - ``model`` for the pricing-table lookup (falls back to the
      ``default`` entry when not in the table).
    - ``llm_usage.input_tokens`` / ``llm_usage.output_tokens`` when
      the LLM second-opinion analyzer ran and recorded usage. When
      absent, returns a "no LLM usage recorded" rationale and zero
      cost — Proofloop's heuristic-only path is free.
    """
    target = Path(scorecard_path)
    if not target.is_file():
        raise FileNotFoundError(f"scorecard not found: {target}")
    try:
        card = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not parse scorecard: {exc}")
    if not isinstance(card, dict):
        raise ValueError("scorecard root must be a JSON object")
    model = card.get("model") or "default"
    usage = card.get("llm_usage")
    if not isinstance(usage, dict):
        return {
            "scorecard": str(target),
            "skill": card.get("skill"),
            "model_lookup": model,
            "rationale": (
                "No llm_usage block — Proofloop ran heuristics only "
                "(zero LLM cost)."
            ),
            "total_usd": 0.0,
        }
    try:
        input_tokens = int(usage.get("input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"llm_usage tokens must be ints: {exc}")
    estimate = estimate_usd(input_tokens, output_tokens, model, pricing)
    estimate.update({
        "scorecard": str(target),
        "skill": card.get("skill"),
    })
    return estimate


def parse_args(argv: Optional[list] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="proofloop-cost-estimator")
    parser.add_argument(
        "--input-tokens", type=int, default=None,
        help="Input token count for direct estimate. Pair with --model.",
    )
    parser.add_argument(
        "--output-tokens", type=int, default=None,
        help="Output token count for direct estimate. Pair with --model.",
    )
    parser.add_argument(
        "--model", default=None,
        help="Model ID for direct estimate. e.g. claude-haiku-4-5",
    )
    parser.add_argument(
        "--scorecard", default=None,
        help="Scorecard JSON path. Reads model + llm_usage from the file.",
    )
    parser.add_argument(
        "--pricing-file", default=None,
        help="Override pricing table via a JSON file mapping model → "
             "{input, output} (USD per 1M tokens).",
    )
    parser.add_argument(
        "--out", default=None,
        help="Write JSON output to PATH. Default: stdout.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list] = None) -> int:
    args = parse_args(argv)
    try:
        pricing = load_pricing(args.pricing_file)
    except (FileNotFoundError, ValueError) as exc:
        print(f"proofloop-cost-estimator: {exc}", file=sys.stderr)
        return 2
    if args.scorecard:
        try:
            result = estimate_from_scorecard(args.scorecard, pricing)
        except (FileNotFoundError, ValueError) as exc:
            print(f"proofloop-cost-estimator: {exc}", file=sys.stderr)
            return 2
    elif args.input_tokens is not None or args.output_tokens is not None:
        if args.model is None:
            print(
                "proofloop-cost-estimator: --model required for direct estimate",
                file=sys.stderr,
            )
            return 2
        try:
            result = estimate_usd(
                args.input_tokens or 0,
                args.output_tokens or 0,
                args.model,
                pricing,
            )
        except ValueError as exc:
            print(f"proofloop-cost-estimator: {exc}", file=sys.stderr)
            return 2
    else:
        print(
            "proofloop-cost-estimator: provide --scorecard OR "
            "(--input-tokens + --output-tokens + --model)",
            file=sys.stderr,
        )
        return 2
    rendered = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
