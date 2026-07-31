#!/usr/bin/env bash
# send-qr-telegram.sh — deliver the live Remote Control link to Dais's phone as a scannable QR.
#
# The supervised `claude remote-control` server prints "space to show QR code", but it runs
# under launchd with no TTY, so nobody can press space. Per the official docs the QR encodes
# nothing more than the session URL, so we re-generate it ourselves from the server log and
# push it over Telegram instead.
#   https://code.claude.com/docs/en/remote-control#connect-from-another-device
#
# Usage: send-qr-telegram.sh [--dry-run]
#   --dry-run  build the PNG and print the URLs, but do not send.

set -euo pipefail

LOG="${REMOTE_CONTROL_LOG:-$HOME/.claude/logs/remote-control.log}"
OUT_DIR="${TMPDIR:-/tmp}/remote-claude-qr"
CHAT_ID="${TELEGRAM_ALERT_CHAT_ID:-8547730585}"
DRY_RUN=0
[[ "${1:-}" == "--dry-run" ]] && DRY_RUN=1

if [[ ! -r "$LOG" ]]; then
  echo "remote-control log not readable: $LOG" >&2
  exit 1
fi

# The server rewrites its status block continuously, so the last occurrence is the live one.
ENV_URL=$(grep -o 'https://claude\.ai/code?environment=env_[A-Za-z0-9]*' "$LOG" | tail -1 || true)
SESSION_URL=$(grep -o 'https://claude\.ai/code/session_[A-Za-z0-9]*' "$LOG" | tail -1 || true)

if [[ -z "$ENV_URL" ]]; then
  echo "no environment URL in $LOG — is the server connected? (launchctl print gui/\$UID/com.anicca.claude-remote-control)" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"
PNG="$OUT_DIR/remote-control-$(date +%Y%m%d-%H%M%S).png"

uv run --quiet --with 'qrcode[pil]' python - "$ENV_URL" "$PNG" <<'PY'
import sys
import qrcode

url, out = sys.argv[1], sys.argv[2]
img = qrcode.make(url, box_size=12, border=3)
img.save(out)
PY

if [[ $DRY_RUN -eq 1 ]]; then
  echo "env:     $ENV_URL"
  echo "session: ${SESSION_URL:-<none>}"
  echo "png:     $PNG"
  exit 0
fi

set -a
# shellcheck disable=SC1090
. "$HOME/.openclaw/.env"
set +a

CAPTION="Mac mini — Claude Remote Control
Scan with the iPhone camera to open Claude iOS, or tap Code in the app.
Device: $ENV_URL"
[[ -n "$SESSION_URL" ]] && CAPTION="$CAPTION
Live session: $SESSION_URL"

RESPONSE=$(curl -sS -X POST \
  "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendPhoto" \
  -F "chat_id=${CHAT_ID}" \
  -F "photo=@${PNG}" \
  -F "caption=${CAPTION}")

if ! printf '%s' "$RESPONSE" | grep -q '"ok":true'; then
  # Never echo $RESPONSE raw: on some errors Telegram reflects the request back with the token.
  echo "Telegram sendPhoto failed (see error_code in the API reply)" >&2
  printf '%s' "$RESPONSE" | sed "s/${TELEGRAM_BOT_TOKEN}/<redacted>/g" >&2
  exit 1
fi

echo "sent QR to Telegram chat ${CHAT_ID}: $PNG"
