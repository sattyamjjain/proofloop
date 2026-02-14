#!/bin/bash
# Verdict — Detect which skill was used from a transcript
# Delegates to the shared detect_skill_from_transcript() in common.sh
set -euo pipefail

TRANSCRIPT_PATH="${1:-}"

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
  echo "Usage: detect-skill.sh <transcript-path>" >&2
  exit 1
fi

# Source shared detection logic from hooks/common.sh
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
source "$PLUGIN_ROOT/hooks/common.sh"

SKILL=$(detect_skill_from_transcript "$TRANSCRIPT_PATH")
echo "$SKILL"
exit 0
