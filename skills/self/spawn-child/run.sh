#!/usr/bin/env bash
# self/spawn-child — Akash self-spawn READINESS gate (preparation-only capability).
#
# This is NOT the self/spawn birth flow (that already exists and is registry-live: it generates a child
# wallet/AgentMail inbox, provisions DO or Akash, registers on the dashboard — see ../spawn/run.sh). This
# skill answers ONE narrower question the Akash path specifically needs: "does the wallet that pays for
# the Akash lease actually hold enough AKT to fund the ACT-mint + deploy sequence right now?" per spec
# §20.1/§20.2 (2026-07-05): Akash escrow is uact (AEP-76), uact comes from minting AKT via akt-treasury.sh,
# and that mint needs real AKT on hand FIRST. The gate is pure arithmetic (lib/akt-cost-gate.js,
# node:test-covered) — it does not decide WHETHER to spawn; that judgment belongs to the calling agent
# (see SKILL.md "When to consider spawning"). This script only ever reads balances; it NEVER sends,
# swaps, mints, or creates a deployment.
#
# Usage:
#   run.sh                gate-only; queries the akash wallet's REAL on-chain AKT balance (read-only),
#                          compares to spawn_cost_akt+buffer_akt from config.json, prints the decision,
#                          appends one row to the durable ledger. Always exit 0 (NOT-YET is not a failure).
#   run.sh --config PATH   use an alternate config.json (e.g. for tests)
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SKILL_DIR/config.json"
while [ $# -gt 0 ]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --help) sed -n '1,20p' "$0"; exit 0 ;;
    *) echo "spawn-child: unknown arg $1" >&2; exit 64 ;;
  esac
done

JQ="$(command -v jq || true)"
NODE="$(command -v node || true)"
[ -n "$JQ" ]   || { echo "spawn-child: jq missing" >&2; exit 64; }
[ -n "$NODE" ] || { echo "spawn-child: node missing" >&2; exit 64; }
[ -f "$CONFIG" ] || { echo "spawn-child: config not found: $CONFIG" >&2; exit 64; }

set -a
[ -f "$HOME/.hermes/.env" ]   && . "$HOME/.hermes/.env"
[ -f "$HOME/.openclaw/.env" ] && . "$HOME/.openclaw/.env"
set +a

COST_AKT="$("$JQ" -r '.spawn_cost_akt' "$CONFIG")"
BUFFER_AKT="$("$JQ" -r '.buffer_akt' "$CONFIG")"
AKASH_KEY="${AKASH_KEY_NAME:-$("$JQ" -r '.akash_key_name' "$CONFIG")}"
export AKASH_KEYRING_BACKEND="${AKASH_KEYRING_BACKEND:-$("$JQ" -r '.akash_keyring_backend' "$CONFIG")}"

PS="${PROVIDER_SERVICES:-provider-services}"
command -v "$PS" >/dev/null 2>&1 || { echo "spawn-child: provider-services missing — cannot query balance (no fake)" >&2; exit 1; }

# node/chain resolution — same pattern as ../spawn/scripts/{deploy-akash,akt-treasury}.sh (fixed
# 2026-07-05: rpc[0] can be a bare host with no port and fails to dial; prefer a ported entry).
if [ -z "${AKASH_NODE:-}" ] || [ -z "${AKASH_CHAIN_ID:-}" ]; then
  META="${AKASH_META_URL:-https://raw.githubusercontent.com/akash-network/net/main/mainnet/meta.json}"
  MJ="$(curl -sSf "$META")" || { echo "spawn-child: meta.json fetch failed ($META)" >&2; exit 1; }
  export AKASH_CHAIN_ID="${AKASH_CHAIN_ID:-$(jq -r '.chain_id' <<<"$MJ")}"
  export AKASH_NODE="${AKASH_NODE:-$(jq -r '([.apis.rpc[].address | select(test(":[0-9]+"))] | .[0]) // .apis.rpc[0].address' <<<"$MJ")}"
