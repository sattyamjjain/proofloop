"""Claude Code native transcript adapter.

Claude Code and Cowork write transcripts as JSONL, one record per line.
Records include ``{"role": "...", "content": "..."}`` for user /
assistant turns and ``{"type": "tool_use", ...}`` or similar for tool
calls. This is Verdict's reference format — extraction is a lightweight
re-expression of ``score.load_transcript`` that stays adapter-agnostic.

Auto Memory (Opus 4.7, 2026-04-17+)
-----------------------------------
A single "transcript" may span many ``~/.claude/history/*.jsonl`` files
plus a memory preamble that Claude Code injects at the top of every
new session. To handle that, ``extract_lines`` accepts EITHER a file
path OR a directory:

- **File**: behaviour identical to pre-1.2 Verdict.
- **Directory**: enumerate ``*.jsonl`` sorted by mtime (oldest first),
  concatenate the extracted lines, and inject a ``--- session break ---``
  marker between files so downstream heuristics can attribute signals
  to the right session.

Memory preambles are recognised by any of these tokens at the top of
the first session's payload: ``memory_block``, ``<memory>``,
``auto-memory``, ``claude_memory``. Lines inside a memory block are
prefixed with ``[system-memory]`` so ``score.py`` can choose to treat
them as system context rather than user-turn output.

Managed agents (``managed-agents-2026-04-01`` beta)
---------------------------------------------------
Parallel sub-agents share state through a server-managed memory
endpoint. Claude Code streams synthetic records into the JSONL
transcript whenever a managed sub-agent reads from or writes to the
shared store. These records carry tokens like ``managed_memory_v1``,
``agent_memory``, or ``parent_agent_id``. Verdict tags pull events
with ``[managed-memory-pull]`` and push events with
``[managed-memory-push]`` so the scoring engine can tell apart first-
party reasoning from memory stitching.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

SESSION_BREAK_MARKER: str = "--- session break ---"
MEMORY_PREFIX: str = "[system-memory] "
MANAGED_MEMORY_PULL_PREFIX: str = "[managed-memory-pull] "
MANAGED_MEMORY_PUSH_PREFIX: str = "[managed-memory-push] "

# CC1 — Tool-output-rewrite tagging. Claude Code v2.1.121 (2026-04-29)
# lets a PostToolUse hook return ``hookSpecificOutput.updatedToolOutput``
# and the model sees the rewritten payload. This adapter tags such
# rewrites with ``[hook-rewrote: <tool>] [hook-byte-delta: <ratio>]``
# so the score.py CC1 helper can detect undisclosed rewrites,
# rubber-stamps, and credential injection.
HOOK_REWRITE_TAG: str = "[hook-rewrote: {tool}]"
HOOK_BYTE_DELTA_TAG: str = "[hook-byte-delta: {ratio}]"

# CC4 — Anthropic Routines (research preview) trajectory shape.
# When a transcript carries an explicit ``[routine_trigger: <id>]``
# marker OR (env opt-in) has no human turn in the first 5 lines,
# the adapter prepends a ``[trajectory_kind: routine]`` sentinel
# so the consistency analyzer can relax std_dev tolerances
# (cron-triggered runs cluster differently from interactive ones).
# See Issue O15 — the heuristic branch is opt-in by env to avoid
# false-flagging multi-line interactive paste-ins.
TRAJECTORY_KIND_ROUTINE: str = "[trajectory_kind: routine]"
ROUTINE_DETECTION_ENV: str = "VERDICT_DETECT_ROUTINE_HEURISTIC"
_ROUTINE_TRIGGER_RE: re.Pattern = re.compile(
    r"\[routine_trigger:\s*([A-Za-z0-9_.-]+)\]", re.IGNORECASE,
)

_MEMORY_TOKENS = ("memory_block", "<memory>", "auto-memory", "claude_memory")
_MANAGED_MEMORY_TOKENS = ("managed_memory_v1", "agent_memory", "parent_agent_id")
_MANAGED_PULL_OPS = frozenset({
    "read", "pull", "fetch", "load", "get", "retrieve",
})
_MANAGED_PUSH_OPS = frozenset({
    "write", "push", "store", "save", "set", "commit", "append",
})


def _is_memory_marker(text: str) -> bool:
    lowered = text.lower()
    return any(token in lowered for token in _MEMORY_TOKENS)


def _is_managed_memory_record(record: Dict[str, Any], raw_text: str) -> bool:
    """Detect managed-agents ``managed-agents-2026-04-01`` memory records."""
    lowered = raw_text.lower()
    if any(token in lowered for token in _MANAGED_MEMORY_TOKENS):
        return True
    for key in ("type", "event", "record_type"):
        value = record.get(key)
        if isinstance(value, str) and any(
            token in value.lower() for token in _MANAGED_MEMORY_TOKENS
        ):
            return True
    return False


def _managed_memory_prefix(record: Dict[str, Any], raw_text: str) -> str:
    """Choose pull vs push prefix based on the record's op/event fields."""
    for key in ("op", "operation", "direction", "action", "event", "type"):
        value = record.get(key)
        if isinstance(value, str):
            lowered = value.lower()
            if any(token in lowered for token in _MANAGED_PUSH_OPS):
                return MANAGED_MEMORY_PUSH_PREFIX
            if any(token in lowered for token in _MANAGED_PULL_OPS):
                return MANAGED_MEMORY_PULL_PREFIX
    # Fall back to payload-body heuristics before defaulting to pull.
    lowered = raw_text.lower()
    if any(tok in lowered for tok in _MANAGED_PUSH_OPS):
        return MANAGED_MEMORY_PUSH_PREFIX
    return MANAGED_MEMORY_PULL_PREFIX


