#!/usr/bin/env bash
# notifier.sh — env-driven notification for the article loop (spec #70, OSS self-containment).
#
# Replaces the `openclaw message send` / telegram_notify() dependency (openclaw CLI +
# an active OpenClaw gateway session), which only exists on the live Anicca instance and
# is not something an OSS installer has. This talks to the Telegram Bot API directly —
# every installer that wants alerts creates their own bot (@BotFather, 30 seconds, no
# approval) and points these two env vars at it. No env vars set = silent no-op (never
# blocks or crashes the caller; the loop must run with zero notification configured).
#
# Setup (put in ~/.openclaw/.env or wherever this repo's installer sources env from):
#   TELEGRAM_BOT_TOKEN=<token from @BotFather>
#   TELEGRAM_CHAT_ID=<your chat id, e.g. from @userinfobot>
#
# Usage:
#   bash notifier.sh "message text"        # standalone CLI
#   source notifier.sh; notify "message text"   # sourced, as a function
#
# Exit code: 0 on successful send OR on a deliberate no-op (env vars unset -- that is not
# a failure, it is the documented default). Non-zero only when the env vars ARE set but
# the actual Telegram API call failed (network error, bad token, etc.) -- callers that
# care can check this; callers that do not (most) can ignore it, matching the old
# telegram_notify()'s `return $?` contract.

notify() {
  local text="$1"
  if [ -z "${TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${TELEGRAM_CHAT_ID:-}" ]; then
    echo "[notifier] TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not set -- no-op (this is the documented default, not an error)" >&2
    return 0
  fi
  curl -sS --max-time 10 -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d chat_id="${TELEGRAM_CHAT_ID}" \
    --data-urlencode text="${text}" \
    -o /dev/null -w '%{http_code}' | grep -q '^200$'
}

# Only run as a standalone CLI when NOT sourced (mirrors the `source ...; notify ...`
# usage documented above -- sourcing must not also execute a stray notify call).
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  if [ $# -lt 1 ]; then
    echo "usage: notifier.sh \"message text\"" >&2
    exit 2
  fi
  notify "$1"
  exit $?
fi
