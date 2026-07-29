#!/usr/bin/env bash
# Previous completed JST week through the durable Telegram outbox.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

exec /opt/homebrew/bin/python3 "$HOME/profitable-claude/skills/gig-work/scripts/telegram_report.py" weekly \
  --telegram-database "${GIG_TELEGRAM_OUTBOX_DB:-$HOME/gig/telegram-outbox.sqlite3}" \
  --gig-dir "$HOME/gig" \
  --runner-config "$HOME/profitable-claude/skills/agent-runner/config.json" \
  --target "${GIG_REPORT_CHAT:-8547730585}"
