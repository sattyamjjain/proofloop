# Research log

Citations and retrieval dates for every external claim that shapes
Verdict's implementation. Add a new entry each time you verify a spec
before shipping code that depends on it.

## 2026-04-18 — Claude Code hooks reference

**URL:** <https://code.claude.com/docs/en/hooks>

- The hook event set as of April 2026 is: `SessionStart`, `UserPromptSubmit`,
  `PreToolUse`, `PermissionRequest`, `PermissionDenied`, `PostToolUse`,
  `PostToolUseFailure`, `Notification`, `SubagentStart`, `SubagentStop`,
  `TaskCreated`, `TaskCompleted`, `Stop`, `StopFailure`, `TeammateIdle`,
  `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `FileChanged`,
  `WorktreeCreate`, `WorktreeRemove`, `PreCompact`, `PostCompact`,
  `Elicitation`, `ElicitationResult`, `SessionEnd`.
- **No `agent` event.** Earlier planning documents referenced one; the
  correct equivalents are `SubagentStart` and `SubagentStop`.
- `SubagentStop` payload (confirmed April 2026): `session_id`,
  `transcript_path`, `cwd`, `permission_mode`, `hook_event_name`,
  `stop_hook_active`, `agent_id`, `agent_type`,
  `agent_transcript_path`, `last_assistant_message`. The subagent's own
  transcript is at `agent_transcript_path` — Verdict should score that
  file when it is present, falling back to `transcript_path` otherwise.
- `StopFailure` fires when the turn ends due to an API error
  (rate_limit / authentication_failed / billing_error / invalid_request /
  server_error / max_output_tokens / unknown). Output/exit code are
  ignored. Verdict should not auto-judge on this event.
- Default timeouts: command hooks 600s, prompt hooks 30s, agent hooks
  60s. Verdict currently specifies `"timeout": 120` explicitly.
- Exit codes: 0 success; 2 blocks (effect varies per event); any other
  non-zero is a non-blocking error.

## 2026-04-18 — Plugin marketplace spec

**URL:** <https://code.claude.com/docs/en/plugin-marketplaces>

- `.claude-plugin/marketplace.json` required fields: `name` (kebab-case),
  `owner` (object with `name` required, `email` optional), `plugins`
  (array).
- Optional top-level: `metadata.description`, `metadata.version`,
  `metadata.pluginRoot`.
- Plugin entries require `name` and `source`. Source can be a relative
  string (`./path`) or one of `{source: "github", repo, ref?, sha?}`,
  `{source: "url", url, ref?, sha?}`, `{source: "git-subdir", url, path,
  ref?, sha?}`, `{source: "npm", package, version?, registry?}`.
- Plugin-entry optional fields mirror the plugin manifest: `description`,
  `version`, `author`, `homepage`, `repository`, `license`, `keywords`,
  `category`, `tags`, `strict`, plus component overrides
  (`skills`, `commands`, `agents`, `hooks`, `mcpServers`, `lspServers`).
- **Reserved marketplace names** include `claude-plugins-official`,
  `anthropic-plugins`, `agent-skills`, and impersonation variants —
  Verdict's `"name": "verdict"` is fine.
- Schema URL `https://anthropic.com/claude-code/marketplace.schema.json`
  is referenced but does not resolve (confirmed via
  <https://github.com/anthropics/claude-code/issues/9686>). Validation
  should rely on reading the docs, not fetching the schema.

## 2026-04-18 — Routines

**URL:** <https://code.claude.com/docs/en/routines>

- Routines launched 2026-04-14 as research preview. Scheduled, API, and
  GitHub triggers all produce **normal Claude Code cloud sessions** with
  the routine prompt acting as the user turn.
- Implication for Verdict: the existing `Stop` hook fires normally when
  a routine finishes. No `--mode routine` flag is required to handle a
  "missing user turn" — the user turn is the routine prompt. Document
  the behavior; no transcript-format change.
- API trigger beta header: `anthropic-beta: experimental-cc-routine-2026-04-01`.
  Shape may change during preview.

## 2026-04-18 — Claude Opus 4.7 + tokenizer

**URL:** <https://platform.claude.com/docs/en/about-claude/models/overview>
**URL:** <https://www.claudecodecamp.com/p/i-measured-claude-4-7-s-new-tokenizer-here-s-what-it-costs-you>

- Current canonical model IDs:
  - `claude-opus-4-7` (Opus 4.7) — 1M context, 128k max output
  - `claude-sonnet-4-6` (Sonnet 4.6) — 1M context, 64k max output
  - `claude-haiku-4-5-20251001` (alias `claude-haiku-4-5`) — 200k
    context, 64k max output
- Opus 4.7 uses a new tokenizer that produces **~1.0x–1.35x** as many
  tokens as Opus 4.6 for the same text (up to 35% more, content-dependent).
- Verdict uses line/char counts, not real tokens, so the tokenizer
  change affects length-based thresholds indirectly. Model-aware scaling
  of the efficiency thresholds (2000/1000 lines) prevents first-run
  regressions when the same skill moves to Opus 4.7.
