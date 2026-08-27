#!/bin/bash
# SBI 7 USDC 着金監視 — Base mainnet 上の Anicca Automaton wallet を 1 時間ごとにポーリング
# 残高変化を検知したら Slack #metrics 通知 + CFO 再 build trigger + dispatch-log
# Earn-or-Die loop の "確定した過去形収益" の第 1 観測点

set -eu
ANICCA_HOME="${ANICCA_HOME:-$HOME/.openclaw}"
DATA="$ANICCA_HOME/skills/sbi-usdc-monitor/data"
mkdir -p "$DATA"
STATE="$DATA/state.json"
LOG="$DATA/log.jsonl"

WALLET="0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"
USDC_CONTRACT="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
RPC="https://base-rpc.publicnode.com"
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)

log() { echo "[$(date +%H:%M:%S)] $*" >&2; }

# eth_call USDC.balanceOf(WALLET)
ADDR_LOWER=$(echo "$WALLET" | sed 's/0x//' | tr 'A-Z' 'a-z')
PADDED=$(printf "%064s" "$ADDR_LOWER" | tr ' ' '0')
DATA_HEX="0x70a08231${PADDED}"

RESP=$(curl -sS -X POST -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$USDC_CONTRACT\",\"data\":\"$DATA_HEX\"},\"latest\"]}" \
  --max-time 15 "$RPC" 2>&1)

HEX=$(echo "$RESP" | jq -r '.result // empty')
if [ -z "$HEX" ] || [ "$HEX" = "null" ]; then
  log "FATAL: RPC returned no result: $RESP"
  echo "{\"ts\":\"$TS\",\"status\":\"rpc-fail\"}" >> "$LOG"
  exit 2
fi

# hex -> integer (USDC = 6 decimals)
BAL_RAW=$(printf "%d" "$HEX")
BAL_USDC=$(python3 -c "print(f'{$BAL_RAW / 1_000_000:.6f}')")
log "Current USDC balance: \$$BAL_USDC"

# Compare with previous state
PREV_USDC=$(jq -r '.balance_usdc // 0' "$STATE" 2>/dev/null || echo "0")
PREV_USDC=${PREV_USDC:-0}

DELTA=$(python3 -c "print(f'{float('$BAL_USDC') - float('$PREV_USDC'):.6f}')")
CHANGED=$(python3 -c "print(1 if abs(float('$BAL_USDC') - float('$PREV_USDC')) > 0.000001 else 0)")

if [ "$CHANGED" = "1" ]; then
  log "BALANCE CHANGED: prev=\$$PREV_USDC, now=\$$BAL_USDC, delta=\$$DELTA"

  # Slack notify
  if [ -n "${SLACK_BOT_TOKEN:-}" ] || { set -a; source "$ANICCA_HOME/.env" 2>/dev/null; set +a; [ -n "${SLACK_BOT_TOKEN:-}" ]; }; then
    set -a; source "$ANICCA_HOME/.env" 2>/dev/null; set +a
    MSG_EMOJI="💰"
    [ "$(python3 -c "print(1 if float('$DELTA') < 0 else 0)")" = "1" ] && MSG_EMOJI="💸"
    MSG="${MSG_EMOJI} Anicca Automaton wallet USDC: prev=\$${PREV_USDC} → now=\$${BAL_USDC} (Δ \$${DELTA}) — *確定収益/支出 on Base mainnet*"
    curl -sS -X POST https://slack.com/api/chat.postMessage \
      -H "Authorization: Bearer $SLACK_BOT_TOKEN" \
      -H "Content-type: application/json; charset=utf-8" \
      -d "$(jq -n --arg ch "C091G3PKHL2" --arg t "$MSG" '{channel:$ch,text:$t}')" >/dev/null || log "Slack notify failed"
  fi

  # Trigger CFO rebuild (incorporates wallet balance into Anicca's makes/landed)
  if [ -x "$ANICCA_HOME/skills/cfo-core/run-cfo-hourly.sh" ]; then
    log "Triggering CFO rebuild..."
    bash "$ANICCA_HOME/skills/cfo-core/run-cfo-hourly.sh" >/dev/null 2>&1 || log "CFO rebuild failed"
  fi
fi

# Update state
echo "{\"ts\":\"$TS\",\"balance_usdc\":\"$BAL_USDC\",\"hex\":\"$HEX\"}" > "$STATE"
echo "{\"ts\":\"$TS\",\"balance_usdc\":\"$BAL_USDC\",\"prev_usdc\":\"$PREV_USDC\",\"delta_usdc\":\"$DELTA\"}" >> "$LOG"

log "OK"
exit 0
