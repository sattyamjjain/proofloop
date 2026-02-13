#!/bin/bash
# SkillJudge — Common hook utilities

# Get the plugin root directory
get_plugin_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
}

# Detect which skill was used from a transcript
# Looks for skill invocation patterns in the transcript
detect_skill_from_transcript() {
  local transcript_path="$1"

  if [ ! -f "$transcript_path" ]; then
    echo ""
    return
  fi

  # Pattern 1: Look for skills/*/SKILL.md references
  local skill_name
  skill_name=$(grep -oP '(?<=skills/)[^/]+(?=/SKILL\.md)' "$transcript_path" 2>/dev/null | tail -1)

  if [ -n "$skill_name" ]; then
    echo "$skill_name"
    return
  fi

  # Pattern 2: Look for /skill-name command invocations
  skill_name=$(grep -oP '(?<=Skill tool invoked: )[a-zA-Z0-9_-]+' "$transcript_path" 2>/dev/null | tail -1)

  if [ -n "$skill_name" ]; then
    echo "$skill_name"
    return
  fi

  # Pattern 3: Look for skill: "name" in Skill tool calls
  skill_name=$(grep -oP '(?<="skill":\s?")[a-zA-Z0-9_-]+' "$transcript_path" 2>/dev/null | tail -1)

  if [ -n "$skill_name" ]; then
    echo "$skill_name"
    return
  fi

  echo ""
}

# Check if a skill should be auto-judged based on config
should_auto_judge() {
  local skill_name="$1"
  local config_path="$2"

  # If config doesn't exist, don't auto-judge
  if [ ! -f "$config_path" ]; then
    echo "false"
    return
  fi

  # Check if auto_judge is enabled
  local enabled
  enabled=$(jq -r '.auto_judge.enabled // true' "$config_path" 2>/dev/null)
  if [ "$enabled" = "false" ]; then
    echo "false"
    return
  fi

  # Check if skill is in "never" list
  local in_never
  in_never=$(jq -r --arg s "$skill_name" \
    'if (.auto_judge.never // []) | index($s) then "true" else "false" end' \
    "$config_path" 2>/dev/null)
  if [ "$in_never" = "true" ]; then
    echo "false"
    return
  fi

  # Check if skill is in "always" list
  local in_always
  in_always=$(jq -r --arg s "$skill_name" \
    'if (.auto_judge.always // []) | index($s) then "true" else "false" end' \
    "$config_path" 2>/dev/null)
  if [ "$in_always" = "true" ]; then
    echo "true"
    return
  fi

  # Not in either list = manual-only
  echo "false"
}

# Get the scoring threshold from config
get_threshold() {
  local config_path="$1"
  jq -r '.auto_judge.threshold // 5.0' "$config_path" 2>/dev/null
}
