"""Cloudflare AI Gateway eval-webhook integration (read-only, pure Python).

Cloudflare's AI Gateway gained an eval-webhook surface in April 2026
(`developers.cloudflare.com/ai-gateway/evaluations`). The hook fires
on every request/response pair the gateway sees and expects the
target endpoint to return ``{score: 0..1, passed: bool, ...}``.

This module exposes ``verdict_as_eval_webhook(payload)`` — a pure-
function entry point that adapts the gateway's payload shape into a
synthetic Verdict transcript, runs the heuristic scorer, and maps
Verdict's 1-10 composite onto Cloudflare's ``[0.0, 1.0]`` range.

Design constraints
------------------
- **No Cloudflare SDK dependency.** The function is dict-in / dict-
  out; the caller (a Cloudflare Worker, a Vercel function, or a
  direct ``urllib`` POST handler) wraps the HTTP transport layer.
- **Stdlib only.** Verdict's offline-first invariant is preserved.
- **Transcript builder is conservative.** When the payload's shape
  diverges from the documented format, the function builds a
  best-effort transcript rather than raising — gateway operators
  prefer a soft pass to a 500.

Expected payload shape (verified 2026-04-23 docs):

.. code-block:: json

   {
     "request": {
       "messages": [{"role":"user","content":"..."}],
       "model": "claude-haiku-4-5"
     },
     "response": {
       "choices": [{"message":{"role":"assistant","content":"..."}}]
     },
     "model": "claude-haiku-4-5",
     "gateway_id": "my-prod-gateway"
   }

Returns:

.. code-block:: json

   {
     "score": 0.84,
     "passed": true,
     "rationale": "<short summary line>",
     "scorecard_url": null
   }

Source signal: `blog.cloudflare.com — AI Gateway evals (2026-04-23)
<https://blog.cloudflare.com/ai-gateway-evals/>`_,
`developers.cloudflare.com/ai-gateway/evaluations
<https://developers.cloudflare.com/ai-gateway/evaluations/>`_.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import score  # noqa: E402

# Default skill name when the payload doesn't carry one. Picks the
# generic rubric in skills/judge/rubrics/default.md.
DEFAULT_SKILL: str = "default"

# Composite threshold above which the gateway's ``passed`` flag is
# True. Verdict scores 1-10; 7.0 = "above average / B-". Operators
# can override via the payload's ``threshold`` field.
DEFAULT_PASS_THRESHOLD: float = 7.0


def _build_synthetic_transcript_path(
    request: Any, response: Any, model: Optional[str], tmpdir: Path,
) -> Path:
    """Materialise a JSONL transcript file score.py can ingest."""
    import json

    lines: list = []
    if isinstance(request, dict):
        for msg in request.get("messages", []) or []:
            if isinstance(msg, dict):
                lines.append(msg)
    if isinstance(response, dict):
        for choice in response.get("choices", []) or []:
            if isinstance(choice, dict) and isinstance(choice.get("message"), dict):
                lines.append(choice["message"])
    if model and lines:
        # Inject model into the first record so detect_model_from_transcript
        # picks it up via the existing "model":"<id>" raw-file scan.
        lines[0] = {**lines[0], "model": model}
    path = tmpdir / "cf-eval-transcript.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for record in lines:
            handle.write(json.dumps(record) + "\n")
    return path


def _short_rationale(scorecard: Dict[str, Any]) -> str:
    """One-line summary suitable for logs / Slack / dashboard tooltip."""
    composite = scorecard.get("composite_score", "?")
    grade = scorecard.get("grade", "?")
    one_liner = scorecard.get("one_liner", "").strip()
    if one_liner:
        return f"{composite}/10 ({grade}) — {one_liner}"
    return f"{composite}/10 ({grade})"


def verdict_as_eval_webhook(
    request_body: Dict[str, Any],
    rubric_dir: Optional[str] = None,
    skill_name: Optional[str] = None,
    threshold: Optional[float] = None,
    scorecard_url_template: Optional[str] = None,
) -> Dict[str, Any]:
    """Run Verdict against a Cloudflare AI Gateway eval-webhook payload.

    Maps Verdict's 1-10 composite onto Cloudflare's expected
    ``[0.0, 1.0]`` band by dividing by 10. ``passed`` is True when
    composite ≥ ``threshold`` (default 7.0; can be overridden via
    payload ``threshold`` or the *threshold* argument).

    *scorecard_url_template* lets the caller embed a templated URL —
    e.g. ``"https://verdict.example/sc/{gateway_id}/{request_id}"``.
    The returned ``scorecard_url`` is ``None`` when the template is
    omitted or doesn't render.

    Returns a dict with shape:
    ``{"score": float, "passed": bool, "rationale": str, "scorecard_url": str|None}``.
    """
    import tempfile

    if not isinstance(request_body, dict):
        return {
            "score": 0.0, "passed": False,
            "rationale": "invalid payload: not a dict",
            "scorecard_url": None,
        }

    request = request_body.get("request") or {}
    response = request_body.get("response") or {}
    model = request_body.get("model")
    if isinstance(request, dict) and not model:
        model = request.get("model")
    gateway_id = request_body.get("gateway_id")
    request_id = request_body.get("request_id") or request_body.get("id")

    payload_threshold = request_body.get("threshold")
    if isinstance(payload_threshold, (int, float)):
        threshold_value = float(payload_threshold)
    elif isinstance(threshold, (int, float)):
        threshold_value = float(threshold)
    else:
        threshold_value = DEFAULT_PASS_THRESHOLD

    skill = skill_name or request_body.get("skill") or DEFAULT_SKILL
    rubric_path = rubric_dir or str(PROJECT_ROOT / "rubrics")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        transcript_path = _build_synthetic_transcript_path(
            request, response, model if isinstance(model, str) else None, tmp,
        )
        scores_dir = tmp / "scores"
        try:
            scorecard = score.build_scorecard(
                skill_name=skill,
                transcript_path=str(transcript_path),
                rubric_dir=rubric_path,
                scores_dir=str(scores_dir),
            )
        except Exception as exc:  # pragma: no cover — defensive
            return {
                "score": 0.0, "passed": False,
                "rationale": f"verdict scoring failed: {exc.__class__.__name__}",
                "scorecard_url": None,
            }

    composite = scorecard.get("composite_score", 0.0)
    cf_score = max(0.0, min(1.0, float(composite) / 10.0))
    rationale = _short_rationale(scorecard)
    scorecard_url: Optional[str] = None
    if scorecard_url_template and gateway_id and request_id:
        try:
            scorecard_url = scorecard_url_template.format(
                gateway_id=gateway_id, request_id=request_id,
            )
        except (KeyError, IndexError):
            scorecard_url = None
    return {
        "score": round(cf_score, 4),
        "passed": float(composite) >= threshold_value,
        "rationale": rationale,
        "scorecard_url": scorecard_url,
    }