fi
[ -n "${AKASH_NODE:-}" ] && [ -n "${AKASH_CHAIN_ID:-}" ] || { echo "spawn-child: could not resolve node/chain" >&2; exit 1; }

ADDR="$("$PS" keys show "$AKASH_KEY" -a 2>/dev/null || true)"
[ -n "$ADDR" ] || { echo "spawn-child: akash key '$AKASH_KEY' not in keyring — cannot query balance (no fake)" >&2; exit 1; }

# READ-ONLY balance query. No tx, no swap, no mint, no send.
UAKT="$("$PS" query bank balances "$ADDR" -o json 2>/dev/null | "$JQ" -r '.balances[]? | select(.denom=="uakt") | .amount' || true)"
UAKT="${UAKT:-0}"
BAL_AKT="$("$NODE" -e 'process.stdout.write(String(Number(process.argv[1]||0)/1e6))' "$UAKT")"

GATE="$("$NODE" -e '
  const { computeSpawnGate } = require(process.argv[1] + "/lib/akt-cost-gate");
  const g = computeSpawnGate({
    balanceAkt: Number(process.argv[2]),
    costAkt: Number(process.argv[3]),
    bufferAkt: Number(process.argv[4]),
  });
  process.stdout.write(JSON.stringify(g));
' "$SKILL_DIR" "$BAL_AKT" "$COST_AKT" "$BUFFER_AKT")"
READY="$(printf '%s' "$GATE" | "$JQ" -r '.ready')"

# durable ledger (fail-closed against /tmp — mirrors ../spawn/lib/state-path.js convention; every
# instance's spawn-readiness history lives where reboots/tmp-cleans cannot erase it).
STATE_DIR="${ANICCA_STATE_DIR:-$HOME/.hermes/state}"
case "$STATE_DIR" in
  /tmp/*|/private/tmp/*) echo "spawn-child: refusing non-durable state dir '$STATE_DIR'" >&2; exit 1 ;;
esac
mkdir -p "$STATE_DIR"
LEDGER="$STATE_DIR/spawn-child-gate.jsonl"
ROW="$("$JQ" -nc --arg ts "$(date -u +%FT%TZ)" --arg addr "$ADDR" --argjson bal "$BAL_AKT" --argjson gate "$GATE" \
  '{ts:$ts, akash_address:$addr, balance_akt:$bal, gate:$gate}')"
printf '%s\n' "$ROW" >> "$LEDGER"

echo "spawn-child: akash_address=${ADDR} balance_akt=${BAL_AKT} gate=${GATE}"

if [ "$READY" != "true" ]; then
  SHORT="$(printf '%s' "$GATE" | "$JQ" -r '.shortfallAkt')"
  THRESH="$(printf '%s' "$GATE" | "$JQ" -r '.thresholdAkt')"
  REASON="$(printf '%s' "$GATE" | "$JQ" -r '.reason')"
  echo "spawn-child: NOT-YET (${REASON}) — have ${BAL_AKT} AKT, need ${THRESH} AKT (short ${SHORT} AKT). No funding/deploy action taken; recorded to ${LEDGER}."
  exit 0
fi

echo "spawn-child: READY — balance ${BAL_AKT} AKT covers the funding+deploy threshold."
echo "spawn-child: this script never moves funds or creates a deployment itself. The calling agent decides whether/when to run the next steps below (spec §20.2):"
echo "  1) Jupiter: SOL -> USDC (Solana)"
echo "  2) Skip API 4-hop smart_relay: USDC(solana) -> AKT(${AKASH_CHAIN_ID}), recipient=${ADDR}, route = $("$JQ" -r '.funding_route' "$CONFIG")"
echo "  3) bash \"$SKILL_DIR/../spawn/scripts/akt-treasury.sh\"   # mint ACT from AKT (off the deploy critical path)"
echo "  4) AKASH_SDL_TEMPLATE=\"$SKILL_DIR/$("$JQ" -r '.sdl_template' "$CONFIG")\" bash \"$SKILL_DIR/../spawn/scripts/deploy-akash.sh\" <CHILD_ID>   # create -> bid -> lease -> manifest"
exit 0
