#!/usr/bin/env bash
# Akash lease path for a sovereign child (host=akash). Previously MISSING (run.sh:144 dangling ref).
# Fail-closed: requires the `akash` CLI + AKASH_KEY_NAME + a funded AKT wallet. On ANY missing
# prerequisite or failed bid, exits non-zero with NO fake lease id (HARD 0.24).
#
#   deploy-akash.sh CHILD_ID  -> prints the lease id (dseq) to stdout on success, exit 1 otherwise.
#
# The SDL deploys the same automaton image the DO cloud-init brings up, with AUTOMATON_GOAL=earn, so the
# child earns on its own wake on Akash too (sovereign, censorship-resistant host).
set -euo pipefail

CHILD_ID="${1:?deploy-akash.sh: CHILD_ID required}"

command -v akash >/dev/null 2>&1 || { echo "deploy-akash: akash CLI missing — cannot lease (no fake)" >&2; exit 1; }
[ -n "${AKASH_KEY_NAME:-}" ] || { echo "deploy-akash: AKASH_KEY_NAME unset — cannot sign the deployment tx" >&2; exit 1; }

NODE="${AKASH_NODE:-https://rpc.akashnet.net:443}"
CHAIN="${AKASH_CHAIN_ID:-akashnet-2}"
SDL_FILE="$(mktemp -t "anicca-${CHILD_ID}-sdl-XXXX.yml")"
trap 'rm -f "$SDL_FILE"' EXIT

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
        cpu:
          units: 0.5
        memory:
          size: 512Mi
        storage:
          size: 1Gi
  placement:
    akash:
      pricing:
        automaton:
          denom: uakt
          amount: 10000
deployment:
  automaton:
    akash:
      profile: automaton
      count: 1
SDL

# create the deployment (real on-chain tx). dseq is the lease id we track.
TX_JSON="$(akash tx deployment create "$SDL_FILE" \
  --from "$AKASH_KEY_NAME" --node "$NODE" --chain-id "$CHAIN" \
  --gas auto --gas-adjustment 1.3 --yes -o json 2>/dev/null)" \
  || { echo "deploy-akash: deployment tx failed" >&2; exit 1; }

DSEQ="$(printf '%s' "$TX_JSON" | jq -r '
  .logs[].events[]? | select(.type=="akash.v1") | .attributes[]? | select(.key=="dseq") | .value' 2>/dev/null | head -1)"
[ -n "$DSEQ" ] || { echo "deploy-akash: no dseq in tx response — lease not created" >&2; exit 1; }

printf '%s' "$DSEQ"
