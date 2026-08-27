#!/usr/bin/env bash
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"  # launchd/cron have a minimal PATH; gog/openclaw/python3 binaries live in homebrew or ~/.local/bin
# connector-streak-verify.sh — deterministic daily wrapper for connector_streak_verify.py (7日streak
# goal). Sources ~/.openclaw/.env for GOG_ACCOUNT/GOG_KEYRING_PASSWORD (gog is always invoked this
# way in this repo, per the connector STARTUP prompt's own "set -a; . ~/.openclaw/.env; set +a"
# convention -- individual python scripts never source .env themselves).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY=/opt/homebrew/bin/python3; [ -x "$PY" ] || PY=python3

if [ -f "$HOME/.openclaw/.env" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$HOME/.openclaw/.env"
  set +a
fi

exec "$PY" "$HERE/connector_streak_verify.py"
