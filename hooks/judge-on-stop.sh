#!/bin/bash
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
source "$PLUGIN_ROOT/hooks/common.sh"

# Check dependencies before proceeding
check_dependencies || exit 0

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
    echo "Proofloop: Scoring failed for $SKILL_NAME" >&2
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
    echo "Proofloop BLOCKED: $SKILL_NAME scored $SCORE/10 ($GRADE) — below threshold of $THRESHOLD" >&2
    echo "Issues: $ISSUES" >&2
    echo "Summary: $SUMMARY" >&2
    exit 2
  fi
fi

# Verifier-collapse gate (offline heuristic; see judge-config.json
# .verifier_collapse). gate_mode "warn" -- stderr only; "fail" --
# exit 2 like a threshold breach; "off" -- ignore entirely.
COLLAPSE=$(echo "$SCORECARD" | jq -r '.verifier_collapse // false' 2>/dev/null)
if [ "$COLLAPSE" = "true" ]; then
  GATE_MODE=$(get_verifier_collapse_gate_mode "$CONFIG_PATH")
  REASON=$(echo "$SCORECARD" | jq -r '.dimensions.consistency.verifier_collapse_reason // "verifier collapse detected"' 2>/dev/null)
  case "$GATE_MODE" in
    fail)
      echo "Proofloop BLOCKED: verifier collapse detected for $SKILL_NAME — $REASON" >&2
      echo "Tip: set judge-config.json.verifier_collapse.gate_mode to \"warn\" to demote to a warning." >&2
      exit 2
      ;;
    off)
      ;;  # silent
    *)
      echo "Proofloop WARNING: verifier collapse detected for $SKILL_NAME — $REASON" >&2
      echo "Tip: set judge-config.json.verifier_collapse.gate_mode to \"fail\" to block on this signal." >&2
      ;;
  esac
fi

# PASS: Output score as additional context
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "Stop",
    "additionalContext": "Proofloop: $SKILL_NAME → $SCORE/10 ($GRADE). $ONE_LINER"
  }
}
EOF
