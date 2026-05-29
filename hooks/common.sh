#!/bin/bash
# Verdict — Common hook utilities

# Check required dependencies
_check_dependency() {
  local cmd="$1"
  local install_hint="$2"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Verdict: requires '$cmd' but it is not installed. $install_hint" >&2
    return 1
  fi
  return 0
}

check_dependencies() {
  _check_dependency "jq" "Install: brew install jq / apt-get install jq" || return 1
  _check_dependency "bc" "Install: brew install bc / apt-get install bc" || return 1
  _check_dependency "python3" "Install: brew install python3 / apt-get install python3" || return 1
  return 0
}

# Get the plugin root directory
get_plugin_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd
}

# Detect which skill was used from a transcript.
#
# Looks for skill invocation patterns in order; first match wins.
# Uses `sed -nE` instead of `grep -oP` so the function works on
# BSD sed (macOS) as well as GNU (Linux, CI). `grep -oP` relies on
# PCRE, which macOS's BSD grep rejects — the old implementation
# silently fell through to "no skill detected" on every darwin run.
detect_skill_from_transcript() {
  local transcript_path="$1"

  if [ ! -f "$transcript_path" ]; then
    echo ""
    return
  fi

  local skill_name

  # Pattern 1: skills/<name>/SKILL.md references (last match wins)
  skill_name=$(sed -nE 's|.*skills/([a-zA-Z0-9_-]+)/SKILL\.md.*|\1|p' "$transcript_path" 2>/dev/null | tail -1)
  if [ -n "$skill_name" ]; then
    echo "$skill_name"
    return
  fi

  # Pattern 2: "Skill tool invoked: <name>" marker
  skill_name=$(sed -nE 's|.*Skill tool invoked: ([a-zA-Z0-9_-]+).*|\1|p' "$transcript_path" 2>/dev/null | tail -1)
  if [ -n "$skill_name" ]; then
    echo "$skill_name"
    return
  fi

  # Pattern 3: JSON "skill": "<name>" field
  skill_name=$(sed -nE 's|.*"skill":[[:space:]]*"([a-zA-Z0-9_-]+)".*|\1|p' "$transcript_path" 2>/dev/null | tail -1)
  if [ -n "$skill_name" ]; then
    echo "$skill_name"
    return
  fi

  # Pattern 4: leading /skill-name slash command (first match wins)
  skill_name=$(sed -nE 's|^/([a-zA-Z0-9_-]+).*|\1|p' "$transcript_path" 2>/dev/null | head -1)
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

# Get the verifier-collapse gate mode from config.
# Returns "warn" (default), "fail", or "off".
#   warn -- emit stderr warning, exit code unchanged
#   fail -- emit stderr "BLOCKED" line and exit 2 from the caller
#   off  -- ignore the flag entirely
get_verifier_collapse_gate_mode() {
  local config_path="$1"
  jq -r '.verifier_collapse.gate_mode // "warn"' "$config_path" 2>/dev/null
}
