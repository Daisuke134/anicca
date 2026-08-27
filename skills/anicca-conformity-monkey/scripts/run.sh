#!/usr/bin/env bash
# Anicca Conformity Monkey — policy violation disable (Netflix Conformity pattern)
# Spec: 2026-06-07 v1.3 §3.6.2
set -uo pipefail
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
source "$HOME/.openclaw/skills/_shared/cron-lock.sh"
export ANICCA_MONKEY="anicca-conformity-monkey"

AUDIT="$HOME/.openclaw/skills/anicca-doctor-monkey/data/audit-rules.json"
NEVER_DISABLE=$(jq -r '.guardrails_NEVER_DISABLE | to_entries[].value[]' "$AUDIT" 2>/dev/null | sort -u)
[ -z "$NEVER_DISABLE" ] && NEVER_DISABLE=$(jq -r '.guardrails_NEVER_DISABLE[]?' "$AUDIT" 2>/dev/null | sort -u)

VIOLATIONS=0; ALERTED=0; SKIPPED=0
LANDING_PATTERN='apps/landing|aniccaai\.com'

# v1.4 F2-style perf: cache cron-list + jq @tsv + inline (= 30x speedup, see Janitor)
CRON_LIST_JSON=$(openclaw cron list --all --json 2>/dev/null)
NOW=$(date -u +%s)
echo "$CRON_LIST_JSON" | \
  jq -r '.jobs[] | select(.enabled==true) | [.name, .id, (.payload.message // ""), (.payload.last_modified_by // ""), (.payload.last_modified_at // "")] | @tsv' | \
  while IFS=$'\t' read -r NAME UUID MSG LAST_BY LAST_AT; do

  if echo "$NEVER_DISABLE" | grep -qFx "$NAME"; then
    if echo "$MSG" | grep -qE "$LANDING_PATTERN"; then
      ALERTED=$((ALERTED+1))
      echo "alert-cornerstone-violation: $NAME"
      [ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
        -H "Content-Type: application/json" \
        --data "$(jq -nc --arg c C091G3PKHL2 --arg t ":warning: cornerstone $NAME has apps/landing/ in message — manual review needed" '{channel:$c,text:$t}')" \
        https://slack.com/api/chat.postMessage >/dev/null 2>&1
    fi
    SKIPPED=$((SKIPPED+1)); continue
  fi

  # inline provenance check (= no per-UUID API call)
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

  if echo "$MSG" | grep -qE "$LANDING_PATTERN"; then
    if with_cron_lock "$UUID" "disable-landing-violation" -- \
       bash -c "openclaw cron disable '$UUID' >/dev/null && set_provenance '$UUID' 'apps_landing_policy_violation'"; then
      VIOLATIONS=$((VIOLATIONS+1))
      echo "disabled-policy-violation: $NAME"
    fi
  fi
done

REPORT=":cop: conformity $(date -Iseconds) | violations=$VIOLATIONS alerted=$ALERTED skipped=$SKIPPED"
echo "$REPORT"
[ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
  -H "Content-Type: application/json" \
  --data "$(jq -nc --arg c C091G3PKHL2 --arg t "$REPORT" '{channel:$c,text:$t}')" \
  https://slack.com/api/chat.postMessage >/dev/null 2>&1
exit 0
