"""Register Verdict as a LightEval v0.13.0+ custom metric.

Usage (inside a LightEval config file)::

    from skills.judge.integrations.lighteval_shim import verdict_metric

    # Most LightEval custom-metric surfaces accept a callable; drop
    # ``verdict_metric`` in and it will score each prediction against
    # its reference using the Verdict scoring engine.

The shim:

- **Does not** import ``lighteval`` at module-import time. LightEval
  isn't a runtime dep of Verdict and importing it eagerly would break
  the stdlib-only pitch for users who don't want it. The lazy import
  happens only when :func:`_apply_lighteval_side_effects` is called,
  which no call path in this shim actually does — it's a stub that
  other wrappers can opt into.
- **Does** call Verdict's own scorer by building a synthetic
  single-turn transcript from the prediction/reference pair.
- **Returns a float in [0, 1]** so it can slot into LightEval's
  metric-aggregation layer without further scaling.

References (retrieved 2026-04-20):

- LightEval v0.13.0 custom metrics guide. The metric callable shape
  this shim matches is intentionally conservative and independent
  of LightEval's internals — if their shape changes, update this
  file, not score.py.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve the scoring engine relative to this file without hard-coding
# the full path — the integration works both as a package import and
# when ``skills/judge`` is dropped into another project.
_HERE = Path(__file__).resolve()
_SCRIPTS_DIR = _HERE.parent.parent / "scripts"
_RUBRICS_DIR = _HERE.parent.parent / "rubrics"
_DEFAULT_RUBRIC = "correctness"

# Range of LightEval-friendly output. Verdict scores are 1-10; we
# rescale to [0, 1] by subtracting 1 then dividing by 9.
_LIGHTEVAL_SCALE_DENOMINATOR: float = 9.0


def _import_score_module() -> Any:
    """Lazy import of Verdict's score engine.

    Kept behind a function (rather than a top-level ``import``) so
    that callers who only want to check the shim's signature don't
    pay the cost of parsing score.py.
    """
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    import score  # type: ignore
    return score


def _synthesize_transcript(prediction: str, reference: str) -> List[str]:
    """Turn a (prediction, reference) pair into a two-turn transcript."""
    return [
        json.dumps({"role": "user", "content": reference}),
        json.dumps({"role": "assistant", "content": prediction}),
    ]


def _score_pair(prediction: str, reference: str, rubric: str) -> float:
    """Return a single [0, 1] score for one (prediction, reference) pair."""
    score = _import_score_module()

    with tempfile.TemporaryDirectory() as tmp_root:
        tmp = Path(tmp_root)
        transcript_path = tmp / "pair.jsonl"
        transcript_path.write_text(
            "\n".join(_synthesize_transcript(prediction, reference)) + "\n",
            encoding="utf-8",
        )
        card = score.build_scorecard(
            skill_name=rubric,
            transcript_path=str(transcript_path),
            rubric_dir=str(_RUBRICS_DIR),
            scores_dir=str(tmp / "scores"),
            config_path=None,
        )
        raw: float = float(card.get("composite_score", 0.0))
    return max(0.0, min((raw - 1.0) / _LIGHTEVAL_SCALE_DENOMINATOR, 1.0))


def verdict_metric(
    predictions: List[str],
    references: List[str],
    rubric: str = _DEFAULT_RUBRIC,
) -> Dict[str, float]:
    """LightEval-compatible metric callable.

    Parameters
    ----------
    predictions, references:
        Parallel lists from LightEval's evaluation loop. Mismatched
        lengths raise ``ValueError``.
    rubric:
        Verdict rubric name (from ``skills/judge/rubrics/``) used to
        score the pair. Default ``"correctness"`` — falls through to
        the ``default`` rubric because no ``correctness.md`` exists,
        which keeps the metric neutral / self-describing.

    Returns
    -------
    dict[str, float]
        ``{"verdict_score": mean_score_in_[0,1], "n": len(predictions)}``
        so LightEval can aggregate across samples. Individual sample
        scores are not returned here — callers that want them should
        call :func:`_score_pair` directly.
    """
    if len(predictions) != len(references):
        raise ValueError(
            f"verdict_metric: len(predictions)={len(predictions)} != "
            f"len(references)={len(references)}"
        )
    if not predictions:
        return {"verdict_score": 0.0, "n": 0.0}

    scores = [_score_pair(p, r, rubric) for p, r in zip(predictions, references)]
    mean = sum(scores) / len(scores)
    return {"verdict_score": mean, "n": float(len(scores))}


def _apply_lighteval_side_effects(_lighteval_module: Optional[Any] = None) -> None:
    """Placeholder for LightEval runtime registration.

    No-ops today. Left as an extension point so downstream users can
    subclass and do whatever LightEval's metric-registry API requires
    in the version they're pinned to — without Verdict taking a hard
    ``lighteval`` dep. If you call this, supply the already-imported
    ``lighteval`` module yourself.
    """
    return None
