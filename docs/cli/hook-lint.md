# `verdict hook lint` CLI (T3)

Static analyzer for Claude Code PostToolUse hook scripts. The
`tool-output-rewrite` rubric (CC1) scores transcripts on hook
behavior; `hook lint` scores the hook **source** so adopters can
catch issues in CI before any rewrite happens.

## Usage

```shell
python3 skills/judge/scripts/hook_lint.py path/to/hook.sh
```

Supported extensions: `.sh`, `.bash`, `.py`, `.js`, `.mjs`, `.ts`.

## Rule set

- **F1 — undisclosed-mutation** — hook writes `updatedToolOutput`
  but never emits `[hook-rewrote: <tool>]`. Adopters running the
  CC1 rubric will fail their transcripts.
- **F2 — missing-source-tag** — hook discloses rewrites but
  doesn't emit `[hook-source: <path>]`. CC1 audit-link dimension
  caps at ≤ 5.0.
- **F3 — error-suppression-without-justification** — hook flips
  `error: true → false` without `[error-suppressed-by-design:
  <reason>]`. CC1 rubber-stamp red flag will fire (composite
  caps at ≤ 4.0).
- **F4 — credential-leak-in-output** — hook source contains a
  literal credential-shaped string (sk-…, AKIA…, ghp_…, AIza…,
  PRIVATE KEY block). High-severity defensive check.

## Comment-stripping

The linter strips `#`-prefixed and `//`-prefixed comment-only
lines before signal detection. So a comment that mentions
`updatedToolOutput` or `[hook-rewrote: ...]` doesn't false-flag.

## Exit codes

- `0` — clean.
- `1` — at least one finding.
- `2` — bad input (missing file, unsupported extension).

## Examples

`examples/hooks/compliant-rewrite-hook.sh` shows the canonical
shape: emit byte-delta + source tag + disclosure marker.

`examples/hooks/non-compliant-rewrite-hook.sh` shows the failure
shape: mutate output silently, suppress errors silently.
