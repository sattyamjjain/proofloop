# CI workflow staging

`ci/workflow.yml` contains the CI pipeline for Verdict. It lives here
rather than at `.github/workflows/ci.yml` because the OAuth token used
to land the v1.1.0 release lacked the `workflow` scope, and GitHub
rejects writes to `.github/workflows/*` without it.

## One-line install

From the repo root, with a `gh` session that has `workflow` scope:

```shell
./ci/install.sh
```

The script:
1. Creates `.github/workflows/` if missing.
2. Moves `ci/workflow.yml` → `.github/workflows/ci.yml`.
3. Stages + commits the move with a conventional-commits message.

To get `workflow` scope on your token: `gh auth refresh -h github.com -s workflow`.
You'll be bounced through a browser once; subsequent commands use the
refreshed token transparently.

## Pipeline contents

The workflow runs on every PR and push to `main`, across Python 3.9 /
3.11 / 3.12:

- `python3 -m unittest discover tests/`
- `python3 scripts/validate_marketplace.py`
- `python3 scripts/benchmark_pack.py`
- `shellcheck hooks/*.sh`

All four gates are already passing locally at release time; the
workflow just formalises them as PR checks.
