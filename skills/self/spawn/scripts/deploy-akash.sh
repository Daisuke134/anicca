#!/usr/bin/env bash
# Akash sovereign deploy via provider-services (own wallet / crypto = NO Console managed wallet = NO credit card
# = NO human in the loop). Accelerated + COMPLETE: one-time client cert (reused), fast RPC+chain from meta.json,
# fixed gas, and the FULL flow (deployment create -> POLL bids -> lease create -> wait lease -> send-manifest) so the
# child ACTUALLY boots. Funding (USDC->AKT swap + ACT mint) lives OFF this path in akt-treasury.sh — this script
# never swaps/mints, so per-spawn latency is just the tx flow (~20-30s, was ~3min).
# Fail-closed (HARD 0.24): missing CLI/key/dseq/bid/lease/manifest -> exit !=0, NO fake dseq.
#   deploy-akash.sh CHILD_ID  -> prints {"dseq","priceAmount","priceDenom"} (the winning bid's own settled
#   price, FIND-002/PROP-303c) as one JSON line to stdout on success, exit 1 otherwise.
set -euo pipefail
CHILD_ID="${1:?deploy-akash.sh: CHILD_ID required}"

PS="${PROVIDER_SERVICES:-provider-services}"
command -v "$PS" >/dev/null 2>&1 || { echo "deploy-akash: provider-services missing — cannot lease (no fake)" >&2; exit 1; }
: "${AKASH_KEY_NAME:?deploy-akash: AKASH_KEY_NAME unset — cannot sign with the own wallet}"
export AKASH_FROM="$AKASH_KEY_NAME" AKASH_KEYRING_BACKEND="${AKASH_KEYRING_BACKEND:-test}"
export AKASH_YES=1   # NOT AKASH_OUTPUT=json globally — it conflicts with `keys show -a` ("cannot use --output with --address"); each query/tx passes -o json explicitly

# fast RPC + chain id from the network's own meta.json — fetched ONCE (no TOCTOU); overridable (tests/other nets).
# Every provider-services call reads AKASH_NODE/AKASH_CHAIN_ID from the env, so the query and the txs hit ONE node.
if [ -z "${AKASH_NODE:-}" ] || [ -z "${AKASH_CHAIN_ID:-}" ]; then
  META="${AKASH_META_URL:-https://raw.githubusercontent.com/akash-network/net/main/mainnet/meta.json}"
  MJ="$(curl -sSf "$META")" || { echo "deploy-akash: meta.json fetch failed ($META)" >&2; exit 1; }
  export AKASH_CHAIN_ID="${AKASH_CHAIN_ID:-$(jq -r '.chain_id' <<<"$MJ")}"
  # rpc[0] is sometimes a bare host with NO port (e.g. https://rpc.akt.dev/rpc) -> provider-services
  # fails to dial it ("missing port in address", verified live 2026-07-05). Prefer the first entry that
  # HAS an explicit port; fall back to rpc[0] only if none do.
  export AKASH_NODE="${AKASH_NODE:-$(jq -r '([.apis.rpc[].address | select(test(":[0-9]+"))] | .[0]) // .apis.rpc[0].address' <<<"$MJ")}"
fi
export AKASH_GAS="${AKASH_GAS:-500000}" AKASH_GAS_PRICES="${AKASH_GAS_PRICES:-0.025uakt}" AKASH_GAS_ADJUSTMENT="${AKASH_GAS_ADJUSTMENT:-1.5}"   # FIXED gas (real deployment-create gasUsed=138662 + buffer) — NO --gas auto simulation round-trip
[ -n "${AKASH_CHAIN_ID:-}" ] && [ -n "${AKASH_NODE:-}" ] || { echo "deploy-akash: could not resolve node/chain" >&2; exit 1; }

ADDR="$("$PS" keys show "$AKASH_KEY_NAME" -a)" || { echo "deploy-akash: key '$AKASH_KEY_NAME' not in keyring" >&2; exit 1; }

