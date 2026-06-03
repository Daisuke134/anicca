#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# cert.sh — Akash client cert generate + publish.
#
# v1 = idempotent: skips if cert already published for the configured key.
# Reads from $AKASH_KEY (= default anicca-spawn-mother) and broadcasts on
# akashnet-2 via the configured RPC.
#
# This is the only on-chain action that does not require USDC — Akash cert
# tx is a no-fee operation. T3 in spec 13 § 2.

set -euo pipefail

AKASH_KEY="${AKASH_KEY:-anicca-spawn-mother}"
AKASH_RPC="${AKASH_RPC:-https://rpc.akashnet.net:443}"
AKASH_CHAIN_ID="${AKASH_CHAIN_ID:-akashnet-2}"
AKASH_KEYRING="${AKASH_KEYRING:-test}"

if ! command -v akash >/dev/null 2>&1; then
  echo "akash CLI not installed; brew install akash-network/tap/akash" >&2
  exit 10
fi

ADDR=$(akash keys show "$AKASH_KEY" -a --keyring-backend "$AKASH_KEYRING" 2>/dev/null || true)
if [[ -z "$ADDR" ]]; then
  echo "key '$AKASH_KEY' not found in keyring '$AKASH_KEYRING'" >&2
  exit 11
fi

# Check existing cert
if akash query cert list --owner "$ADDR" --node "$AKASH_RPC" -o json 2>/dev/null | \
   python3 -c "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('certificates') else 1)"; then
  echo "cert already published for $ADDR — skipping"
  exit 0
fi

echo "generating cert for $ADDR..."
akash tx cert generate client \
  --from "$AKASH_KEY" --keyring-backend "$AKASH_KEYRING" \
  --chain-id "$AKASH_CHAIN_ID" --node "$AKASH_RPC" \
  --gas auto --gas-adjustment 1.3 -y 2>&1 | tail -5

echo "publishing cert..."
akash tx cert publish client \
  --from "$AKASH_KEY" --keyring-backend "$AKASH_KEYRING" \
  --chain-id "$AKASH_CHAIN_ID" --node "$AKASH_RPC" \
  --gas auto --gas-adjustment 1.3 -y 2>&1 | tail -5

echo "cert published; verify via: akash query cert list --owner $ADDR --node $AKASH_RPC"
