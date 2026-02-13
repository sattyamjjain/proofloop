#!/bin/bash
# Verdict — Detect which skill was used from a transcript
set -euo pipefail

TRANSCRIPT_PATH="${1:-}"

if [ -z "$TRANSCRIPT_PATH" ] || [ ! -f "$TRANSCRIPT_PATH" ]; then
  echo "Usage: detect-skill.sh <transcript-path>" >&2
  exit 1
fi

# Try multiple detection patterns
# Pattern 1: skills/*/SKILL.md
SKILL=$(grep -oP '(?<=skills/)[^/]+(?=/SKILL\.md)' "$TRANSCRIPT_PATH" 2>/dev/null | tail -1)
[ -n "$SKILL" ] && echo "$SKILL" && exit 0

# Pattern 2: Skill tool invocation
SKILL=$(grep -oP '(?<=Skill tool invoked: )[a-zA-Z0-9_-]+' "$TRANSCRIPT_PATH" 2>/dev/null | tail -1)
[ -n "$SKILL" ] && echo "$SKILL" && exit 0

# Pattern 3: "skill": "name" in JSON
SKILL=$(grep -oP '(?<="skill":\s?")[a-zA-Z0-9_-]+' "$TRANSCRIPT_PATH" 2>/dev/null | tail -1)
[ -n "$SKILL" ] && echo "$SKILL" && exit 0

# Pattern 4: /skill-name command
SKILL=$(grep -oP '(?<=^/)[a-zA-Z0-9_-]+' "$TRANSCRIPT_PATH" 2>/dev/null | head -1)
[ -n "$SKILL" ] && echo "$SKILL" && exit 0

echo ""
exit 0
