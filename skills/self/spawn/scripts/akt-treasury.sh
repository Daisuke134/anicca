#!/usr/bin/env bash
# Off-path treasury — keeps the ACT (uact, the deployment-escrow denom) buffer topped by minting from AKT, so
# deploy-akash.sh NEVER mints per-spawn (that is what makes the per-spawn deploy ~20-30s instead of ~15min). Run on
# cron / wake, NOT on the deploy critical path.
#
# KEY constraints (verified on the real sandbox-2 chain, evidence/2026-06-27-real-sandbox2-e2e.md):
#  - ACT (uact) is the escrow denom; AKT (uakt) is gas only.
#  - `akash tx bme mint-act <X>uakt` CANCELS (cancel_reason 6 = BMCancelReasonMinimumMint) unless its OUTPUT clears
#    `bme params.min_mint` (10,000,000 uact). At P_mint≈0.66 a 25 AKT burn → ~16.5M uact = EXECUTED. So mint in chunks
#    whose output ≥ min_mint; verify via `bme ledger` status=executed (a canceled record refunds the AKT, mints nothing).
#  - Verify the credited uact in the act ledger / bank balance, not by assuming the tx code==0 means minted.
#
# Fail-soft for the swap, fail-LOUD for the mint: a mint that stays canceled exits !=0 so the operator/cron sees it;
# the per-spawn deploy still fail-closes on its own if uact is short, so a missed top-up never produces a fake deploy.
#   akt-treasury.sh  → tops ACT up to ACT_BUFFER_UACT; exits 0 if already ≥ buffer or a mint executed, !=0 on failure.
set -euo pipefail
AKASH="${AKASH_CLI:-akash}"
command -v "$AKASH" >/dev/null 2>&1 || { echo "akt-treasury: akash CLI missing" >&2; exit 1; }
: "${AKASH_KEY_NAME:?akt-treasury: AKASH_KEY_NAME unset — cannot sign with the own wallet}"
export AKASH_KEYRING_BACKEND="${AKASH_KEYRING_BACKEND:-test}" AKASH_YES=1   # NOT AKASH_OUTPUT=json (conflicts with `keys show -a`); queries pass -o json explicitly

# node/chain from the network meta.json (fetched once), overridable for tests/other nets
if [ -z "${AKASH_NODE:-}" ] || [ -z "${AKASH_CHAIN_ID:-}" ]; then
  META="${AKASH_META_URL:-https://raw.githubusercontent.com/akash-network/net/main/mainnet/meta.json}"
  MJ="$(curl -sSf "$META")" || { echo "akt-treasury: meta.json fetch failed" >&2; exit 1; }
  export AKASH_CHAIN_ID="${AKASH_CHAIN_ID:-$(jq -r '.chain_id' <<<"$MJ")}"
  export AKASH_NODE="${AKASH_NODE:-$(jq -r '.apis.rpc[0].address' <<<"$MJ")}"
fi
export AKASH_GAS="${AKASH_GAS:-500000}" AKASH_GAS_PRICES="${AKASH_GAS_PRICES:-0.025uakt}" AKASH_GAS_ADJUSTMENT="${AKASH_GAS_ADJUSTMENT:-1.5}"
[ -n "${AKASH_NODE:-}" ] && [ -n "${AKASH_CHAIN_ID:-}" ] || { echo "akt-treasury: could not resolve node/chain" >&2; exit 1; }

ADDR="$("$AKASH" keys show "$AKASH_KEY_NAME" -a)" || { echo "akt-treasury: key '$AKASH_KEY_NAME' not in keyring" >&2; exit 1; }

ACT_BUFFER="${ACT_BUFFER_UACT:-20000000}"      # target ACT on hand (≥ 2× min_mint so a few deploys never wait)
MIN_MINT="${AKASH_MIN_MINT_UACT:-10000000}"    # bme params.min_mint (10M uact) — a mint below this is canceled
MINT_UAKT="${TREASURY_MINT_UAKT:-25000000}"    # AKT to burn per top-up; must clear min_mint at the current price (25 AKT verified)

balance(){ "$AKASH" query bank balances "$ADDR" -o json 2>/dev/null | jq -r --arg d "$1" '.balances[]? | select(.denom==$d) | .amount' ; }

CUR_UACT="$(balance uact)"; CUR_UACT="${CUR_UACT:-0}"
if [ "$CUR_UACT" -ge "$ACT_BUFFER" ]; then
  echo "akt-treasury: ACT ok ($CUR_UACT uact ≥ $ACT_BUFFER) — no mint"; exit 0
fi

# need AKT (uakt) to burn for the mint
CUR_UAKT="$(balance uakt)"; CUR_UAKT="${CUR_UAKT:-0}"
if [ "$CUR_UAKT" -lt "$MINT_UAKT" ]; then
  # USDC→AKT swap HOOK (off-path): refill AKT from the agent's Base USDC via a no-human bridge when wired.
  if [ -n "${TREASURY_SWAP_CMD:-}" ]; then
    echo "akt-treasury: AKT low ($CUR_UAKT) — running TREASURY_SWAP_CMD"
    bash -c "$TREASURY_SWAP_CMD" || { echo "akt-treasury: swap failed" >&2; exit 1; }
    CUR_UAKT="$(balance uakt)"; CUR_UAKT="${CUR_UAKT:-0}"
  fi
  [ "$CUR_UAKT" -ge "$MINT_UAKT" ] || { echo "akt-treasury: insufficient AKT to mint ($CUR_UAKT < $MINT_UAKT); set TREASURY_SWAP_CMD to refill" >&2; exit 1; }
fi

echo "akt-treasury: minting ${MINT_UAKT}uakt → ACT (current uact=$CUR_UACT < $ACT_BUFFER)"
"$AKASH" tx bme mint-act "${MINT_UAKT}uakt" --from "$AKASH_KEY_NAME" >/dev/null 2>&1 \
  || { echo "akt-treasury: mint-act tx errored" >&2; exit 1; }

# the mint settles at the epoch. EXECUTED ⇒ uact RISES above the pre-mint level; CANCELED (output below min_mint) ⇒
# the AKT refunds and uact never rises. Poll the BALANCE DELTA — robust: the ledger's records[-1] is NOT the newest
# record (verified on sandbox-2: an executed mint left records[-1] pointing at an older canceled record).
for _ in $(seq 1 "${TREASURY_MINT_TRIES:-30}"); do
  NEW_UACT="$(balance uact)"; NEW_UACT="${NEW_UACT:-0}"
  [ "$NEW_UACT" -gt "$CUR_UACT" ] && { echo "akt-treasury: mint EXECUTED — uact $CUR_UACT → $NEW_UACT"; exit 0; }
  sleep "${AKASH_POLL_SLEEP:-3}"
done
echo "akt-treasury: mint did NOT credit uact in the window (likely CANCELED = output below min_mint $MIN_MINT — raise TREASURY_MINT_UAKT)" >&2; exit 1
