#!/usr/bin/env bash
# accumulate.sh — ONE paper-accumulation tick (money-safe): record a paper trade if there's an edge, then
# resolve any matured windows. Run every ~60s by launchd to build the ≥20 resolved-trade sample that gate.py
# needs to PASS. No real money anywhere (decide.py/resolve.py never sign or place an order).
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
LOG="$HOME/loops/earn-pm-trade/accumulate.log"; mkdir -p "$(dirname "$LOG")"
{
  echo "[$(date -u +%FT%TZ)] decide: $("$PY" "$HERE/decide.py" "${PM_BANKROLL:-8}" 2>&1 | tail -1)"
  echo "[$(date -u +%FT%TZ)] resolve: $("$PY" "$HERE/resolve.py" 2>&1 | tail -1)"
  echo "[$(date -u +%FT%TZ)] gate: $("$PY" "$HERE/gate.py" 2>&1 | head -1)"
} >> "$LOG" 2>&1
tail -3 "$LOG"
