#!/usr/bin/env bash
# file-issue: read detected-issue JSONL (stdin or $1) → for each NEW issue
# (not already filed today for that type) → `gh issue create` on
# Daisuke134/anicca-oss with @anicca mention → record number to
# self-improve-filed.jsonl. Idempotent per (issue_type, day).
#
# Env:
#   DRY_RUN=1   print intended title only, no gh write, no state write.
#   GH_TOKEN    inherited by gh (never echoed).
set -uo pipefail

STATE_DIR="${STATE_DIR:-/Users/anicca/.hermes/state}"
REPO="${SELF_IMPROVE_REPO:-Daisuke134/anicca-oss}"
JQ=/usr/bin/jq
mkdir -p "$STATE_DIR"
FILED="$STATE_DIR/self-improve-filed.jsonl"

if [ "${1:-}" = "-" ] || [ -z "${1:-}" ]; then
  INPUT="$(cat)"
else
  INPUT="$(cat "$1")"
fi

TODAY="$(date -u +%Y-%m-%d)"

already_filed() {
  # already_filed <issue_type> <day> → 0 if a row exists
  [ -r "$FILED" ] || return 1
  "$JQ" -e --arg it "$1" --arg d "$2" \
    'select(.issue_type==$it and .day==$d)' "$FILED" >/dev/null 2>&1
}

printf '%s\n' "$INPUT" | while IFS= read -r line; do
  [ -z "$line" ] && continue
  itype="$(printf '%s' "$line" | "$JQ" -r '.issue_type // empty' 2>/dev/null)"
  [ -z "$itype" ] && continue
  sev="$(printf '%s' "$line" | "$JQ" -r '.severity // "info"' 2>/dev/null)"
  ev="$(printf '%s' "$line" | "$JQ" -r '.evidence // ""' 2>/dev/null)"
  skill="$(printf '%s' "$line" | "$JQ" -r '.affected_skill // ""' 2>/dev/null)"

  title="@anicca self-improve: $itype"
  body="$(printf '**Detected by self-improve loop** (severity: %s)\n\n**Evidence:** %s\n\n**Affected skill:** %s\n\n@anicca please investigate and propose a fix.\n\nfiled automatically by skills/self-improve' \
    "$sev" "$ev" "${skill:-unknown}")"

  if [ "${DRY_RUN:-}" = "1" ]; then
    echo "$title"
    continue
  fi

  if already_filed "$itype" "$TODAY"; then
    echo "skip (already filed today): $itype" >&2
    continue
  fi

  url="$(gh issue create --repo "$REPO" \
    --title "$title" --body "$body" \
    --label "self-improve" --label "auto-filed" 2>/dev/null)"
  if [ -z "$url" ]; then
    # labels may not exist on the repo — retry without them so the loop is robust
    url="$(gh issue create --repo "$REPO" --title "$title" --body "$body" 2>/dev/null)" || {
      echo "gh issue create failed for $itype" >&2
      continue
    }
  fi
  num="$(printf '%s' "$url" | grep -oE '[0-9]+$' || echo "")"
  echo "$url"
  "$JQ" -nc --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" --arg it "$itype" \
    --arg d "$TODAY" --arg n "$num" --arg t "$title" --arg u "$url" \
    '{ts:$ts, issue_type:$it, day:$d, issue_number:($n|select(.!="")|tonumber?), title:$t, url:$u}' \
    >> "$FILED"
done
