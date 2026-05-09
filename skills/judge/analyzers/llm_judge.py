"""Opt-in LLM second-opinion analyzer.

.. warning::

    This consumes tokens. Set a per-request budget via the
    ``task-budgets-2026-03-13`` beta header (supported by Claude since
    2026-04-17) so Claude hard-caps its own spend and you don't ship a
    surprise bill when someone turns this on in CI.

Default is OFF. Enabling it requires two things:

1. ``judge-config.json.llm_second_opinion.enabled = true``
2. ``ANTHROPIC_API_KEY`` in the environment

When both are set, ``score.py`` calls ``score_with_llm`` after the
heuristic pass and merges per-dimension scores into the scorecard under
``dimensions[dim].llm_score`` and ``dimensions[dim].llm_justification``.

The module is stdlib-only: HTTP calls go through ``urllib.request``.
No ``anthropic`` pip package is imported. Callers who want to inject
a custom client (mock in tests, hit a proxy in prod) can construct an
``AnthropicClient`` subclass or any object that implements
``messages_create(model: str, system: str, prompt: str, max_tokens: int) -> str``.

Cross-family second-opinion pattern note (2026-05-09): GitHub
Copilot CLI's Rubber Duck (cross-family critic, expanded model
pairings shipped 2026-05-07) is the same pattern this analyzer
implements: an opt-in second model from a different family reviews
the first model's output. Verdict runs this off-by-default and
stdlib-only; the critic is one signal among many, NOT a leaderboard
verdict. Source:
https://github.blog/changelog/2026-05-07-rubber-duck-in-github-copilot-cli-now-supports-more-models/
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Protocol, Tuple

__all__ = [
    "DIMENSIONS",
    "MAX_TRANSCRIPT_CHARS",
    "LLMJudgeError",
    "LLMClient",
    "AnthropicClient",
    "score_with_llm",
    "truncate_transcript",
    "build_prompt",
    "parse_scores",
    "resolve_cache_ttl_from_env",
    "build_cached_system_block",
]

DIMENSIONS: List[str] = [
    "correctness", "completeness", "adherence", "actionability",
    "efficiency", "safety", "consistency",
]

# ~4k tokens ≈ 16k chars (rough; depends on model tokenizer).
# Leave headroom for the system prompt + rubric criteria so the outgoing
# request stays under Haiku's 200k context window without contention.
MAX_TRANSCRIPT_CHARS: int = 16_000

ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
# 2026-04-20 verified: beta header is underscore-cased per the current
# platform docs (anthropic-beta: task_budgets-2026-03-13). Kept the
# hyphenated alias around for older clients that still send the dashed
# form — both variants are accepted by the Messages API during the
# research-preview window.
TASK_BUDGETS_BETA = "task_budgets-2026-03-13"
TASK_BUDGETS_BETA_LEGACY = "task-budgets-2026-03-13"

# Minimum total tokens the task_budgets header accepts (per docs).
TASK_BUDGET_MIN_TOKENS: int = 20_000
# Hard ceiling multiplier: task_budget is a soft suggestion; the
# ``max_tokens`` request parameter is the hard cap. Verdict sets both
# so the judge finishes gracefully without over-spend.
TASK_BUDGET_HARD_CEILING_RATIO: float = 1.25

# Prompt-caching (Apr 2026). Claude Code's changelog enables caching by
# default; Verdict mirrors that. TTLs: "5m" is stock; "1h" requires the
# extended-cache-ttl-2025-04-11 beta header. Env vars flip the knob
# without touching judge-config.json so CI can set them on a hot path.
EXTENDED_CACHE_TTL_BETA: str = "extended-cache-ttl-2025-04-11"
DEFAULT_PROMPT_CACHE_TTL: str = "5m"
ENV_ENABLE_CACHE_1H: str = "ENABLE_PROMPT_CACHING_1H"
ENV_FORCE_CACHE_5M: str = "FORCE_PROMPT_CACHING_5M"


def resolve_cache_ttl_from_env(env: Optional[Dict[str, str]] = None) -> str:
    """Pick a prompt-cache TTL from Verdict's env-var convention.

    Precedence: ``FORCE_PROMPT_CACHING_5M`` (explicit lock-down) >
    ``ENABLE_PROMPT_CACHING_1H`` (extended beta) > default ``"5m"``.

    Accepts an *env* mapping for testability; falls back to
    :data:`os.environ` when omitted.
    """
    source = env if env is not None else os.environ
    force_5m = source.get(ENV_FORCE_CACHE_5M, "").strip()
    enable_1h = source.get(ENV_ENABLE_CACHE_1H, "").strip()
    if force_5m and force_5m not in ("0", "false", "False", ""):
        return "5m"
    if enable_1h and enable_1h not in ("0", "false", "False", ""):
        return "1h"
    return DEFAULT_PROMPT_CACHE_TTL


def build_cached_system_block(rubric_md: str, ttl: str = DEFAULT_PROMPT_CACHE_TTL) -> Dict[str, Any]:
    """Return a cached system content block for the Messages API.

    The rubric text rarely changes within a run, so caching it cuts the
    per-call token cost dramatically once the cache warms. *ttl* must be
    either ``"5m"`` (standard) or ``"1h"`` (extended beta).
    """
    if ttl not in ("5m", "1h"):
        raise ValueError(f"prompt cache TTL must be '5m' or '1h', got {ttl!r}")
    return {
        "type": "text",
        "text": rubric_md,
        "cache_control": {"type": "ephemeral", "ttl": ttl},
    }


class LLMJudgeError(RuntimeError):
    """Raised when the LLM call fails in a way the caller should surface."""


class LLMClient(Protocol):
    """Duck-typed client contract.

    Implementations must accept a ``system`` + ``prompt`` pair and
    return the assistant's text response. Everything else (headers,
    streaming, retries) is implementation-defined.
    """

    def messages_create(
        self,
        model: str,
        system: str,
        prompt: str,
        max_tokens: int,
    ) -> str: ...


class AnthropicClient:
    """Minimal stdlib-only Anthropic API client.

    Only implements the single ``messages_create`` call Verdict needs.
    Adds the ``task-budgets-2026-03-13`` beta header when a budget is
    configured so Claude self-caps runaway evaluations.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        budget_tokens: Optional[int] = None,
        timeout: float = 30.0,
        log_budget_countdown: bool = True,
        prompt_cache_ttl: Optional[str] = None,
        log_cache_usage: bool = True,
    ) -> None:
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise LLMJudgeError(
                "ANTHROPIC_API_KEY not set; LLM second opinion cannot call the API"
            )
        self.budget_tokens = budget_tokens
        self.timeout = timeout
        self.log_budget_countdown = log_budget_countdown
        if prompt_cache_ttl is not None and prompt_cache_ttl not in ("5m", "1h"):
            raise ValueError(
                f"prompt_cache_ttl must be '5m' or '1h', got {prompt_cache_ttl!r}"
            )
        self.prompt_cache_ttl = prompt_cache_ttl
        self.log_cache_usage = log_cache_usage

    def messages_create(
        self,
        model: str,
        system: str,
        prompt: str,
        max_tokens: int = 2048,
    ) -> str:
        # Enforce the task_budgets invariants:
        # - soft budget (task_budget.total) >= TASK_BUDGET_MIN_TOKENS
        # - hard ceiling (max_tokens) = ceil(budget * TASK_BUDGET_HARD_CEILING_RATIO)
        # task_budget is a hint that lets Claude finish mid-sentence
        # when it's close to done; max_tokens is the model-side cap.
        # Per Anthropic docs (2026-04-20): total is soft, max_tokens
        # is hard. Verdict sets both so the judge finishes gracefully
        # without over-spend.
        body: Dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        # Prompt caching: wrap the system prompt in a cached content
        # block. The beta headers stack — 1h TTL requires the extended
        # beta alongside any other beta (e.g. task_budgets).
        beta_headers: List[str] = []
        if self.prompt_cache_ttl:
            body["system"] = [build_cached_system_block(system, self.prompt_cache_ttl)]
            if self.prompt_cache_ttl == "1h":
                beta_headers.append(EXTENDED_CACHE_TTL_BETA)
        else:
            body["system"] = system

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
        }
        if self.budget_tokens:
            soft_budget = max(int(self.budget_tokens), TASK_BUDGET_MIN_TOKENS)
            beta_headers.append(TASK_BUDGETS_BETA)
            body["output_config"] = {
                "task_budget": {"type": "tokens", "total": soft_budget},
            }
            # Raise max_tokens to the hard ceiling when the caller asked
            # for less — otherwise the soft budget can never kick in.
            hard_ceiling = int(soft_budget * TASK_BUDGET_HARD_CEILING_RATIO)
            body["max_tokens"] = max(max_tokens, hard_ceiling)
            if self.log_budget_countdown:
                print(
                    f"[llm_judge] task_budget soft={soft_budget} "
                    f"hard_ceiling={body['max_tokens']} model={model}",
                    file=sys.stderr,
                )
        if beta_headers:
            # Multiple betas join with ", " per the anthropic-beta spec.
            headers["anthropic-beta"] = ", ".join(beta_headers)

        req = urllib.request.Request(
            ANTHROPIC_MESSAGES_URL,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
            raise LLMJudgeError(f"Anthropic API HTTP {exc.code}: {detail[:400]}")
        except urllib.error.URLError as exc:
            raise LLMJudgeError(f"Anthropic API unreachable: {exc}")

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise LLMJudgeError(f"Anthropic response was not JSON: {exc}")

        if self.log_cache_usage and self.prompt_cache_ttl:
            _log_cache_usage(data, model)

        return _extract_text(data)


def _log_cache_usage(response: Dict[str, Any], model: str) -> None:
    """Emit a cache-hit / cache-miss counter to stderr for observability.

    Reads ``usage.cache_read_input_tokens`` (hit) and
    ``usage.cache_creation_input_tokens`` (miss) from the Messages API
    response. Silent when neither field is present — pre-caching hosts
    won't return them and Verdict shouldn't log noise.
    """
    usage = response.get("usage")
    if not isinstance(usage, dict):
        return
    hits = usage.get("cache_read_input_tokens") or 0
    misses = usage.get("cache_creation_input_tokens") or 0
    if not (hits or misses):
        return
    print(
        f"[llm_judge] cache_hit={hits} cache_miss={misses} model={model}",
        file=sys.stderr,
    )


def _extract_text(response: Dict[str, Any]) -> str:
    """Return the concatenated text blocks from a Claude messages response."""
    content = response.get("content", [])
    if not isinstance(content, list):
        raise LLMJudgeError("Anthropic response missing 'content' array")
    out: List[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if isinstance(text, str):
                out.append(text)
    return "\n".join(out)


def truncate_transcript(lines: List[str], max_chars: int = MAX_TRANSCRIPT_CHARS) -> str:
    """Flatten + trim to ``max_chars``, keeping head and tail context.

    When the transcript is over budget the middle is replaced with a
    marker that records how many characters were dropped. Keeping both
    ends preserves the user intent (prompt at the top) and the result
    (output at the bottom).
    """
    joined = "\n".join(lines)
    if len(joined) <= max_chars:
        return joined
    half = max_chars // 2
    head = joined[:half]
    tail = joined[-half:]
    elided = len(joined) - max_chars
    return f"{head}\n\n... [{elided} chars elided to stay under the {max_chars}-char transcript budget] ...\n\n{tail}"


def _rubric_criteria_summary(rubric: Dict[str, Any]) -> str:
    """Render the rubric's per-dimension criteria as a compact string.

    Accepts either the pre-parsed criteria dict (dimension → criteria
    string) produced by ``score._parse_rubric_criteria`` or a richer
    ``{"name": "...", "criteria": {...}}`` envelope.
    """
    criteria = rubric.get("criteria") if isinstance(rubric.get("criteria"), dict) else rubric
    lines: List[str] = []
    for dim in DIMENSIONS:
        text = criteria.get(dim) if isinstance(criteria, dict) else None
        if not text:
            continue
        # Keep each dimension's criteria terse — Haiku can re-read the
        # full rubric file if the maintainer wants to, but we don't
        # pipe it wholesale through the API call.
        excerpt = text.strip()
        if len(excerpt) > 600:
            excerpt = excerpt[:600] + " ..."
        lines.append(f"- {dim}: {excerpt}")
    return "\n".join(lines) if lines else "(no per-dimension criteria provided)"


SYSTEM_PROMPT = (
    "You are Verdict's second-opinion judge. Score the transcript on the "
    "seven dimensions below, each on a 1-10 integer scale. Reply with a "
    "single JSON object mapping each dimension name to "
    '{"score": <int 1-10>, "justification": "<one sentence>"}. '
    "No prose outside the JSON."
)


def build_prompt(transcript: List[str], rubric: Dict[str, Any]) -> str:
    """Compose the user-facing prompt for a single evaluation call."""
    excerpt = truncate_transcript(transcript)
    criteria = _rubric_criteria_summary(rubric)
    dims = ", ".join(DIMENSIONS)
    return (
        f"Rubric: {rubric.get('name', 'default')}\n"
        f"Dimensions: {dims}\n\n"
        f"Per-dimension criteria:\n{criteria}\n\n"
        f"---BEGIN TRANSCRIPT---\n{excerpt}\n---END TRANSCRIPT---\n\n"
        f"Return only the JSON object."
    )


_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_scores(response_text: str) -> Dict[str, Tuple[int, str]]:
    """Parse the LLM response text into a ``{dim: (score, justification)}`` dict.

    Tolerates: leading/trailing prose, triple-backtick fences, minor
    trailing commas. Any dimension missing from the response is
    omitted (caller merges selectively). Scores outside 1-10 are
    clamped; non-numeric scores are skipped with a warning.
    """
    # Strip markdown fences if the model wrapped its output.
    cleaned = response_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    match = _JSON_OBJECT_RE.search(cleaned)
    if not match:
        raise LLMJudgeError(f"LLM response did not contain a JSON object: {response_text[:200]!r}")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        # Second-chance: strip trailing commas (common LLM slop).
        repaired = re.sub(r",(\s*[}\]])", r"\1", match.group(0))
        try:
            data = json.loads(repaired)
        except json.JSONDecodeError:
            raise LLMJudgeError(f"LLM response was not valid JSON: {exc}")

    if not isinstance(data, dict):
        raise LLMJudgeError("LLM response root was not an object")

    out: Dict[str, Tuple[int, str]] = {}
    for dim in DIMENSIONS:
        entry = data.get(dim)
        if not isinstance(entry, dict):
            continue
        raw_score = entry.get("score")
        if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            continue
        score = int(round(raw_score))
        score = max(1, min(10, score))
        justification = entry.get("justification", "")
        if not isinstance(justification, str):
            justification = str(justification)
        out[dim] = (score, justification.strip())
    return out


def score_with_llm(
    transcript: List[str],
    rubric: Dict[str, Any],
    model: str = "claude-haiku-4-5",
    client: Optional[LLMClient] = None,
    max_response_tokens: int = 2048,
) -> Dict[str, Tuple[int, str]]:
    """Return a per-dimension (score, justification) dict from the LLM.

    *transcript*: list of transcript lines as produced by
        ``score.load_transcript`` (pre-adapter output).
    *rubric*: either the parsed criteria dict produced by
        ``score._parse_rubric_criteria`` or a richer envelope with
        ``{"name": "...", "criteria": {...}}``.
    *model*: any Claude model ID. Default ``claude-haiku-4-5`` keeps
        the opt-in second opinion cheap (≈$1/MTok input).
    *client*: injectable for tests. When ``None``, a default
        :class:`AnthropicClient` is constructed from
        ``ANTHROPIC_API_KEY``.

    Raises :class:`LLMJudgeError` on API failures or unparseable
    responses. The caller (``score.build_scorecard``) is expected to
    catch that and degrade to heuristics-only.
    """
    if client is None:
        client = AnthropicClient(prompt_cache_ttl=resolve_cache_ttl_from_env())
    prompt = build_prompt(transcript, rubric)
    response_text = client.messages_create(
        model=model,
        system=SYSTEM_PROMPT,
        prompt=prompt,
        max_tokens=max_response_tokens,
    )
    return parse_scores(response_text)
