#!/usr/bin/env bash
# anicca local-default compute proxy — fully local, free, no server/API key.
#
# Anicca pays its OWN compute via ClawRouter/BlockRun (USDC x402) from its OWN
# wallet — exactly like Franklin. The user provides only SHELTER (this device);
# Anicca buys its own FOOD (inference). Free NVIDIA models when the wallet is
# empty; frontier models unlock automatically once USDC lands in the wallet.
#
# What this script DOES (and does NOT) do:
#   1. ensures a self-owned wallet at ~/.automaton/wallet.json (auto-gen, never a human key)
#   2. starts runtime/compute-proxy/proxy.mjs on :8402 (x402 self-pay, OpenAI-compatible)
#   3. exports OPENAI_BASE_URL + OPENAI_API_KEY (placeholder) + ANICCA_MODEL so an
#      OpenAI-compatible loop you pass in routes inference through the self-paid proxy
#   4. exec "$@" if you give it a loop command; otherwise HOLD the proxy in the
#      foreground and PRINT how to plug your loop in.
#
# Anicca SHIPS its loop at runtime/loop/index.mjs. Pass it as the loop command:
#   ./start-local.sh node runtime/loop/index.mjs
# With NO args this script only holds the self-pay proxy in the foreground and
# prints how to start the loop. Any OpenAI-compatible loop that reads
# OPENAI_BASE_URL / OPENAI_API_KEY (or ANICCA_MODEL) routes through the proxy.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT="${COMPUTE_PROXY_PORT:-8402}"
# per-instance EVM identity (#26 EQUALIZE, R4): prefer $ANICCA_HOME so every instance is
# isolated (its own key → its own on-chain identity, comparable P&L). Fall back to the legacy
# shared $HOME path ONLY if a live instance already has a wallet there — never regenerate or
# relocate an existing wallet, so a running instance's identity never changes. A fresh spawn
# with ANICCA_HOME set is born with its OWN wallet under $ANICCA_HOME.
EFFECTIVE_HOME="${ANICCA_HOME:-$HOME/.anicca}"
WALLET="$EFFECTIVE_HOME/.automaton/wallet.json"
LEGACY_WALLET="$HOME/.automaton/wallet.json"
if [ ! -f "$WALLET" ] && [ -f "$LEGACY_WALLET" ]; then
  WALLET="$LEGACY_WALLET"
fi
# Free BlockRun model = $0/call, no key. Frontier (paid) is chosen by your loop
# when the wallet has USDC; override with ANICCA_MODEL to pin one.
FREE_MODEL="${ANICCA_FREE_MODEL:-nvidia/deepseek-v4-flash}"

# --- 1. self-owned wallet (no human key) -------------------------------
if [ ! -f "$WALLET" ]; then
  mkdir -p "$(dirname "$WALLET")"
  WALLET_PATH="$WALLET" node -e '
    const {generatePrivateKey,privateKeyToAccount}=require("'"$HERE"'/../node_modules/viem/accounts");
    const fs=require("fs"); const pk=generatePrivateKey(); const wp=process.env.WALLET_PATH;
    fs.writeFileSync(wp,
      JSON.stringify({privateKey:pk,address:privateKeyToAccount(pk).address},null,2));
    fs.chmodSync(wp,0o600);
    console.error("[local] created self-owned wallet "+privateKeyToAccount(pk).address);
  '
else
  echo "[local] wallet preserved: $(WALLET_PATH="$WALLET" node -e 'console.log(JSON.parse(require("fs").readFileSync(process.env.WALLET_PATH)).address)')"
fi

# --- 1b. self-owned Solana wallet (fund via Binance SOL -> auto-swap to USDC) --
# Lets anyone top anicca up from Binance (which in many regions only sells SOL):
# send SOL here, the funding daemon swaps it to USDC on Base. No human key, no deps.
node "$HERE/ensure-solana-wallet.mjs" || echo "[local] WARN: solana wallet gen skipped"

# --- 2. start the x402 self-pay proxy ----------------------------------
# Readiness is proven by a real routed path (/v1/chat/completions), NOT /v1/models
# (proxy.mjs returns an empty data:[] for /models, so a 200 there proves nothing).
proxy_ready() {
  curl -sS --max-time 3 "http://127.0.0.1:$PORT/v1/chat/completions" \
    -H 'Content-Type: application/json' \
    -d "{\"model\":\"$FREE_MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"ping\"}]}" \
    >/dev/null 2>&1
}
if ! curl -sS --max-time 2 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1; then
  echo "[local] starting compute-proxy on :$PORT (x402 self-pay from own wallet)..."
  ( cd "$HERE" && COMPUTE_PROXY_PORT="$PORT" node proxy.mjs ) &
  # wait for the HTTP server to bind (port up). Live inference still needs the
  # network + a free-tier/funded wallet — see step 4 / verify notes.
  for _ in $(seq 1 20); do
    curl -sS --max-time 1 "http://127.0.0.1:$PORT/v1/models" >/dev/null 2>&1 && break
    sleep 0.5
  done
else
  echo "[local] compute-proxy already live on :$PORT"
fi

# --- 3. point any OpenAI-compatible loop at the self-paid proxy --------
export OPENAI_BASE_URL="http://127.0.0.1:$PORT/v1"
export OPENAI_API_KEY="${OPENAI_API_KEY:-x402-local-nokey}"   # placeholder; proxy pays in USDC, not this
# Use ClawRouter's `auto` router by default (no hardcoded model); ANICCA_MODEL can pin one.
export ANICCA_MODEL="${ANICCA_MODEL:-auto}"
# The loop requires ANICCA_HOME (no default) — derive it the same way install.sh does.
export ANICCA_HOME="${ANICCA_HOME:-$HOME/.anicca}"
# Expose the self-owned wallet address so the loop can read its balance (tier selection).
# Derive from the private key when the wallet file has no `address` field (older format).
export ANICCA_WALLET_ADDRESS="${ANICCA_WALLET_ADDRESS:-$(WALLET_PATH="$WALLET" node -e '
  try {
    const w=JSON.parse(require("fs").readFileSync(process.env.WALLET_PATH));
    if (w.address) { console.log(w.address); }
    else if (w.privateKey) {
      const {privateKeyToAccount}=require("'"$HERE"'/../node_modules/viem/accounts");
      console.log(privateKeyToAccount(w.privateKey).address);
    }
  } catch(e){ process.exit(0); }
')}"
echo "[local] inference -> $OPENAI_BASE_URL  model=$ANICCA_MODEL  (ClawRouter auto; free until wallet funded)"
echo "[local] ANICCA_HOME=$ANICCA_HOME  wallet=$ANICCA_WALLET_ADDRESS"

# --- 4. run YOUR loop, or hold the proxy + show how to plug one in -----
if [ "$#" -gt 0 ]; then
  echo "[local] launching your loop: $*"
  exec "$@"
else
  echo "[local] no loop command given — holding the self-pay compute proxy in foreground."
  echo "[local] start the anicca loop with:"
  echo "[local]     ./start-local.sh node runtime/loop/index.mjs   (from the repo root)"
  echo "[local] (or attach any OpenAI-compatible loop that reads OPENAI_BASE_URL=$OPENAI_BASE_URL)"
  echo "[local] fund frontier: send USDC to the wallet address above; your loop can then pick a paid model."
  echo "[local] (Ctrl-C to stop the proxy.)"
  wait
fi
