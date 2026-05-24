#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export STATE_FILE="$SKILL_DIR/data/state.json"
CANDIDATES_FILE="$SKILL_DIR/data/candidates.json"

# shellcheck source=lib/state.sh
source "$SKILL_DIR/scripts/lib/state.sh"

state_init

cat <<EOF
=== anicca-retreat-factory status ===
candidates master: $(jq '.candidates | length' "$CANDIDATES_FILE") entries
$(state_summary)

--- outreach log (last 20) ---
$(jq -r '.outreach_log | sort_by(.sent_at) | reverse | .[0:20] | .[] | "[\(.sent_at)] \(.candidate_id) → \(.recipient) (msg: \(.message_id))"' "$STATE_FILE")

--- candidates not yet contacted ---
$(jq -r --slurpfile s "$STATE_FILE" '
  ($s[0].outreach_log | map(.candidate_id)) as $sent
  | .candidates
  | map(select(.id as \$id | $sent | index(\$id) | not))
  | map("• \(.id) (\(.confidence // "n/a")) — \(.{{profile.lateness.stakeholders.channel}} // "no-{{profile.lateness.stakeholders.channel}}") — \(.name)")
  | .[]
' "$CANDIDATES_FILE" 2>/dev/null || echo "(jq slurpfile fallback)")
EOF
