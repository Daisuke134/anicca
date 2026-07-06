#!/usr/bin/env bash
# Start (idempotent) the self-host x402-rs facilitator — the gasless settlement
# heart of the gig marketplace (SPEC.md P2.1). Colony agents call this facilitator's
# /verify + /settle instead of Coinbase's hosted facilitator: no CDP account, no
# human credential, self-held signer key only.
#
# Secrets (FACILITATOR_PRIVATE_KEY) live OUTSIDE this repo at
# ~/.anicca-signing/x402-facilitator/.env (gitignored, chmod 600) — never commit a key.
#
# Usage: ./start.sh            # start (idempotent, testnet: eip155:84532 Base Sepolia)
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

SECRETS_ENV="$HOME/.anicca-signing/x402-facilitator/.env"
[ -f "$SECRETS_ENV" ] || { echo "missing $SECRETS_ENV — generate a fresh FACILITATOR_PRIVATE_KEY first" >&2; exit 1; }
set -a
source "$SECRETS_ENV"
set +a
[ -n "${FACILITATOR_PRIVATE_KEY:-}" ] || { echo "FACILITATOR_PRIVATE_KEY not set in $SECRETS_ENV" >&2; exit 1; }

PORT="${PORT:-8405}"
BIN="$HERE/x402-rs/target/release/x402-facilitator"
mkdir -p state

if [ ! -x "$BIN" ]; then
  echo "building x402-facilitator (release, chain-eip155+chain-solana)..." >&2
  ( cd "$HERE/x402-rs" && cargo build --package x402-facilitator --features chain-eip155,chain-solana --release --locked )
fi

if ! curl -s -m3 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
  CONFIG="$HERE/config.json" PORT="$PORT" RUST_LOG="${RUST_LOG:-info}" \
    nohup "$BIN" > state/facilitator.log 2>&1 &
  for i in $(seq 1 15); do sleep 1; curl -s -m3 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 && break; done
fi
curl -s -m3 "http://127.0.0.1:$PORT/health" >/dev/null 2>&1 || { echo "facilitator failed to start — see state/facilitator.log" >&2; exit 1; }

echo "x402-rs facilitator live:"
echo "  local : http://127.0.0.1:$PORT"
echo "  chain : eip155:84532 (Base Sepolia, TESTNET)"
echo "  signer: (see $SECRETS_ENV -> FACILITATOR_ADDRESS)"
echo "  routes: /  /health  /supported  /verify  /settle"
