#!/usr/bin/env bash
# fuel-usdc.sh — Phase 1 fuel option (3): create a USDC wallet, show a QR
# code for the user, wait for funding, write the address to $HOME/.local/state/life-manager/.env.
#
# Invoked by the external coding agent (per docs/INSTALL_BOOTSTRAP.md
# step 3.2) when the user picks fuel choice (3).
#
# Requirements:
#   - cdp CLI (Coinbase AgentKit) installed and in PATH
#   - CDP_API_KEY_NAME + CDP_API_KEY_PRIVATE present in $HOME/.local/state/life-manager/.env
#   - qrencode (= optional; falls back to text-only address display)
#
# What it does:
#   1. read or create a wallet via `cdp wallet create --network base-mainnet`
#   2. print the address as both text and ANSI QR
#   3. poll `cdp wallet balance` every 30s for max 30 min
#   4. once balance > 0, append WALLET_ADDR + HARNESS=openclaw-x402 to .env
#   5. stop (= the user's fuel is now self-funded via x402 micropayments)

set -uo pipefail

ANICCA_HOME="${ANICCA_HOME:-$HOME/.local/state/life-manager}"
ENV_FILE="$ANICCA_HOME/.env"
WALLET_STATE="$ANICCA_HOME/state/fuel-usdc-wallet.json"
MIN_USD="${FUEL_MIN_USD:-10}"
POLL_SEC="${FUEL_POLL_SEC:-30}"
TIMEOUT_MIN="${FUEL_TIMEOUT_MIN:-30}"

cyan(){ printf "\033[36m%s\033[0m\n" "$*"; }
green(){ printf "\033[32m%s\033[0m\n" "$*"; }
yellow(){ printf "\033[33m%s\033[0m\n" "$*"; }
red(){ printf "\033[31m%s\033[0m\n" "$*"; }

mkdir -p "$(dirname "$WALLET_STATE")"

# ─── 1. precond ────────────────────────────────────────────────────────
if ! command -v cdp >/dev/null 2>&1; then
  red "✗ cdp CLI not found. Install Coinbase AgentKit first:"
  yellow "    npm install -g @coinbase/cdp-cli"
  exit 2
fi

set -a; [ -f "$ENV_FILE" ] && source "$ENV_FILE"; set +a
if [ -z "${CDP_API_KEY_NAME:-}" ] || [ -z "${CDP_API_KEY_PRIVATE:-}" ]; then
  red "✗ CDP_API_KEY_NAME and CDP_API_KEY_PRIVATE must be set in $ENV_FILE"
  yellow "  Get keys at https://portal.cdp.coinbase.com (free tier)"
  exit 3
fi

# ─── 2. wallet creation or recovery ────────────────────────────────────
if [ -f "$WALLET_STATE" ]; then
  ADDR=$(jq -r .address "$WALLET_STATE" 2>/dev/null)
  if [ -n "$ADDR" ] && [ "$ADDR" != "null" ]; then
    green "✓ reusing existing wallet: $ADDR"
  fi
fi

if [ -z "${ADDR:-}" ]; then
  cyan "creating a new Coinbase AgentKit smart wallet on Base mainnet…"
  OUT=$(cdp wallet create --network base-mainnet --json 2>&1) || {
    red "✗ cdp wallet create failed"
    echo "$OUT"
    exit 4
  }
  ADDR=$(echo "$OUT" | jq -r '.address // .wallet_address // .wallet.address')
  if [ -z "$ADDR" ] || [ "$ADDR" = "null" ]; then
    red "✗ could not parse address from cdp output"
    echo "$OUT"
    exit 5
  fi
  echo "$OUT" > "$WALLET_STATE"
  green "✓ wallet created: $ADDR"
fi

# ─── 3. display address + QR ──────────────────────────────────────────
echo
green "================================================================"
green "  Send min \$$MIN_USD USDC on Base network to:"
echo
yellow "    $ADDR"
echo
green "================================================================"
echo
if command -v qrencode >/dev/null 2>&1; then
  qrencode -t ANSIUTF8 "ethereum:$ADDR@8453/transfer?address=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913" 2>/dev/null \
    || qrencode -t ANSIUTF8 "$ADDR" 2>/dev/null
else
  yellow "  (install qrencode for an inline QR — skipping)"
fi
echo
cyan "I'll poll every ${POLL_SEC}s for max ${TIMEOUT_MIN}min and stop"
cyan "once the wallet has any balance. Send the USDC any time before that."
echo

# ─── 4. balance polling ───────────────────────────────────────────────
END_TS=$(( $(date +%s) + TIMEOUT_MIN * 60 ))
ATTEMPT=0
while [ "$(date +%s)" -lt "$END_TS" ]; do
  ATTEMPT=$(( ATTEMPT + 1 ))
  BAL_RAW=$(cdp wallet balance "$ADDR" --network base-mainnet --token USDC --json 2>/dev/null || echo '{}')
  BAL_USD=$(echo "$BAL_RAW" | jq -r '.balance_usd // .balance // 0' 2>/dev/null)
  BAL_USD=${BAL_USD:-0}
  printf "\r  attempt %3d  balance ≈ \$%s    " "$ATTEMPT" "$BAL_USD"
  # Compare as float — jq returns a number
  if [ "$(awk -v b="$BAL_USD" 'BEGIN{print (b>0)?1:0}')" = "1" ]; then
    echo
    green "✓ balance detected: \$$BAL_USD"
    break
  fi
  sleep "$POLL_SEC"
done

if [ "$(awk -v b="${BAL_USD:-0}" 'BEGIN{print (b>0)?1:0}')" != "1" ]; then
  echo
  red "✗ timeout — no funds detected after ${TIMEOUT_MIN}min."
  yellow "  Re-run me later; the wallet at $ADDR is persisted."
  exit 6
fi

# ─── 5. .env append ───────────────────────────────────────────────────
cyan "writing fuel wiring into $ENV_FILE…"
# Strip any existing WALLET_ADDR/HARNESS lines first (idempotent)
TMP_ENV=$(mktemp)
[ -f "$ENV_FILE" ] && grep -vE '^(WALLET_ADDR|HARNESS)=' "$ENV_FILE" > "$TMP_ENV" || true
{
  cat "$TMP_ENV"
  echo "WALLET_ADDR=$ADDR"
  echo "HARNESS=openclaw-x402"
} > "$ENV_FILE"
chmod 600 "$ENV_FILE"
rm -f "$TMP_ENV"

echo
green "================================================================"
green "  ✅ USDC fuel wired."
green "     Wallet : $ADDR"
green "     Harness: openclaw-x402"
green "  Anicca's LLM inference will now be paid via x402 micropayments"
green "  out of this wallet. No subscription needed."
green "================================================================"
