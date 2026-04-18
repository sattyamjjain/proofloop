# Transcript fixtures

Canonical examples per ecosystem. Used by `tests/test_adapter_fixtures.py`
to guarantee each adapter keeps extracting lines correctly when an
ecosystem's format shifts.

Fixtures are anonymised and kept minimal — one or two turns each,
enough to exercise every branch of the corresponding adapter
(content-as-string, content-as-blocks, tool_calls, etc.).

| File                             | Ecosystem        | Adapter name        | Covers                          |
| -------------------------------- | ---------------- | ------------------- | ------------------------------- |
| `claude-code.jsonl`              | Claude Code      | `claude-code`       | JSONL + content-block list      |
| `cowork.jsonl`                   | Cowork           | `cowork`            | JSONL with `routine_id` marker  |
| `openai-compatible-array.json`   | Cursor/Continue  | `openai-compatible` | Top-level JSON array            |
| `openai-compatible-messages.json`| Cursor/Continue  | `openai-compatible` | `{messages: [...]}` envelope    |
| `openai-compatible-jsonl.jsonl`  | Cursor/Continue  | `openai-compatible` | JSONL one-message-per-line      |
| `openai-compatible-tools.json`   | Cursor/Continue  | `openai-compatible` | `tool_calls` flattening         |
| `codex.md`                       | OpenAI Codex CLI | `codex`             | Markdown-style session          |
| `codex-sidecar.json`             | OpenAI Codex CLI | `codex`             | JSON sidecar delegates OpenAI   |

When an ecosystem changes its format, update the fixture *and* the
adapter together so the test pins the new behaviour. Never rely on
live transcripts from your own sessions — they contain identifying
data and drift as the ecosystem evolves.
