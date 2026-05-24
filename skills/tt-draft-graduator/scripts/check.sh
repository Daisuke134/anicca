#!/usr/bin/env bash
# tt-draft-graduator — auto-flip TT factories from UPLOAD draft → DIRECT_POST after N days.
# Reads/writes ~/.openclaw/state/tt-posting-state.json
# IG/X/YT は対象外 (day 1 から DIRECT)。

set -uo pipefail

STATE="$HOME/.openclaw/state/tt-posting-state.json"
SLACK_CHANNEL="${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}"

if [ ! -f "$STATE" ]; then
  echo "ERR: state file missing: $STATE" >&2
  exit 1
fi

NOW=$(date -u +%s)
TMP=$(mktemp)
GRADUATED=()

# Iterate all keys
for FACTORY in $(jq -r 'keys[]' "$STATE"); do
  STARTED=$(jq -r --arg k "$FACTORY" '.[$k].started_at' "$STATE")
  DAYS=$(jq -r --arg k "$FACTORY" '.[$k].draft_days' "$STATE")
  IN_DRAFT=$(jq -r --arg k "$FACTORY" '.[$k].in_draft' "$STATE")

  # Cross-platform date parse (BSD vs GNU)
  if STARTED_TS=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$STARTED" +%s 2>/dev/null); then
    :
  elif STARTED_TS=$(gdate -d "$STARTED" +%s 2>/dev/null); then
    :
  else
    echo "WARN: cannot parse started_at for $FACTORY: $STARTED" >&2
    continue
  fi

  ELAPSED=$(( (NOW - STARTED_TS) / 86400 ))

  if [ "$IN_DRAFT" = "true" ] && [ "$ELAPSED" -ge "$DAYS" ]; then
    GRADUATED_AT=$(date -u +%FT%TZ)
    jq --arg k "$FACTORY" --arg t "$GRADUATED_AT" \
      '.[$k].in_draft = false | .[$k].auto_graduated_at = $t' \
      "$STATE" > "$TMP" && mv "$TMP" "$STATE"
    GRADUATED+=("$FACTORY (${ELAPSED}d)")
    echo "🎓 graduated: $FACTORY ($ELAPSED days)"
  fi
done

if [ ${#GRADUATED[@]} -gt 0 ]; then
  MSG="🎓 tt-draft-graduator: $(IFS=', '; echo "${GRADUATED[*]}") → DIRECT_POST"
  if command -v openclaw &>/dev/null; then
    openclaw message send --channel slack --target "$SLACK_CHANNEL" --text "$MSG" 2>/dev/null || echo "WARN: slack send failed" >&2
  fi
else
  echo "ℹ️  no graduations today (all up to date)"
fi
