#!/usr/bin/env bash
# VPS で .env を 2 箇所揃え、Gateway を再起動する。
# 実行場所: VPS 上（ssh で入ったあと）、またはローカルから ssh で流し込む。
#
# 用法（VPS にログインした状態で）:
#   bash vps-ensure-env-and-restart-gateway.sh
#
# 用法（ローカルから）:
#   scp scripts/openclaw-vps/vps-ensure-env-and-restart-gateway.sh anicca@46.225.70.241:~/
#   ssh anicca@46.225.70.241 'bash ~/vps-ensure-env-and-restart-gateway.sh'

set -e
OPENCLAW_ENV="$HOME/.openclaw/.env"
HOME_ENV="$HOME/.env"

if [[ ! -f "$OPENCLAW_ENV" ]]; then
  echo "Error: $OPENCLAW_ENV not found. Run sync-env-to-vps.sh from repo first."
  exit 1
fi

echo "Ensuring $HOME_ENV exists (copy from $OPENCLAW_ENV)..."
cp -f "$OPENCLAW_ENV" "$HOME_ENV"
chmod 600 "$HOME_ENV"

echo "Restarting openclaw-gateway..."
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
systemctl --user daemon-reload
systemctl --user restart openclaw-gateway.service
sleep 2
systemctl --user status openclaw-gateway.service --no-pager || true

echo "Done. If active (running), open http://127.0.0.1:18789/ after SSH tunnel."
