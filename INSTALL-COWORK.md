# Installing Proofloop on Claude Cowork

Proofloop ships as a dual-platform plugin (`claude-code` + `claude-cowork`).
The standard marketplace install flow works on both platforms, but Cowork
currently has an open plugin-loading issue that affects some
organizations. This guide covers the canonical path and the workaround.

## Recommended: marketplace install

```shell
/plugin marketplace add sattyamjjain/proofloop
/plugin install proofloop@proofloop
```

This clones the repo into Cowork's plugin cache, wires up the Stop /
SubagentStop / StopFailure hooks, registers the four slash commands, and
installs the `judge-agent` read-only evaluator. No further steps are
required; the first skill execution that matches an `always` entry in
`judge-config.json` will trigger an auto-scored run.

## Workaround: direct zip upload (GH #39400)

Some Cowork tenants surface an error like:

```
Plugin failed to load: components.skills path ./skills/judge/SKILL.md
not resolvable under plugin cache.
```

The root cause is Cowork's plugin-cache symlink resolution, tracked in
[anthropics/claude-code#39400](https://github.com/anthropics/claude-code/issues/39400).
Until it lands, use the zip-upload path:

1. Download the latest release tarball:

   ```shell
   gh release download v1.1.0 \
     --repo sattyamjjain/proofloop \
     --pattern 'proofloop-*.zip'
   ```

2. In Cowork → **Settings** → **Plugins** → **Upload**, select the
   downloaded zip. Cowork installs the plugin as a self-contained unit
   and bypasses the cache-symlink path.

3. Verify with `/judge-config` — it should print the current
   auto-judge allowlist without errors.

## Verifying installation

After install, run any skill that is on the `always` list (e.g.
`/code-review`). When the turn ends, Proofloop posts a single-line
scorecard via the Stop hook:

```
Proofloop: code-review → 8.7/10 (A-). Solid execution with minor areas
for improvement.
```

If no line appears:

- `jq`, `bc`, and `python3` must be on `$PATH`. Install via
  `brew install jq bc` on macOS or `apt-get install jq bc` on Debian.
- Check `skills/judge/scores/` for a new JSON file. If present, the
  scorecard was written but the hook stdout was suppressed — typically
  a Cowork permission-mode issue. Re-run with `--permission-mode
  default`.
- For `always` matches that still aren't scored, confirm the skill name
  shows up in the transcript via one of the four detection patterns in
  `hooks/common.sh:29`.

## Uninstalling

```shell
/plugin uninstall proofloop@proofloop
/plugin marketplace remove proofloop
```

Score history in `skills/judge/scores/` is not deleted automatically —
remove it by hand if you want a clean slate, or keep it for `/scorecard`
to render trends after reinstalling.

## Supported Cowork plans

Routines-driven scoring is supported on all Cowork plans that include
Claude Code on the web. Each Routine run is a normal Claude Code
session: the routine prompt is the user turn, and Proofloop's Stop hook
fires at the end exactly as it would in an interactive session. No
`--mode routine` flag is required — the routine prompt is visible to
Proofloop through the normal transcript.
