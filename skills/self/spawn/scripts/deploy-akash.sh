#!/usr/bin/env bash
# Akash sovereign deploy via provider-services (own wallet / crypto = NO Console managed wallet = NO credit card
# = NO human in the loop). Accelerated + COMPLETE: one-time client cert (reused), fast RPC+chain from the network's
# meta.json, fixed gas, and the FULL flow (deployment create -> POLL bids -> lease create -> send-manifest) so the
# child ACTUALLY boots. Funding (USDC->AKT swap + ACT mint) lives OFF this path in akt-treasury.sh — this script
# never swaps/mints, so per-spawn latency is just the tx flow (~20-30s, was ~3min).
# Fail-closed (HARD 0.24): missing CLI/key/dseq/bid/lease/manifest -> exit !=0, NO fake dseq.
#   deploy-akash.sh CHILD_ID  -> prints the lease id (dseq) to stdout on success, exit 1 otherwise.
set -euo pipefail
CHILD_ID="${1:?deploy-akash.sh: CHILD_ID required}"

PS="${PROVIDER_SERVICES:-provider-services}"
command -v "$PS" >/dev/null 2>&1 || { echo "deploy-akash: provider-services missing — cannot lease (no fake)" >&2; exit 1; }
: "${AKASH_KEY_NAME:?deploy-akash: AKASH_KEY_NAME unset — cannot sign with the own wallet}"
export AKASH_FROM="$AKASH_KEY_NAME" AKASH_KEYRING_BACKEND="${AKASH_KEYRING_BACKEND:-test}"

# fast RPC + chain id from the network's own meta.json (docs: cli/configuration); overridable (tests / other nets)
META="${AKASH_META_URL:-https://raw.githubusercontent.com/akash-network/net/main/mainnet/meta.json}"
export AKASH_CHAIN_ID="${AKASH_CHAIN_ID:-$(curl -sSf "$META" | jq -r '.chain_id')}"
export AKASH_NODE="${AKASH_NODE:-$(curl -sSf "$META" | jq -r '.apis.rpc[0].address')}"
export AKASH_GAS_PRICES="${AKASH_GAS_PRICES:-0.025uakt}" AKASH_GAS_ADJUSTMENT="${AKASH_GAS_ADJUSTMENT:-1.5}"
[ -n "$AKASH_CHAIN_ID" ] && [ -n "$AKASH_NODE" ] || { echo "deploy-akash: could not resolve node/chain from meta.json" >&2; exit 1; }

ADDR="$("$PS" keys show "$AKASH_KEY_NAME" -a)" || { echo "deploy-akash: key '$AKASH_KEY_NAME' not in keyring" >&2; exit 1; }

# one-time client cert — published once, reused by EVERY deploy (NOT per-spawn). Idempotent.
if ! "$PS" query cert list --owner "$ADDR" --node "$AKASH_NODE" -o json 2>/dev/null | jq -e '.certificates[0]' >/dev/null 2>&1; then
  "$PS" tx cert generate client --from "$AKASH_KEY_NAME" -y >/dev/null 2>&1 || true
  "$PS" tx cert publish  client --from "$AKASH_KEY_NAME" -y >/dev/null 2>&1 \
    || { echo "deploy-akash: cert publish failed" >&2; exit 1; }
fi

SDL_FILE="$(mktemp -t "anicca-${CHILD_ID}-sdl-XXXX.yml")"
trap 'rm -f "$SDL_FILE"' EXIT
PRICE_DENOM="${AKASH_PRICE_DENOM:-uact}"; PRICE_AMOUNT="${AKASH_PRICE_AMOUNT:-10000}"
cat > "$SDL_FILE" <<SDL
version: "2.0"
services:
  automaton:
    image: ghcr.io/conway-research/automaton:latest
    env:
      - AUTOMATON_GOAL=earn
      - ANICCA_CHILD_ID=${CHILD_ID}
    expose:
      - port: 8080
        as: 80
        to:
          - global: true
profiles:
  compute:
    automaton:
      resources:
        cpu: { units: 0.5 }
        memory: { size: 512Mi }
        storage: { size: 1Gi }
  placement:
    akash:
      pricing:
        automaton:
          denom: ${PRICE_DENOM}
          amount: ${PRICE_AMOUNT}
deployment:
  automaton:
    akash:
      profile: automaton
      count: 1
SDL

# 1. create the deployment (sync broadcast + json). dseq is the lease id we track.
DSEQ="$("$PS" tx deployment create "$SDL_FILE" --from "$AKASH_KEY_NAME" -y -o json 2>/dev/null \
        | jq -r '.. | .dseq? // empty' | head -1)"
[ -n "$DSEQ" ] || { echo "deploy-akash: no dseq — deployment tx failed" >&2; exit 1; }

# 2. POLL bids (no fixed 30s sleep — break on the first bid; ~5-15s typical)
BID=""
for _ in $(seq 1 30); do
  BID="$("$PS" query market bid list --owner "$ADDR" --dseq "$DSEQ" --node "$AKASH_NODE" -o json 2>/dev/null \
         | jq -c '.bids[0].bid.bid_id // empty')"
  [ -n "$BID" ] && break
  sleep 2
done
[ -n "$BID" ] || { echo "deploy-akash: no bids for dseq $DSEQ" >&2; exit 1; }
GSEQ="$(jq -r '.gseq' <<<"$BID")"; OSEQ="$(jq -r '.oseq' <<<"$BID")"; PROVIDER="$(jq -r '.provider' <<<"$BID")"

# 3. accept the bid (create the lease) + 4. ship the manifest -> the child ACTUALLY boots
"$PS" tx market lease create --dseq "$DSEQ" --gseq "$GSEQ" --oseq "$OSEQ" --provider "$PROVIDER" \
  --from "$AKASH_KEY_NAME" -y >/dev/null 2>&1 || { echo "deploy-akash: lease create failed" >&2; exit 1; }
"$PS" send-manifest "$SDL_FILE" --dseq "$DSEQ" --provider "$PROVIDER" --from "$AKASH_KEY_NAME" >/dev/null 2>&1 \
  || { echo "deploy-akash: send-manifest failed" >&2; exit 1; }

printf '%s' "$DSEQ"
