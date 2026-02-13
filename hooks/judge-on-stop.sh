#!/bin/bash
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$PLUGIN_ROOT/hooks/common.sh"

# Read hook input from stdin
INPUT=$(cat)

# Extract transcript path from input
TRANSCRIPT_PATH=$(echo "$INPUT" | jq -r '.transcript_path // empty' 2>/dev/null)
[ -z "$TRANSCRIPT_PATH" ] && exit 0

# Detect which skill was used
SKILL_NAME=$(detect_skill_from_transcript "$TRANSCRIPT_PATH")
[ -z "$SKILL_NAME" ] && exit 0

# Check if this skill should be auto-judged
CONFIG_PATH="$PLUGIN_ROOT/judge-config.json"
SHOULD_JUDGE=$(should_auto_judge "$SKILL_NAME" "$CONFIG_PATH")
[ "$SHOULD_JUDGE" != "true" ] && exit 0

# Run the scoring engine
SCORECARD=$(python3 "$PLUGIN_ROOT/skills/judge/scripts/score.py" \
  --skill "$SKILL_NAME" \
  --transcript "$TRANSCRIPT_PATH" \
  --rubric-dir "$PLUGIN_ROOT/skills/judge/rubrics" \
  --scores-dir "$PLUGIN_ROOT/skills/judge/scores" \
  --config "$CONFIG_PATH" 2>&1) || {
    echo "SkillJudge: Scoring failed for $SKILL_NAME" >&2
    exit 0  # Don't block on scoring errors
  }

# Extract score and grade
SCORE=$(echo "$SCORECARD" | jq -r '.composite_score // 0' 2>/dev/null)
GRADE=$(echo "$SCORECARD" | jq -r '.grade // "N/A"' 2>/dev/null)
ONE_LINER=$(echo "$SCORECARD" | jq -r '.one_liner // "Score computed"' 2>/dev/null)
THRESHOLD=$(get_threshold "$CONFIG_PATH")

# Check if score is below threshold
if [ -n "$SCORE" ] && [ -n "$THRESHOLD" ]; then
  BELOW=$(echo "$SCORE < $THRESHOLD" | bc -l 2>/dev/null || echo "0")
  if [ "$BELOW" = "1" ]; then
    # BLOCK: Score below threshold
    SUMMARY=$(echo "$SCORECARD" | jq -r '.summary // "Quality below threshold"' 2>/dev/null)
    ISSUES=$(echo "$SCORECARD" | jq -r '.critical_issues // [] | join("; ")' 2>/dev/null)
    echo "SkillJudge BLOCKED: $SKILL_NAME scored $SCORE/10 ($GRADE) — below threshold of $THRESHOLD" >&2
    echo "Issues: $ISSUES" >&2
    echo "Summary: $SUMMARY" >&2
    exit 2
  fi
fi

# PASS: Output score as additional context
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "additionalContext": "SkillJudge: $SKILL_NAME → $SCORE/10 ($GRADE). $ONE_LINER"
  }
}
EOF
