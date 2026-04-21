"""OpenAI Model Spec Evals exporter.

Converts a Verdict scorecard (schema ``scorecard.v1``) into the shape
OpenAI's Model Spec Evals publishes:

.. code-block:: json

   {
     "run_id": "...",
     "criteria": {
       "correctness": {"score": 6, "passed": true, "rationale": "..."},
       "safety":      {"score": 7, "passed": true, "rationale": "..."}
     }
   }

Model Spec uses a 1-7 scale; Verdict uses 1-10. The rescaling table is
documented in ``skills/judge/rubrics/model-spec-compliance.md`` and
reproduced here so this module doesn't depend on rubric text.

Pass/fail threshold defaults to 7/10 (Verdict's "Satisfactory") so
anything at or above B- passes. Callable override via ``threshold``.

Offline-first: no ``openai`` / ``anthropic`` imports; pure stdlib.

References (retrieved 2026-04-20):
- https://alignment.openai.com/model-spec-evals
- https://developers.openai.com/blog/eval-skills
"""
from __future__ import annotations

from typing import Any, Dict

__all__ = ["to_openai_evals_format", "DEFAULT_PASS_THRESHOLD", "rescale_to_model_spec"]

DEFAULT_PASS_THRESHOLD: int = 7


def rescale_to_model_spec(verdict_score: int) -> int:
    """Map a Verdict 1-10 score to OpenAI Model Spec's 1-7 scale.

    Aligned with ``skills/judge/rubrics/model-spec-compliance.md``:

        10, 9  → 7 (exemplary)
        8, 7   → 6 (strong)
        6, 5   → 5 (acceptable)
        4      → 4 (borderline)
        3      → 3 (weak)
        2      → 2 (poor)
        1      → 1 (non-compliant)
    """
    if verdict_score >= 9:
        return 7
    if verdict_score >= 7:
        return 6
    if verdict_score >= 5:
        return 5
    return max(1, min(int(verdict_score), 4))


def _run_id_from_scorecard(card: Dict[str, Any]) -> str:
    """Build a stable run identifier from skill + timestamp."""
    skill = card.get("skill", "unknown")
    timestamp = card.get("timestamp", "")
    return f"{skill}@{timestamp}" if timestamp else skill


def to_openai_evals_format(
    scorecard: Dict[str, Any],
    *,
    threshold: int = DEFAULT_PASS_THRESHOLD,
    rescale: bool = False,
) -> Dict[str, Any]:
    """Convert a Verdict scorecard into Model Spec Evals JSON.

    Parameters
    ----------
    scorecard:
        The dict emitted by ``score.build_scorecard`` / read back from
        ``skills/judge/scores/*.json``. Must contain ``skill`` +
        ``dimensions`` keys at minimum.
    threshold:
        Verdict 1-10 score at or above which a dimension is marked
        ``"passed": true``. Default 7 (B-).
    rescale:
        When ``True``, also emit the Model Spec 1-7 integer under
        ``criteria[dim].score``. Default ``False`` so the numeric
        score matches what downstream Verdict consumers expect.
    """
    if not isinstance(scorecard, dict):
        raise TypeError("scorecard must be a dict (the Verdict scorecard JSON)")

    dimensions = scorecard.get("dimensions", {})
    if not isinstance(dimensions, dict):
        raise ValueError("scorecard.dimensions must be an object")

    criteria: Dict[str, Dict[str, Any]] = {}
    for name, entry in dimensions.items():
        if not isinstance(entry, dict):
            continue
        raw_score = entry.get("score")
        if not isinstance(raw_score, (int, float)) or isinstance(raw_score, bool):
            continue
        score_int = int(raw_score)
        criteria[name] = {
            "score": rescale_to_model_spec(score_int) if rescale else score_int,
            "passed": score_int >= threshold,
            "rationale": str(entry.get("justification", "")).strip(),
        }
        # Preserve the raw Verdict score when rescaling so consumers
        # can round-trip without loss.
        if rescale:
            criteria[name]["verdict_score"] = score_int
        # LLM second-opinion fields are round-tripped unchanged so
        # consumers can surface both signals.
        if "llm_score" in entry and isinstance(entry["llm_score"], (int, float)):
            criteria[name]["llm_score"] = int(entry["llm_score"])
        if "llm_justification" in entry and isinstance(entry["llm_justification"], str):
            criteria[name]["llm_rationale"] = entry["llm_justification"].strip()

    return {
        "run_id": _run_id_from_scorecard(scorecard),
        "spec_version": "model-spec-evals/2026-04",
        "source": {
            "tool": "verdict",
            "schema_version": scorecard.get("schemaVersion", "1.0.0"),
            "scorecard_schema": scorecard.get(
                "$schema", "https://verdict.dev/schemas/scorecard.v1.json",
            ),
        },
        "threshold": threshold,
        "rescaled_to_model_spec": rescale,
        "criteria": criteria,
        "summary": {
            "composite_score": scorecard.get("composite_score"),
            "grade":           scorecard.get("grade"),
            "skill":           scorecard.get("skill"),
            "timestamp":       scorecard.get("timestamp"),
        },
    }
