#!/bin/bash
# Example PostToolUse hook that rewrites tool output and stays
# CC1 (tool-output-rewrite) compliant.
#
# Reads the original tool output on stdin (per Claude Code v2.1.121
# convention) and emits a JSON object with the rewritten payload
# plus the disclosure markers verdict's CC1 rubric expects.
#
set -euo pipefail

ORIGINAL=$(cat)
TOOL_NAME="${TOOL_NAME:-Bash}"
HOOK_SOURCE="${BASH_SOURCE[0]:-hooks/compliant-rewrite-hook.sh}"

# Compute byte-delta ratio (rewritten / original).
ORIG_LEN=${#ORIGINAL}
REWRITTEN="${ORIGINAL//root:x:0:0:root/<root>}"
NEW_LEN=${#REWRITTEN}
if [[ "${ORIG_LEN}" -gt 0 ]]; then
    RATIO=$(awk -v n="${NEW_LEN}" -v d="${ORIG_LEN}" 'BEGIN { printf "%.3f", n/d }')
else
    RATIO="1.000"
fi

# Emit the disclosure markers in the rewritten payload itself so
# the CC1 rubric sees them.
TAGGED="[hook-rewrote: ${TOOL_NAME}] [hook-byte-delta: ${RATIO}] [hook-source: ${HOOK_SOURCE}] ${REWRITTEN}"

# Emit Claude Code v2.1.121 hookSpecificOutput shape.
printf '{"hookSpecificOutput":{"updatedToolOutput":%s}}\n' "$(printf '%s' "${TAGGED}" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')"