# one-time client cert — published once, reused by EVERY deploy (NOT per-spawn). Only skip if a VALID cert exists.
if ! "$PS" query cert list --owner "$ADDR" -o json 2>/dev/null \
     | jq -e '.certificates[]? | select((.certificate.state // .state)=="valid")' >/dev/null 2>&1; then
  "$PS" tx cert generate client --from "$AKASH_KEY_NAME" -y >/dev/null 2>&1 || true
  "$PS" tx cert publish  client --from "$AKASH_KEY_NAME" -y >/dev/null 2>&1 \
    || { echo "deploy-akash: cert publish failed" >&2; exit 1; }
fi

SDL_FILE="$(mktemp -t "anicca-${CHILD_ID}-sdl-XXXX.yml")"
trap 'rm -f "$SDL_FILE"' EXIT
PRICE_DENOM="${AKASH_PRICE_DENOM:-uact}"; PRICE_AMOUNT="${AKASH_PRICE_AMOUNT:-10000}"   # AEP-76: escrow MUST be uact (NOT uakt); gas stays uakt
if [ -n "${AKASH_SDL_TEMPLATE:-}" ]; then
  # external template (skills/self/spawn-child/sdl/child.yaml) — image-independent (public node:22 base,
  # git-clones the OSS repo at boot), so it never depends on a custom registry image being reachable.
  [ -f "$AKASH_SDL_TEMPLATE" ] || { echo "deploy-akash: AKASH_SDL_TEMPLATE not found: $AKASH_SDL_TEMPLATE" >&2; exit 1; }
  CHILD_ID="$CHILD_ID" PRICE_DENOM="$PRICE_DENOM" PRICE_AMOUNT="$PRICE_AMOUNT" \
    envsubst '${CHILD_ID} ${PRICE_DENOM} ${PRICE_AMOUNT}' < "$AKASH_SDL_TEMPLATE" > "$SDL_FILE"
else
cat > "$SDL_FILE" <<SDL
version: "2.0"
services:
  automaton:
    image: ${AKASH_IMAGE:-node:22-bookworm}
    env:
      - AUTOMATON_GOAL=earn
      - ANICCA_CHILD_ID=${CHILD_ID}
    command: ["/bin/sh","-c"]
    args:
      - |
        apt-get update && apt-get install -y git python3 python3-pip
        git clone --depth 1 https://github.com/Daisuke134/life-manager /opt/anicca
        cd /opt/anicca && ./install.sh && node runtime/loop/index.mjs
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
fi

# 1. create the deployment. dseq lives in the EventDeploymentCreated `id` attribute, whose VALUE is a JSON string
#    {"owner":..,"dseq":".."} — provider-services -o json emits decoded events (verified on real sandbox-2).
CREATE="$("$PS" tx deployment create "$SDL_FILE" --from "$AKASH_KEY_NAME" --deposit "${AKASH_DEPOSIT:-5000000uact}" -y -o json 2>/dev/null)" \
  || { echo "deploy-akash: deployment create tx errored" >&2; exit 1; }
[ "$(jq -r '.code // 0' <<<"$CREATE")" = "0" ] \
  || { echo "deploy-akash: deployment tx failed code=$(jq -r '.code' <<<"$CREATE") log=$(jq -r '.raw_log // ""' <<<"$CREATE" | head -c160)" >&2; exit 1; }
DSEQ="$(jq -r 'first(.events[]? | select(.type=="akash.deployment.v1.EventDeploymentCreated") | .attributes[]? | select(.key=="id") | (.value|fromjson).dseq) // empty' <<<"$CREATE")"
[ -n "$DSEQ" ] && [[ "$DSEQ" =~ ^[0-9]+$ ]] \
  || { echo "deploy-akash: no numeric dseq in tx response — lease not created" >&2; exit 1; }

