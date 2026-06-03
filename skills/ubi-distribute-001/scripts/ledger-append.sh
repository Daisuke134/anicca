#!/usr/bin/env bash
# ledger-append.sh — append-only writer for the UBI ledger.
#
# Appends one JSON line to ~/.openclaw/state/ubi-ledger.jsonl with shape:
#   {month, charity_name, charity_url, charity_addr, amount_usd, amount_usdc,
#    tx_hash, paid_at, status, post_url, basescan_url}
#
# Then refreshes aniccaai.com/donation by patching the `charity` block in:
#   1. ~/.openclaw/state/dashboard.json           (runtime canonical)
#   2. ~/anicca-products/apps/landing/public/dashboard.json (deployed by Netlify)
#
# Page shape (apps/landing/app/donation/page.tsx) expects:
#   d.charity.this_month  = {charity_name, charity_url, queued_amount_usd, payout_date}
#   d.charity.ledger      = [{month, charity_name, charity_url, amount_usd, paid_at, status, post_url}]
#   d.charity.total_given_usd, d.charity.org_count
#
# NEVER rewrites prior rows. Bad input → exit non-zero, ledger untouched.
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHARITIES="$SKILL_DIR/charities.json"
LEDGER_FILE="${UBI_LEDGER_FILE:-$HOME/.openclaw/state/ubi-ledger.jsonl}"
LOCAL_DASHBOARD="${ANICCA_DASHBOARD_FILE:-$HOME/.openclaw/state/dashboard.json}"
LANDING_DASHBOARD="${ANICCA_LANDING_DASHBOARD:-$HOME/anicca-products/apps/landing/public/dashboard.json}"

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

# Look up the charity homepage from charities.json (best effort).
charity_url=""
if [[ -f "$CHARITIES" ]]; then
  charity_url=$(jq -r --arg n "$charity" \
    '.[] | select(.name == $n) | .url // empty' "$CHARITIES" 2>/dev/null | head -n1)
fi

basescan_url=""
if [[ -n "$tx" ]]; then
  basescan_url="https://basescan.org/tx/$tx"
fi

mkdir -p "$(dirname "$LEDGER_FILE")"

# Canonical ledger row. Includes BOTH amount_usd (page-compatible) and
# amount_usdc (USDC-precise — for our skill they're identical, but keeping
# them separate is forward-compatible if Anicca ever swaps another stable).
row=$(jq -nc \
  --arg month "$month" \
  --arg charity "$charity" \
  --arg charity_url "$charity_url" \
  --arg addr "$addr" \
  --arg amount "$amount" \
  --arg tx "$tx" \
  --arg status "$status" \
  --arg paid_at "$paid_at" \
  --arg post_url "$post_url" \
  --arg basescan_url "$basescan_url" \
  '{month:$month, charity_name:$charity,
    charity_url:(if $charity_url == "" then null else $charity_url end),
    charity_addr:$addr,
    amount_usd:($amount|tonumber), amount_usdc:($amount|tonumber),
    tx_hash:(if $tx == "" then null else $tx end),
    paid_at:$paid_at, status:$status,
    post_url:(if $post_url == "" then null else $post_url end),
    basescan_url:(if $basescan_url == "" then null else $basescan_url end)}')

echo "$row" >> "$LEDGER_FILE"
echo "[ledger] appended row to $LEDGER_FILE" >&2

# Build the charity block once, replay for both dashboards. The block recomputes
# totals from the FULL ledger.jsonl so it stays consistent across restarts.
charity_block=$(python3 - "$LEDGER_FILE" "$charity" "$amount" "$status" "$paid_at" "$charity_url" "$month" <<'PY'
import json, sys
from collections import OrderedDict

ledger_path, name, amount, status, paid_at, charity_url, month = sys.argv[1:]
rows = []
try:
    with open(ledger_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            try: rows.append(json.loads(line))
            except json.JSONDecodeError: continue
except FileNotFoundError:
    rows = []

paid = [r for r in rows if r.get("status") in ("sent", "paid")]
total_given_usd = round(sum(float(r.get("amount_usd", 0) or 0) for r in paid), 2)
org_count = len({r.get("charity_name") for r in paid if r.get("charity_name")})

# Compute payout_date = 1st of next month (matches cron schedule "5 6 1 * *")
y, m = map(int, month.split("-"))
ny = y + (1 if m == 12 else 0)
nm = 1 if m == 12 else m + 1
payout_date = f"{ny:04d}-{nm:02d}-01"

charity_block = OrderedDict()
charity_block["this_month"] = {
    "charity_name": name,
    "charity_url": charity_url or None,
    "queued_amount_usd": float(amount),
    "payout_date": payout_date,
    "status": status,
}
charity_block["ledger"] = rows
charity_block["total_given_usd"] = total_given_usd
charity_block["org_count"] = org_count
charity_block["last_payout"] = rows[-1] if rows else None
print(json.dumps(charity_block))
PY
)

patch_dashboard() {
  local path="$1"
  [[ -f "$path" ]] || { echo "[ledger] skip $path (not present)" >&2; return 0; }
  local tmp
  tmp=$(mktemp)
  if jq --argjson c "$charity_block" '.charity = $c' "$path" >"$tmp" 2>/dev/null; then
    mv "$tmp" "$path"
    echo "[ledger] patched $path .charity ($(jq -r '.charity.ledger | length' "$path") rows, total \$$(jq -r '.charity.total_given_usd' "$path"))" >&2
  else
    rm -f "$tmp"
    echo "[ledger] dashboard patch failed for $path (non-fatal)" >&2
  fi
}

patch_dashboard "$LOCAL_DASHBOARD"
patch_dashboard "$LANDING_DASHBOARD"

# Optional Netlify build hook for paranoid refresh — declarative env, no
# hardcoded URL. ANICCA_LANDING_DASHBOARD already updated, so this is a
# belt-and-suspenders trigger for cache invalidation.
if [[ -n "${NETLIFY_BUILD_HOOK_DONATION:-}" ]]; then
  if curl -fsS -X POST -d '{}' "$NETLIFY_BUILD_HOOK_DONATION" >/dev/null 2>&1; then
    echo "[ledger] triggered Netlify build via NETLIFY_BUILD_HOOK_DONATION" >&2
  else
    echo "[ledger] Netlify build hook failed (non-fatal)" >&2
  fi
fi
