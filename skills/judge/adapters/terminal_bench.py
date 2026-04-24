"""Terminal-Bench trajectory adapter (read-only).

Terminal-Bench is a shell-task leaderboard (`llm-stats.com/benchmarks/
terminal-bench`) that records each task run as a trajectory JSON with
an ordered ``steps`` array. Each step is a shell command the agent
issued plus the resulting stdout / stderr / exit-code tuple.

Verdict flattens that into a line stream that the heuristic scorer
and the ``terminal-bench`` rubric can both consume:

- ``[shell_cmd] <command>`` — always emitted, once per step.
- ``[stdout] <content>`` — only when the step produced stdout.
- ``[stderr:exit=<N>] <content>`` — always emitted so the scorer has
  the exit code, even when stderr is empty. The prefix form pins the
  exit code to the stderr turn so the correctness analyzer can read
  both in one pass.

The adapter is offline-first (stdlib only) and lazy: missing fields
degrade to empty lines rather than raising, and the whole file is
read at most once.

Market signal: `llm-stats.com/benchmarks/terminal-bench
<https://llm-stats.com/benchmarks/terminal-bench>`_.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, List

FINGERPRINT_TOKENS = (
    '"steps"',
    '"exit_code"',
    '"terminal_bench"',
)


def _stringify(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, separators=(",", ":"))
    except (TypeError, ValueError):
        return str(value)


def _step_lines(step: Any) -> Iterable[str]:
    if not isinstance(step, dict):
        return
    command = _stringify(step.get("command") or step.get("cmd"))
    if command:
        yield f"[shell_cmd] {command}"
    stdout = _stringify(step.get("stdout"))
    if stdout:
        yield f"[stdout] {stdout}"
    stderr = _stringify(step.get("stderr"))
    exit_code = step.get("exit_code")
    if exit_code is None:
        exit_code = step.get("exitCode")
    if exit_code is None:
        exit_code = step.get("returncode")
    # Exit-code turn is always emitted so consistency / correctness
    # analysers always have a pass/fail signal per step.
    exit_str = _stringify(exit_code) if exit_code is not None else "?"
    prefix = f"[stderr:exit={exit_str}]"
    yield f"{prefix} {stderr}" if stderr else prefix


def _iter_steps(payload: Any) -> Iterable[Any]:
    """Yield steps from any of the common Terminal-Bench envelopes."""
    if isinstance(payload, list):
        yield from payload
        return
    if not isinstance(payload, dict):
        return
    steps = payload.get("steps")
    if isinstance(steps, list):
        yield from steps
        return
    trajectory = payload.get("trajectory")
    if isinstance(trajectory, dict):
        nested = trajectory.get("steps")
        if isinstance(nested, list):
            yield from nested
            return
    # Some runners nest under {"result": {"steps": [...]}}.
    result = payload.get("result")
    if isinstance(result, dict):
        nested = result.get("steps")
        if isinstance(nested, list):
            yield from nested


def detect(head: bytes) -> bool:
    """Fingerprint the first bytes of a Terminal-Bench trajectory file."""
    if not head:
        return False
    try:
        text = head.decode("utf-8", errors="replace")
    except AttributeError:
        return False
    # Must carry BOTH the steps token AND an exit_code or explicit
    # terminal_bench marker; either alone is too generic.
    if '"terminal_bench"' in text:
        return True
    return '"steps"' in text and '"exit_code"' in text


def looks_like_terminal_bench(path: str, scan_bytes: int = 2048) -> bool:
    """Heuristic autoloader: does *path* head look like a Terminal-Bench trajectory?"""
    target = Path(path)
    if not target.is_file():
        return False
    try:
        with target.open("rb") as handle:
            head = handle.read(scan_bytes)
    except OSError:
        return False
    return detect(head)


def extract_lines(path: str) -> List[str]:
    """Flatten a Terminal-Bench trajectory JSON into Verdict-flavoured lines."""
    source = Path(path)
    if not source.is_file():
        return []
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    out: List[str] = []
    # Header metadata: the task name + agent model are useful context
    # for downstream analyzers (model-aware efficiency thresholds).
    if isinstance(payload, dict):
        meta = payload.get("task") or payload.get("task_id")
        if meta:
            out.append(f"[task] {_stringify(meta)}")
        model = payload.get("model") or payload.get("agent_model")
        if model:
            out.append(f"[model] {_stringify(model)}")
    for step in _iter_steps(payload):
        out.extend(_step_lines(step))
    return out
