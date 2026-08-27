#!/usr/bin/env bash
# Anicca Monkey Watchdog — out-of-band launchd, monitors 3 in-band monkeys
# Spec: 2026-06-07 v1.3 §3.6.2 + reviewer BLOCKING #5
# 2026-07-04: Phase 0 wiring (spec 2026-07-01-openclaw-self-heal-design.md §2.0 item 2)
#   - "missing" case now self-heals: re-registers the monkey's cron via the
#     shared register-monkey-cron.sh (same mechanism used to bootstrap all 3
#     monkeys), then confirms via `openclaw cron get`.
#   - "found but disabled" case (proven real 2026-07-04: doctor-monkey +
#     janitor-monkey existed, enabled=false, dead-Slack delivery, since
#     2026-06 — invisible to the old "missing" check because the id lookup
#     did find them) now also self-heals via the same shared script.
#   - alert channel migrated dead Slack (#C091G3PKHL2, account_inactive) ->
#     Telegram, same destination the other 211 migrated crons use
#     (git 74a7de13). Slack call kept as a harmless best-effort fallback.
set -uo pipefail
set -a; source "$HOME/.openclaw/.env" 2>/dev/null; set +a
source "$HOME/.openclaw/skills/_shared/scripts/telegram-notify.sh"

MONKEYS=("anicca-doctor-monkey" "anicca-janitor-monkey" "anicca-conformity-monkey")
NOW=$(date -u +%s)
CUTOFF_24H=$(( NOW - 24*3600 ))
DOWN=()
HEALED=()

REGISTER_SCRIPT="$HOME/.openclaw/skills/_shared/scripts/register-monkey-cron.sh"

self_heal_missing() {
  local m="$1"
  local new_uuid
  new_uuid=$(bash "$REGISTER_SCRIPT" "$m" 2>&1 | tail -1)
  local confirm
  confirm=$(openclaw cron get "$new_uuid" 2>/dev/null | jq -r '.id // empty')
  if [ -n "$confirm" ]; then
    HEALED+=("$m:missing->$new_uuid")
    echo ":wrench: watchdog self-healed: $m (was missing, recreated as $new_uuid)"
    echo "$new_uuid"
  else
    echo ":x: watchdog self-heal FAILED for $m (register-monkey-cron.sh did not produce a valid job id)" >&2
    echo ""
  fi
}

for M in "${MONKEYS[@]}"; do
  UUID=$(openclaw cron list --all --json 2>/dev/null | jq -r --arg n "$M" '.jobs[]|select(.name==$n)|.id')
  if [ -z "$UUID" ]; then
    DOWN+=("$M:missing")
    UUID=$(self_heal_missing "$M")
    [ -z "$UUID" ] && continue
  fi

  ENABLED=$(openclaw cron get "$UUID" 2>/dev/null | jq -r '.enabled // true')
  if [ "$ENABLED" != "true" ]; then
    DOWN+=("$M:disabled")
    NEW_UUID=$(bash "$REGISTER_SCRIPT" "$M" 2>&1 | tail -1)
    STILL_ENABLED=$(openclaw cron get "$NEW_UUID" 2>/dev/null | jq -r '.enabled // false')
    if [ "$STILL_ENABLED" = "true" ]; then
      HEALED+=("$M:disabled->enabled($NEW_UUID)")
      echo ":wrench: watchdog self-healed: $M (was disabled, re-enabled $NEW_UUID)"
      UUID="$NEW_UUID"
    else
      echo ":x: watchdog self-heal FAILED to re-enable $M ($UUID)" >&2
      continue
    fi
  fi

  LAST_OK_MS=$(openclaw cron get "$UUID" 2>/dev/null | jq -r '.state.lastRunAtMs // 0')
  LAST_STATUS=$(openclaw cron get "$UUID" 2>/dev/null | jq -r '.state.lastRunStatus // ""')
  if [ "$LAST_OK_MS" = "0" ] || [ "$LAST_OK_MS" = "null" ]; then
    DOWN+=("$M:never-run")
    continue
  fi
  if [ "$LAST_STATUS" != "ok" ]; then
    DOWN+=("$M:last-status-$LAST_STATUS")
    openclaw cron run "$UUID" --wait --wait-timeout 5m 2>&1 | tail -3 || true
    continue
  fi
  LAST_S=$(( LAST_OK_MS / 1000 ))
  if [ "$LAST_S" -lt "$CUTOFF_24H" ]; then
    DOWN+=("$M:stale-24h")
    openclaw cron run "$UUID" --wait --wait-timeout 5m 2>&1 | tail -3 || true
  fi
done

if [ ${#DOWN[@]} -eq 0 ]; then
  echo ":eye: watchdog $(date -Iseconds) | all 3 monkeys healthy"
else
  REPORT=":rotating_light: watchdog $(date -Iseconds) | DOWN: ${DOWN[*]}"
  if [ ${#HEALED[@]} -gt 0 ]; then
    REPORT="$REPORT | SELF-HEALED: ${HEALED[*]}"
  fi
  echo "$REPORT"
  telegram_notify "$REPORT"
  [ -n "${SLACK_BOT_TOKEN:-}" ] && curl -sS -X POST -H "Authorization: Bearer ${SLACK_BOT_TOKEN}" \
    -H "Content-Type: application/json" \
    --data "$(jq -nc --arg c C091G3PKHL2 --arg t "$REPORT" '{channel:$c,text:$t}')" \
    https://slack.com/api/chat.postMessage >/dev/null 2>&1
fi
exit 0
