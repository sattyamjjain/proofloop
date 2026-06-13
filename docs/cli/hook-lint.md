# `proofloop hook lint` CLI

Static analyzer for Claude Code PostToolUse hook scripts. Flags
safety-relevant patterns in the hook **source** so adopters can
catch issues in CI before any rewrite happens.

## Usage

```shell
python3 skills/judge/scripts/hook_lint.py path/to/hook.sh
```

Supported extensions: `.sh`, `.bash`, `.py`, `.js`, `.mjs`, `.ts`.

## Rule set

- **F1 — undisclosed-mutation** — the hook writes
  `updatedToolOutput` but never emits a
  `[hook-rewrote: <tool>]` disclosure marker downstream tooling
  can pick up.
- **F2 — missing-source-tag** — the hook discloses rewrites but
  doesn't emit `[hook-source: <path>]`, so an audit cannot trace
  the rewrite to its source.
- **F3 — error-suppression-without-justification** — the hook
  flips `error: true → false` without an
  `[error-suppressed-by-design: <reason>]` marker.
- **F4 — credential-leak-in-output** — the hook source contains
  a literal credential-shaped string (sk-…, AKIA…, ghp_…,
  AIza…, PRIVATE KEY block). High-severity defensive check.

## Comment-stripping

The linter strips `#`-prefixed and `//`-prefixed comment-only
lines before signal detection, so a comment that mentions
`updatedToolOutput` or `[hook-rewrote: ...]` does not false-flag.

## Exit codes

- `0` — clean.
- `1` — at least one finding.
- `2` — bad input (missing file, unsupported extension).
