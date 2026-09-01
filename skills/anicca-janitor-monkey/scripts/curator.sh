#!/usr/bin/env bash
# Daily 03:00 curator — Hermes-style 4-layer safe archive
# Layer 1: pinned (audit-rules.json guardrails_NEVER_DISABLE)
# Layer 2: 7d grace period revert
# Layer 3: 3-fire countdown
# Layer 4: 30-day snapshot rollback
set -uo pipefail
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a

SKILL_ROOT="$HOME/.openclaw/skills"
BACKUP="$SKILL_ROOT/.backups"
USAGE="$SKILL_ROOT/anicca-doctor-monkey/data/usage.json"
AUDIT="$HOME/.openclaw/skills/anicca-cron-doctor/data/audit-rules.json"
NOW_MS=$(date +%s000)
TS=$(date -u +%Y-%m-%dT%H-%M-%SZ)

mkdir -p "$BACKUP/$TS"
# NOTE: --exclude must come BEFORE the positional "skills" archive arg — this
# bsdtar build stops option parsing at the first positional arg, so excludes
# placed after "skills" are silently ignored (masked by 2>/dev/null) and never
# actually excluded anything, which is how skills.tar.gz ballooned to GBs/day.
tar -czf "$BACKUP/$TS/skills.tar.gz" -C "$HOME/.openclaw" \
  --exclude="skills/.backups" --exclude="skills/.archive" \
  --exclude="*/state" --exclude="*/venv*" --exclude="*/node_modules" \
  --exclude="*/media" --exclude="*.mp4" --exclude="*/images" \
  --exclude="*/output" --exclude="*/outputs" --exclude="*/runs" \
  --exclude="*/workspace" --exclude="*/.backups" \
  --exclude="skills/anicca-earn-bounty/work" \
  skills 2>/dev/null

find "$BACKUP" -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf {} + 2>/dev/null

# Count-based cap: skills.tar.gz has grown to multiple GB/day (was 1.4G->4.4G->7.8G
# over 3 consecutive days), so the 30-day mtime window above alone let backups balloon
# to 14G+ and was a repeat contributor to host-wide ENOSPC crashes. Keep only the
# single most recent backup regardless of age.
ls -1t "$BACKUP" 2>/dev/null | tail -n +2 | while read -r OLD; do
  rm -rf "$BACKUP/$OLD"
done

[ ! -f "$USAGE" ] && echo '{}' > "$USAGE"

# Build pinned set from audit-rules
PINNED=$(jq -r '.guardrails_NEVER_DISABLE? | to_entries | map(.value) | flatten | unique | .[]' "$AUDIT" 2>/dev/null)

ARCH=0; FLAG=0; REVERT=0
for D in "$SKILL_ROOT"/*/; do
  [ ! -d "$D" ] && continue
  SKILL=$(basename "$D")
  # Layer 1: glob match against pinned patterns
  PINNED_MATCH=0
  for P in $PINNED; do
    case "$SKILL" in $P) PINNED_MATCH=1; break;; esac
  done
  [ "$PINNED_MATCH" = "1" ] && continue

  LAST=$(jq -r --arg s "$SKILL" '.[$s].last_used_at_ms // 0' "$USAGE" 2>/dev/null)
  [ "$LAST" = "0" ] && continue
  AGE=$(( (NOW_MS - LAST) / 86400000 ))

  # Layer 2: 7d grace revert
  RECENT=$(jq -r --arg s "$SKILL" --arg ago "$((NOW_MS - 7*86400000))" \
    '.[$s].uses[]? | select(. > ($ago|tonumber))' "$USAGE" 2>/dev/null | head -1)
  if [ -n "$RECENT" ]; then
    FLAGGED=$(jq -r --arg s "$SKILL" '.[$s].archive_eligible_since // ""' "$USAGE" 2>/dev/null)
    if [ -n "$FLAGGED" ]; then
      jq --arg s "$SKILL" 'del(.[$s].archive_eligible_since) | del(.[$s].stale)' \
        "$USAGE" > "$USAGE.tmp" && mv "$USAGE.tmp" "$USAGE"
      REVERT=$((REVERT + 1))
    fi
    continue
  fi

  # Layer 3a: stale flag (30-89d)
  if [ "$AGE" -ge 30 ] && [ "$AGE" -lt 90 ]; then
    jq --arg s "$SKILL" '.[$s].stale = true' "$USAGE" > "$USAGE.tmp" && mv "$USAGE.tmp" "$USAGE"
    continue
  fi

  # Layer 3b: archive countdown (90d+)
  if [ "$AGE" -ge 90 ]; then
    FLAGGED_SINCE=$(jq -r --arg s "$SKILL" '.[$s].archive_eligible_since // ""' "$USAGE" 2>/dev/null)
    if [ -z "$FLAGGED_SINCE" ]; then
      jq --arg s "$SKILL" --arg ts "$NOW_MS" \
        '.[$s].archive_eligible_since = ($ts|tonumber)' "$USAGE" > "$USAGE.tmp" && mv "$USAGE.tmp" "$USAGE"
      FLAG=$((FLAG + 1))
    else
      FLAG_AGE=$(( (NOW_MS - FLAGGED_SINCE) / 86400000 ))
      if [ "$FLAG_AGE" -ge 3 ]; then
        CRON_NAME=$(jq -r --arg s "$SKILL" '.[$s].cron_name // ""' "$USAGE" 2>/dev/null)
        [ -n "$CRON_NAME" ] && openclaw cron disable "$CRON_NAME" >/dev/null 2>&1
        mkdir -p "$SKILL_ROOT/.archive"
        mv "$SKILL_ROOT/$SKILL" "$SKILL_ROOT/.archive/$SKILL.$TS" 2>/dev/null
        ARCH=$((ARCH + 1))
      fi
    fi
  fi
done

MSG=":wastebasket: curator: archived=$ARCH flagged=$FLAG reverted=$REVERT"
[ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "$(jq -nc --arg c C091G3PKHL2 --arg t "$MSG" '{channel:$c,text:$t}')" \
  https://slack.com/api/chat.postMessage >/dev/null 2>&1 || true
echo "$MSG"
exit 0