def _extract_from_record(record: dict, raw_line: str, in_memory: bool) -> List[str]:
    """Pull readable text out of a single JSONL record.

    ``raw_line`` is the stripped input line, used as the fallback when
    no known text field is present — preserves pre-v1.2 byte-for-byte
    behaviour for the no-match branch.
    """
    out: List[str] = []
    for key in ("content", "text", "message", "output", "data"):
        value = record.get(key)
        if isinstance(value, str) and value:
            out.append(value)
            break
        if isinstance(value, list):
            # Claude Code blocks: [{"type":"text","text":"..."}, ...]
            for block in value:
                if isinstance(block, dict):
                    if isinstance(block.get("text"), str):
                        out.append(block["text"])
                    elif isinstance(block.get("content"), str):
                        out.append(block["content"])
            break
    else:
        out.append(raw_line)
    if _is_managed_memory_record(record, raw_line):
        prefix = _managed_memory_prefix(record, raw_line)
        out = [prefix + line for line in out]
    elif in_memory:
        out = [MEMORY_PREFIX + line for line in out]
    rewrite = _detect_hook_rewrite(record, raw_line)
    if rewrite is not None:
        tag = (
            HOOK_REWRITE_TAG.format(tool=rewrite["tool"])
            + " "
            + HOOK_BYTE_DELTA_TAG.format(ratio=rewrite["byte_delta"])
        )
        # Surface the hookSpecificOutput.updatedToolOutput phrase verbatim
        # so the score.py CC1 helper can also detect undisclosed paths
        # (cases where future Claude Code revisions emit the field
        # without the matching adapter-side disclosure tag).
        out = [
            tag + " hookSpecificOutput.updatedToolOutput "
            + (rewrite["rewritten"] if not line else line)
            for line in (out or [""])
        ]
    return out


def _detect_hook_rewrite(record: Dict[str, Any], raw_text: str) -> Optional[Dict[str, Any]]:
    """Return rewrite metadata if *record* carries a v2.1.121 tool-output rewrite.

    Looks for the canonical Claude Code v2.1.121 shape:
    ``record["hookSpecificOutput"]["updatedToolOutput"]`` (or a flattened
    ``"hookSpecificOutput.updatedToolOutput"`` substring in the raw text
    as a defensive fallback). Returns ``{"tool", "byte_delta", "tool_use_id",
    "rewritten"}`` or ``None``.

    The byte-delta is computed against ``record["original_tool_output"]``
    when available; absent that, returns ``1.0`` (no comparison possible)
    and lets the score.py helper flag the gap downstream.
    """
    spec = record.get("hookSpecificOutput") if isinstance(record, dict) else None
    rewritten = None
    if isinstance(spec, dict):
        rewritten = spec.get("updatedToolOutput")
    if rewritten is None and "hookSpecificOutput.updatedToolOutput" in raw_text:
        # Defensive: caller flattened the JSON; we can't recover the
        # rewritten payload, but we still emit a disclosure.
        rewritten = ""
    if rewritten is None:
        return None
    rewritten_str = str(rewritten) if not isinstance(rewritten, str) else rewritten
    tool = (
        record.get("tool")
        or record.get("tool_name")
        or (spec.get("tool") if isinstance(spec, dict) else None)
        or "unknown"
    )
    original = record.get("original_tool_output") or record.get("original")
    if isinstance(original, str) and original:
        ratio = len(rewritten_str) / max(1, len(original))
    else:
        ratio = 1.0
    return {
        "tool": str(tool),
        "byte_delta": round(ratio, 3),
        "tool_use_id": record.get("tool_use_id"),
        "rewritten": rewritten_str,
    }


def _detect_routine_triggered(lines: List[str]) -> bool:
    """Return True iff the transcript looks routine-triggered.

    Two signals (CC4):

    1. Any line carries ``[routine_trigger: <id>]`` — explicit, always honored.
    2. (Heuristic) No line in the first 5 looks like a human-role turn —
       env-gated via ``VERDICT_DETECT_ROUTINE_HEURISTIC=1`` to avoid
       false-flagging multi-line interactive paste-ins. See Issue O15.
    """
    for line in lines:
        if _ROUTINE_TRIGGER_RE.search(line):
            return True
    if os.environ.get(ROUTINE_DETECTION_ENV) != "1":
        return False
    # Heuristic branch: check the first 5 lines for any human-role marker.
    head = lines[:5]
    human_markers = ("user:", '"role":"user"', "[user]", "user>")
    for line in head:
        lowered = line.lower()
        if any(marker in lowered for marker in human_markers):
            return False
    # Also bail if the head is empty.
    return bool(head)