# 2. POLL bids (no fixed 30s sleep). Pick the CHEAPEST OPEN bid (FIND-002). Capture the WHOLE selected
# bid object (not just .bid.id) so the settled price (FIND-002/PROP-303c) is derived from the SAME
# selection that wins the lease, never a second, independent bid-list query.
SELECTED=""
for _ in $(seq 1 30); do
  SELECTED="$("$PS" query market bid list --owner "$ADDR" --dseq "$DSEQ" --state open -o json 2>/dev/null \
         | jq -c '[.bids[]? | select((.bid.state // "open")=="open")]
                  | sort_by(.bid.price.amount | tonumber? // 1e18) | .[0] // empty')"
  [ -n "$SELECTED" ] && [ "$SELECTED" != "null" ] && break
  SELECTED=""; sleep "${AKASH_POLL_SLEEP:-2}"
done
[ -n "$SELECTED" ] || { echo "deploy-akash: no open bids for dseq $DSEQ" >&2; exit 1; }
BID="$(jq -c '.bid.id' <<<"$SELECTED")"   # bid_id path = .bid.id (verified)
GSEQ="$(jq -r '.gseq' <<<"$BID")"; OSEQ="$(jq -r '.oseq' <<<"$BID")"; PROVIDER="$(jq -r '.provider' <<<"$BID")"
[ -n "$PROVIDER" ] && [ "$PROVIDER" != "null" ] || { echo "deploy-akash: bid has no provider" >&2; exit 1; }
SETTLED_PRICE_AMOUNT="$(jq -r '.bid.price.amount' <<<"$SELECTED")"
SETTLED_PRICE_DENOM="$(jq -r '.bid.price.denom' <<<"$SELECTED")"
[ -n "$SETTLED_PRICE_AMOUNT" ] && [ "$SETTLED_PRICE_AMOUNT" != "null" ] && [ -n "$SETTLED_PRICE_DENOM" ] && [ "$SETTLED_PRICE_DENOM" != "null" ] \
  || { echo "deploy-akash: selected bid missing price fields" >&2; exit 1; }

# 3. accept the bid (create the lease) — verify the tx landed (code==0).
LEASE="$("$PS" tx market lease create --dseq "$DSEQ" --gseq "$GSEQ" --oseq "$OSEQ" --provider "$PROVIDER" \
          --from "$AKASH_KEY_NAME" -y -o json 2>/dev/null)" \
  || { echo "deploy-akash: lease create tx errored" >&2; exit 1; }
[ "$(jq -r '.code // 0' <<<"$LEASE")" = "0" ] \
  || { echo "deploy-akash: lease create failed code=$(jq -r '.code' <<<"$LEASE")" >&2; exit 1; }

# 4. wait for the lease to be ACTIVE, then send the manifest (retry — the provider must see the lease) (FIND-007).
ACTIVE=""
for _ in $(seq 1 20); do
  ACTIVE="$("$PS" query market lease list --owner "$ADDR" --dseq "$DSEQ" -o json 2>/dev/null \
            | jq -r 'first(.leases[]? | select((.lease.state // "")=="active") | .lease.state) // empty')"
  [ -n "$ACTIVE" ] && break
  sleep "${AKASH_POLL_SLEEP:-2}"
done
[ -n "$ACTIVE" ] || { echo "deploy-akash: lease never became active for dseq $DSEQ" >&2; exit 1; }
SENT=""
for _ in $(seq 1 5); do
  if "$PS" send-manifest "$SDL_FILE" --dseq "$DSEQ" --provider "$PROVIDER" --from "$AKASH_KEY_NAME" >/dev/null 2>&1; then
    SENT=1; break
  fi
  sleep "${AKASH_POLL_SLEEP:-2}"
done
[ -n "$SENT" ] || { echo "deploy-akash: send-manifest failed after retries" >&2; exit 1; }

printf '{"dseq":"%s","priceAmount":"%s","priceDenom":"%s"}' "$DSEQ" "$SETTLED_PRICE_AMOUNT" "$SETTLED_PRICE_DENOM"
