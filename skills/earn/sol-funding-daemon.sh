#!/bin/bash
# 24/7 SOL->USDC funding daemon: whenever SOL lands in anicca's Solana wallet,
# auto-swap it to USDC on Base via relay.link. sol-to-usdc.py exits cleanly when no SOL.
set -a; . "$HOME/.openclaw/.env" 2>/dev/null; set +a
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
while true; do
  /opt/homebrew/bin/python3 "$HOME/anicca/skills/earn/sol-to-usdc.py" 2>&1
  sleep 60
done
