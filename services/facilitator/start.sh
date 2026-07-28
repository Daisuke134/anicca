#!/usr/bin/env bash
# Start (idempotent) the self-host x402-rs facilitator — the gasless settlement
# heart of the gig marketplace (SPEC.md P2.1). Colony agents call this facilitator's
# /verify + /settle instead of Coinbase's hosted facilitator: no CDP account, no
# human credential, self-held signer key only.
#
# Secrets (FACILITATOR_PRIVATE_KEY) live OUTSIDE this repo at
# ~/.anicca-signing/x402-facilitator/.env (gitignored, chmod 600) — never commit a key.
#
# GIG_CHAIN selects the network (mirrors skills/economy/gig/lib/escrow.mjs's own toggle):
#   base-sepolia (default) -> config.json    (eip155:84532, testnet, no real money)
#   base                   -> config.mainnet.json (eip155:8453, MAINNET, real USDC -- see
#                              skills/economy/gig/WITNESS-RUNBOOK.md before ever using this)
#
# Usage: ./start.sh                 # start (idempotent, testnet: eip155:84532 Base Sepolia)
#        GIG_CHAIN=base ./start.sh  # start against Base MAINNET config instead
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

SECRETS_ENV="$HOME/.anicca-signing/x402-facilitator/.env"
[ -f "$SECRETS_ENV" ] || { echo "missing $SECRETS_ENV — generate a fresh FACILITATOR_PRIVATE_KEY first" >&2; exit 1; }
set -a
source "$SECRETS_ENV"
set +a
[ -n "${FACILITATOR_PRIVATE_KEY:-}" ] || { echo "FACILITATOR_PRIVATE_KEY not set in $SECRETS_ENV" >&2; exit 1; }

GIG_CHAIN="${GIG_CHAIN:-base-sepolia}"
if [ "$GIG_CHAIN" = "base" ]; then
  CONFIG_FILE="$HERE/config.mainnet.json"
  CHAIN_LABEL="eip155:8453 (Base MAINNET, REAL MONEY)"
else
  CONFIG_FILE="$HERE/config.json"
  CHAIN_LABEL="eip155:84532 (Base Sepolia, TESTNET)"
fi

PORT="${PORT:-8405}"
BIN="$HERE/x402-rs/target/release/x402-facilitator"
mkdir -p state

case "$PORT" in
  ''|*[!0-9]*) echo "PORT must be an integer between 1 and 65535" >&2; exit 1 ;;
esac
if [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
  echo "PORT must be an integer between 1 and 65535" >&2
  exit 1
fi
command -v jq >/dev/null 2>&1 || { echo "jq is required to build the runtime facilitator config" >&2; exit 1; }

# x402-rs reads the bind port from CONFIG when that field is present, so merely
# exporting PORT does not override the checked-in 8405. Build a per-port runtime
# copy and leave the canonical chain config unchanged.
RUNTIME_CONFIG="$HERE/state/config.${GIG_CHAIN}.${PORT}.json"
RUNTIME_CONFIG_TMP="${RUNTIME_CONFIG}.tmp.$$"
jq --argjson port "$PORT" '.port = $port' "$CONFIG_FILE" > "$RUNTIME_CONFIG_TMP"
chmod 600 "$RUNTIME_CONFIG_TMP"
mv "$RUNTIME_CONFIG_TMP" "$RUNTIME_CONFIG"

if [ ! -x "$BIN" ]; then
  echo "building x402-facilitator (release, chain-eip155+chain-solana)..." >&2
  ( cd "$HERE/x402-rs" && cargo build --package x402-facilitator --features chain-eip155,chain-solana --release --locked )
fi

if ! curl -s -m3 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  CONFIG="$RUNTIME_CONFIG" PORT="$PORT" RUST_LOG="${RUST_LOG:-info}" \
    nohup "$BIN" > state/facilitator.log 2>&1 &
  for i in $(seq 1 15); do sleep 1; curl -s -m3 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break; done
fi
curl -s -m3 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 || { echo "facilitator failed to start — see state/facilitator.log" >&2; exit 1; }

echo "x402-rs facilitator live:"
echo "  local : http://127.0.0.1:$PORT"
echo "  chain : $CHAIN_LABEL"
echo "  config: $RUNTIME_CONFIG"
echo "  signer: (see $SECRETS_ENV -> FACILITATOR_ADDRESS)"
echo "  routes: /  /health  /supported  /verify  /settle"
