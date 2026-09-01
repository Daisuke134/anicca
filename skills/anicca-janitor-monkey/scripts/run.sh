#!/usr/bin/env bash
# Anicca Janitor Monkey — useless cron dispose (Netflix Janitor pattern)
# Spec: 2026-06-07 v1.3 §3.6
set -uo pipefail
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
HERE="$(cd "$(dirname "$0")" && pwd)"
source "$HOME/.openclaw/skills/_shared/cron-lock.sh"
export ANICCA_MONKEY="anicca-janitor-monkey"

AUDIT="$HOME/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json"
NEVER_DISABLE=$(jq -r '.guardrails_NEVER_DISABLE | to_entries[].value[]' "$AUDIT" 2>/dev/null | sort -u)
[ -z "$NEVER_DISABLE" ] && NEVER_DISABLE=$(jq -r '.guardrails_NEVER_DISABLE[]?' "$AUDIT" 2>/dev/null | sort -u)

ARCHIVED=0; DISABLED=0; SKIPPED=0
NOW=$(date -u +%s)
CUTOFF_STALE=$(( NOW - 30*86400 ))

# v1.4 F2: cache cron list ONCE + tab-separated extract (= 1 jq call total)
# Include payload.last_modified_by and last_modified_at for inline provenance check
CRON_LIST_JSON=$(openclaw cron list --all --json 2>/dev/null)
echo "$CRON_LIST_JSON" | \
  jq -r '.jobs[] | [.name, .id, .enabled, (.state.lastRunAtMs // 0), (.payload.last_modified_by // ""), (.payload.last_modified_at // "")] | @tsv' | \
  while IFS=$'\t' read -r NAME UUID ENABLED LAST_RUN LAST_BY LAST_AT; do

  if echo "$NEVER_DISABLE" | grep -qFx "$NAME"; then
    SKIPPED=$((SKIPPED+1)); continue
  fi

  # v1.4 F2: inline provenance check (= no per-UUID API call、 no jq subshell)
  if [ -n "$LAST_BY" ] && [ "$LAST_BY" != "$ANICCA_MONKEY" ]; then
    CUTOFF_H=24
    [ "$LAST_BY" = "Dais" ] && CUTOFF_H=$((7*24))
    THEN=$(date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$LAST_AT" +%s 2>/dev/null || echo 0)
    if [ "$THEN" != "0" ]; then
      DIFF_H=$(( (NOW - THEN) / 3600 ))
      if [ "$DIFF_H" -lt "$CUTOFF_H" ]; then
        SKIPPED=$((SKIPPED+1)); continue
      fi
    fi
  fi

  # 30d stale → archive (= disable + provenance)
  if [ -n "$LAST_RUN" ] && [ "$LAST_RUN" != "null" ]; then
    LAST_S=$(( LAST_RUN / 1000 ))
    if [ "$LAST_S" -lt "$CUTOFF_STALE" ] && [ "$ENABLED" = "true" ]; then
      if with_cron_lock "$UUID" "archive-30d-stale" -- \
         bash -c "openclaw cron disable '$UUID' >/dev/null && set_provenance '$UUID' '30d_stale_archive'"; then
        ARCHIVED=$((ARCHIVED+1))
        echo "archived: $NAME (last_run_ms=$LAST_RUN)"
      fi
    fi
  fi
done

# Run inherited curator + Sunday over-scheduled detection
[ -x "$HERE/curator.sh" ] && bash "$HERE/curator.sh" 2>&1 | tail -3 || true
[ -x "$HERE/over-scheduled.sh" ] && [ "$(date +%u)" = "7" ] && \
  bash "$HERE/over-scheduled.sh" 2>&1 | tail -3 || true

REPORT=":robot_face: janitor $(date -Iseconds) | archived=$ARCHIVED disabled=$DISABLED skipped=$SKIPPED"
echo "$REPORT"
if [ -n "${SLACK_BOT_TOKEN:-}" ]; then
  curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "$(jq -nc --arg c C091G3PKHL2 --arg t "$REPORT" '{channel:$c,text:$t}')" \
    https://slack.com/api/chat.postMessage >/dev/null 2>&1
fi
exit 0
