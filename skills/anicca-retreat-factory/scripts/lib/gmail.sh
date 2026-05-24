#!/usr/bin/env bash
set -euo pipefail

# Safety guard log — independent of state.json schema. Tracks every gmail_send call.
# Format: ISO_TS\trecipient\tsha256(subject+body_file)
GMAIL_SEND_LOG="${GMAIL_SEND_LOG:-$HOME/.openclaw/skills/anicca-retreat-factory/data/.gmail-send-guard.tsv}"

# Usage: gmail_send <to> <subject> <body_file> [--force]
# Refuses to send if same (recipient + content_hash) was sent within last GMAIL_RATELIMIT_HOURS (default 24).
# Returns: message_id on stdout (jq parsed). Exit 1 on failure or rate-limit (unless --force).
gmail_send() {
  local to="$1" subject="$2" body_file="$3" force="${4:-}"
  local account="${GMAIL_ACCOUNT:-{{profile.contact.personalEmail}}}"
  local rate_hours="${GMAIL_RATELIMIT_HOURS:-24}"
  : "${GOG_KEYRING_PASSWORD:?GOG_KEYRING_PASSWORD required for gog gmail}"

  if [ ! -f "$body_file" ]; then
    echo "ERROR: body_file not found: $body_file" >&2
    return 1
  fi

  # Compute content hash (recipient + subject + body)
  local content_hash
  content_hash=$(printf "%s\n%s\n" "$to" "$subject" | cat - "$body_file" | shasum -a 256 | awk '{print $1}')

  # Rate-limit check (unless --force)
  if [ "$force" != "--force" ] && [ -f "$GMAIL_SEND_LOG" ]; then
    # cutoff in epoch seconds
    local cutoff_epoch now_epoch
    now_epoch=$(date +%s)
    cutoff_epoch=$((now_epoch - rate_hours * 3600))
    # Look for recent send to same recipient with same content_hash
    local recent
    recent=$(awk -F'\t' -v rcpt="$to" -v hash="$content_hash" -v cutoff="$cutoff_epoch" '
      {
        # parse ISO ts column 1 → epoch via system date
        cmd = "date -j -f \"%Y-%m-%dT%H:%M:%S%z\" \"" $1 "\" +%s 2>/dev/null"
        cmd | getline epoch
        close(cmd)
        if (epoch >= cutoff && $2 == rcpt && $3 == hash) {
          print $1
          exit
        }
      }
    ' "$GMAIL_SEND_LOG" 2>/dev/null || true)
    if [ -n "$recent" ]; then
      echo "ERROR: rate-limit guard — same (recipient + content) sent at $recent (within last ${rate_hours}h). Use --force to override." >&2
      return 1
    fi
  fi

  # Send
  local response mid
  response=$(GOG_KEYRING_PASSWORD="$GOG_KEYRING_PASSWORD" /opt/homebrew/bin/gog gmail send \
    -a "$account" \
    --to "$to" \
    --subject "$subject" \
    --body-file "$body_file" \
    -j --results-only 2>&1) || {
    echo "ERROR: gog gmail send failed: $response" >&2
    return 1
  }

  mid=$(echo "$response" | jq -r '.messageId // empty')
  if [ -z "$mid" ]; then
    echo "ERROR: no messageId in response: $response" >&2
    return 1
  fi

  # Append to guard log (atomic append; create dir/file if needed)
  mkdir -p "$(dirname "$GMAIL_SEND_LOG")"
  printf "%s\t%s\t%s\t%s\n" "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$to" "$content_hash" "$mid" >> "$GMAIL_SEND_LOG"

  echo "$mid"
}
