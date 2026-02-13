#!/bin/bash
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$PLUGIN_ROOT/hooks/common.sh"

# Read hook input from stdin
INPUT=$(cat)

# Extract agent info from input
AGENT_TYPE=$(echo "$INPUT" | jq -r '.agent_type // empty' 2>/dev/null)
AGENT_TRANSCRIPT=$(echo "$INPUT" | jq -r '.agent_transcript_path // empty' 2>/dev/null)

# Need both agent type and transcript
[ -z "$AGENT_TYPE" ] || [ -z "$AGENT_TRANSCRIPT" ] && exit 0

# Check if this agent type should be auto-judged
CONFIG_PATH="$PLUGIN_ROOT/judge-config.json"
SHOULD_JUDGE=$(should_auto_judge "$AGENT_TYPE" "$CONFIG_PATH")
[ "$SHOULD_JUDGE" != "true" ] && exit 0

# Run the scoring engine
SCORECARD=$(python3 "$PLUGIN_ROOT/skills/judge/scripts/score.py" \
  --skill "$AGENT_TYPE" \
  --transcript "$AGENT_TRANSCRIPT" \
  --rubric-dir "$PLUGIN_ROOT/skills/judge/rubrics" \
  --scores-dir "$PLUGIN_ROOT/skills/judge/scores" \
  --config "$CONFIG_PATH" 2>&1) || {
    echo "Verdict: Scoring failed for agent $AGENT_TYPE" >&2
    exit 0
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
    SUMMARY=$(echo "$SCORECARD" | jq -r '.summary // "Quality below threshold"' 2>/dev/null)
    ISSUES=$(echo "$SCORECARD" | jq -r '.critical_issues // [] | join("; ")' 2>/dev/null)
    echo "Verdict BLOCKED: Agent $AGENT_TYPE scored $SCORE/10 ($GRADE) — below threshold of $THRESHOLD" >&2
    echo "Issues: $ISSUES" >&2
    echo "Summary: $SUMMARY" >&2
    exit 2
  fi
fi

# PASS: Output score as additional context
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SubagentStop",
    "additionalContext": "Verdict: Agent $AGENT_TYPE → $SCORE/10 ($GRADE). $ONE_LINER"
  }
}
EOF
