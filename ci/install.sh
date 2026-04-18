#!/bin/bash
# Move ci/workflow.yml into .github/workflows/ and commit.
#
# Requires a gh token with the `workflow` scope. Run once, from the
# repo root, after landing the v1.1.0 release. See ci/README.md.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

SRC="ci/workflow.yml"
DEST_DIR=".github/workflows"
DEST="${DEST_DIR}/ci.yml"

if [ ! -f "$SRC" ]; then
  echo "Error: $SRC not found. Has it already been installed?" >&2
  exit 1
fi
if [ -f "$DEST" ]; then
  echo "Error: $DEST already exists. Aborting to avoid overwriting." >&2
  exit 1
fi

mkdir -p "$DEST_DIR"
git mv "$SRC" "$DEST"
rmdir ci 2>/dev/null || true

git commit -m "ci: activate PR workflow (moved from ci/ to .github/workflows/)

Runs tests + validate_marketplace + benchmark_pack + shellcheck on
every PR. Was staged under ci/ because the release-time gh token
lacked workflow scope."
echo "Workflow installed at $DEST. Push to trigger the first run."
