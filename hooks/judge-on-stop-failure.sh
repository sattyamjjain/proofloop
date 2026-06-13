#!/bin/bash
# Proofloop — StopFailure hook
#
# Claude Code fires StopFailure when a turn ends due to an API error
# (rate_limit, authentication_failed, billing_error, invalid_request,
# server_error, max_output_tokens, unknown). Scoring that transcript
# would dock correctness/completeness unfairly for a failure the user
# didn't cause, so we skip auto-judging and write a non-blocking
# breadcrumb to stderr instead.
set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck disable=SC1091
source "$PLUGIN_ROOT/hooks/common.sh"

check_dependencies || exit 0

INPUT=$(cat)
ERROR_TYPE=$(echo "$INPUT" | jq -r '.matcher // "unknown"' 2>/dev/null)
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"' 2>/dev/null)

echo "Proofloop: skipping auto-judge for session $SESSION_ID — StopFailure ($ERROR_TYPE)." >&2
exit 0
