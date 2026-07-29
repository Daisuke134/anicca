#!/usr/bin/env bash
# telegram-notify.sh — direct-from-bash Telegram alert via OpenClaw's own channel session.
# For launchd / out-of-band scripts that do not have a channel delivery field.
#
# Usage (source then call):
#   source "$LIFE_MANAGER_REPO/skills/_shared/scripts/telegram-notify.sh"
#   telegram_notify "text here"

telegram_notify() {
  local text="$1"
  local target="${TELEGRAM_ALERT_CHAT_ID:?TELEGRAM_ALERT_CHAT_ID is required}"
  openclaw message send --channel telegram --target "$target" -m "$text" >/dev/null 2>&1
  return $?
}
