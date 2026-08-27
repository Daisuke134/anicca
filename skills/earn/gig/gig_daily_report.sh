#!/usr/bin/env bash
# Daily Gig digest through the durable Telegram outbox.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/gig_paths.sh
source "$HERE/scripts/gig_paths.sh"

exec "${PYTHON:-python3}" "$GIG_DIR/scripts/telegram_report.py" daily \
  --connector-database "${GIG_REPLY_OUTBOX_DB:-$HOME/gig/connector-outbox.sqlite3}" \
  --telegram-database "${GIG_TELEGRAM_OUTBOX_DB:-$HOME/gig/telegram-outbox.sqlite3}" \
  --gig-dir "$GIG_STATE_DIR" \
  --runner-config "$GIG_RUNNER_DIR/config.json" \
  --target "${GIG_REPORT_CHAT:-}"
