#!/bin/bash
LIFE_MANAGER_REPO="${LIFE_MANAGER_REPO:-$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$LIFE_MANAGER_REPO" ] || { echo "LIFE_MANAGER_REPO could not be resolved" >&2; exit 2; }
export LIFE_MANAGER_REPO
# 24/7 SOL->USDC funding daemon: whenever SOL lands in anicca's Solana wallet,
# auto-swap it to USDC on Base via relay.link. sol-to-usdc.py exits cleanly when no SOL.
set -a; . "$HOME/.local/state/life-manager/.env" 2>/dev/null; set +a
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
while true; do
  /opt/homebrew/bin/python3 "$LIFE_MANAGER_REPO/skills/earn/sol-to-usdc.py" 2>&1
  sleep 60
done
