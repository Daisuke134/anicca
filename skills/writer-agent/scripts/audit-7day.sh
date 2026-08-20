#!/usr/bin/env bash
# Sunday 22:00 exact8 public/media/language/SEO/learning audit.
set -euo pipefail

export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"

set -a
. "$HOME/.openclaw/.env" 2>/dev/null || true
set +a
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="${ARTICLE_SKILL_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
exec python3 "$SKILL_DIR/scripts/article_weekly_audit.py" \
  --skill-dir "$SKILL_DIR" \
  --target "${TELEGRAM_TARGET_ID:-8547730585}"