def _extract_lines_from_file(path: Path) -> List[str]:
    """Return one readable line per meaningful JSONL record in *path*."""
    if not path.is_file():
        return []
    out: List[str] = []
    in_memory = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if not stripped:
            continue

        # Detect a memory preamble block on entry. Memory blocks end at
        # the first record that does NOT look like a memory marker and
        # carries a recognised role (user/assistant/system/tool). This
        # heuristic is deliberately loose — false positives only mean
        # the line gets a ``[system-memory]`` tag, they don't change
        # the heuristic scorer's pass/fail behaviour.
        if not stripped.startswith("{"):
            out.append(stripped)
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            out.append(stripped)
            continue

        role = record.get("role") if isinstance(record, dict) else None
        raw_text = json.dumps(record, separators=(",", ":")) if isinstance(record, dict) else stripped

        if not in_memory and _is_memory_marker(raw_text):
            in_memory = True
        # A user turn ends any active memory block.
        if role in ("user",):
            in_memory = False
        elif role in ("assistant", "tool") and in_memory and not _is_memory_marker(raw_text):
            # Once we see an assistant/tool turn that's no longer
            # marker-tagged, close the block.
            in_memory = False

        out.extend(_extract_from_record(
            record if isinstance(record, dict) else {},
            stripped,
            in_memory,
        ))
    return out


def parse_managed_agent_memory(lines: List[str]) -> List[str]:
    """Re-tag managed-agents memory records in an already-extracted line list.

    This is a post-processing pass for transcripts whose records reached
    the extractor via the raw-JSON fallback branch (records with no
    recognised content field). For each such line, if the JSON carries a
    managed-memory marker, replace it with a ``[managed-memory-pull]`` /
    ``[managed-memory-push]`` tagged version. Lines that already carry a
    managed-memory prefix are left untouched. Non-JSON lines pass
    through unchanged.

    The extractor already tags managed-memory records during the primary
    pass; this helper is exposed separately so callers working with a
    pre-extracted line list (e.g. archived scorecards or third-party
    tools) can still reclaim the tagging.
    """
    out: List[str] = []
    for line in lines:
        if line.startswith(MANAGED_MEMORY_PULL_PREFIX) or line.startswith(
            MANAGED_MEMORY_PUSH_PREFIX
        ):
            out.append(line)
            continue
        stripped = line.strip()
        if not (stripped.startswith("{") and stripped.endswith("}")):
            out.append(line)
            continue
        try:
            record = json.loads(stripped)
        except json.JSONDecodeError:
            out.append(line)
            continue
        if not isinstance(record, dict):
            out.append(line)
            continue
        if not _is_managed_memory_record(record, stripped):
            out.append(line)
            continue
        for key in ("content", "text", "snippet", "value"):
            value = record.get(key)
            if isinstance(value, str) and value:
                body = value
                break
        else:
            body = stripped
        out.append(_managed_memory_prefix(record, stripped) + body)
    return out


def extract_lines(path: str) -> List[str]:
    """Return one text line per meaningful record in a Claude Code transcript.

    Accepts either a regular file path or a directory of ``*.jsonl``
    session files (Auto Memory layout). Returned lines are flat; session
    boundaries in multi-file input are denoted by the
    :data:`SESSION_BREAK_MARKER` line. Memory-preamble lines are
    prefixed with :data:`MEMORY_PREFIX`. Managed-agents memory pulls /
    pushes are prefixed with :data:`MANAGED_MEMORY_PULL_PREFIX` or
    :data:`MANAGED_MEMORY_PUSH_PREFIX`.
    """
    source = Path(path)
    if source.is_dir():
        # Sort by mtime, using the filename as a stable tie-breaker.
        # ``git clone`` stamps every checked-out file with the same
        # mtime, so an mtime-only sort collapses on fresh CI runners;
        # the filename fallback keeps ordering deterministic there
        # without breaking the mtime-wins behaviour in live Auto
        # Memory layouts where the session files are timestamped.
        session_files = sorted(
            (p for p in source.glob("*.jsonl") if p.is_file()),
            key=lambda p: (p.stat().st_mtime, p.name),
        )
        if not session_files:
            return []
        combined: List[str] = []
        for index, session_path in enumerate(session_files):
            if index > 0:
                combined.append(SESSION_BREAK_MARKER)
            combined.extend(_extract_lines_from_file(session_path))
        # Belt-and-braces: catch any managed-memory records whose content
        # field slipped through the primary tagging pass. The call is
        # idempotent — already-tagged lines pass through unchanged.
        tagged = parse_managed_agent_memory(combined)
        if _detect_routine_triggered(tagged):
            tagged = [TRAJECTORY_KIND_ROUTINE] + tagged
        return tagged
    out = parse_managed_agent_memory(_extract_lines_from_file(source))
    if _detect_routine_triggered(out):
        out = [TRAJECTORY_KIND_ROUTINE] + out
    return out
