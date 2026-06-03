#!/usr/bin/env bash
# ledger-append.sh — append-only writer for the UBI ledger.
#
# Appends one JSON line to ~/.openclaw/state/ubi-ledger.jsonl with shape:
#   {month, charity_name, charity_addr, amount_usdc, tx_hash, paid_at,
#    status, post_url, basescan_url}
#
# Then refreshes aniccaai.com/donation by either
#   (a) curling $NETLIFY_BUILD_HOOK_DONATION (if set), or
#   (b) patching ~/.openclaw/state/dashboard.json's `charity.ledger` array
#       (picked up by the existing dashboard publisher).
#
# NEVER rewrites prior rows. Bad input → exit non-zero, ledger untouched.
set -euo pipefail

LEDGER_FILE="${UBI_LEDGER_FILE:-$HOME/.openclaw/state/ubi-ledger.jsonl}"
DASHBOARD_FILE="${ANICCA_DASHBOARD_FILE:-$HOME/.openclaw/state/dashboard.json}"

month=""; charity=""; addr=""; amount=""; tx=""; status=""; paid_at=""; post_url=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --month)    month="$2"; shift 2 ;;
    --charity)  charity="$2"; shift 2 ;;
    --addr)     addr="$2"; shift 2 ;;
    --amount)   amount="$2"; shift 2 ;;
    --tx)       tx="$2"; shift 2 ;;
    --status)   status="$2"; shift 2 ;;
    --paid-at)  paid_at="$2"; shift 2 ;;
    --post-url) post_url="$2"; shift 2 ;;
    *) echo "[ledger] unknown flag: $1" >&2; exit 64 ;;
  esac
done

for v in month charity addr amount status paid_at; do
  if [[ -z "${!v}" ]]; then
    echo "[ledger] missing required --$v" >&2
    exit 65
  fi
done

basescan_url=""
if [[ -n "$tx" ]]; then
  basescan_url="https://basescan.org/tx/$tx"
fi

mkdir -p "$(dirname "$LEDGER_FILE")"

row=$(jq -nc \
  --arg month "$month" \
  --arg charity "$charity" \
  --arg addr "$addr" \
  --arg amount "$amount" \
  --arg tx "$tx" \
  --arg status "$status" \
  --arg paid_at "$paid_at" \
  --arg post_url "$post_url" \
  --arg basescan_url "$basescan_url" \
  '{month:$month, charity_name:$charity, charity_addr:$addr,
    amount_usdc:($amount|tonumber), tx_hash:(if $tx == "" then null else $tx end),
    paid_at:$paid_at, status:$status,
    post_url:(if $post_url == "" then null else $post_url end),
    basescan_url:(if $basescan_url == "" then null else $basescan_url end)}')

echo "$row" >> "$LEDGER_FILE"
echo "[ledger] appended row to $LEDGER_FILE" >&2

# --- refresh aniccaai.com/donation -----------------------------------------
# Option A: Netlify build hook (preferred when configured).
if [[ -n "${NETLIFY_BUILD_HOOK_DONATION:-}" ]]; then
  if curl -fsS -X POST -d '{}' "$NETLIFY_BUILD_HOOK_DONATION" >/dev/null 2>&1; then
    echo "[ledger] triggered Netlify build via NETLIFY_BUILD_HOOK_DONATION" >&2
  else
    echo "[ledger] Netlify build hook failed (non-fatal)" >&2
  fi
fi

# Option B: patch dashboard.json (always done; downstream publisher pushes it).
if [[ -f "$DASHBOARD_FILE" ]]; then
  tmp=$(mktemp)
  if jq --argjson row "$row" \
       '.charity = (.charity // {}) | .charity.ledger = ((.charity.ledger // []) + [$row])
        | .charity.last_payout = $row
        | .charity.updated_at = now | (.charity.updated_at | tostring) as $t
        | .charity.updated_at = ($t)' \
       "$DASHBOARD_FILE" > "$tmp" 2>/dev/null; then
    mv "$tmp" "$DASHBOARD_FILE"
    echo "[ledger] patched $DASHBOARD_FILE charity.ledger (+1 row)" >&2
  else
    rm -f "$tmp"
    echo "[ledger] dashboard.json patch failed (non-fatal)" >&2
  fi
fi
