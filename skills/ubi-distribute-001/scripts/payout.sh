#!/usr/bin/env bash
# payout.sh — sends USDC to a charity recipient via anicca-payout-wallet.
#
# Usage:
#   bash payout.sh 0xAddr [amount_usdc]
#   bash payout.sh 0xAddr          # default amount = max(0.01, mrr * 0.10)
#   bash payout.sh 0xAddr 0        # DRY mode: no on-chain tx, ledger row only
#
# OR piped from select-charity.sh:
#   bash select-charity.sh | xargs bash payout.sh
#
# Amount is in USDC (human, not atomic). The underlying skill handles 6-decimal
# scaling. DRY mode (amount=0) appends a ledger row stamped status=dry-run and
# never invokes the payout-wallet skill.
set -uo pipefail

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYOUT_WALLET_SKILL="${ANICCA_PAYOUT_WALLET_DIR:-$HOME/.openclaw/skills/anicca-payout-wallet}"
LEDGER_APPEND="$SKILL_DIR/scripts/ledger-append.sh"
CFO_FILE="${ANICCA_CFO_FILE:-$HOME/.openclaw/skills/cfo-core/data/anicca-cfo.json}"
PAYOUT_PERCENT="${UBI_PAYOUT_PERCENT:-10}"   # spec 14 + team-lead = 10%
MIN_USDC="${UBI_MIN_USDC:-0.01}"

if [[ $# -lt 1 ]]; then
  echo "[payout] usage: payout.sh <0xAddress> [amount_usdc]" >&2
  exit 64
fi

to_addr="$1"
amount_arg="${2:-}"
if [[ ! "$to_addr" =~ ^0x[a-fA-F0-9]{40}$ ]]; then
  echo "[payout] invalid recipient address: $to_addr" >&2
  exit 65
fi

# --- compute amount ---------------------------------------------------------
if [[ -n "$amount_arg" ]]; then
  amount="$amount_arg"
else
  mrr=$(jq -r '.makes.monthly_total_usd // 0' "$CFO_FILE" 2>/dev/null || echo 0)
  # max(MIN_USDC, mrr * PCT/100), rounded to cent
  amount=$(awk -v m="$mrr" -v p="$PAYOUT_PERCENT" -v floor="$MIN_USDC" \
    'BEGIN { v = m * p / 100; if (v < floor + 0) v = floor + 0; printf "%.2f", v }')
fi

# --- DRY mode: amount == 0 → no tx, append intent row only ------------------
is_dry=0
if awk -v a="$amount" 'BEGIN { exit !(a + 0 == 0) }'; then
  is_dry=1
fi

month=$(date +%Y-%m)
paid_at=$(date -u +%Y-%m-%dT%H:%M:%SZ)
charity_name=$(jq -r --arg a "$to_addr" \
  '.[] | select((.base_addr|ascii_downcase) == ($a|ascii_downcase)) | .name' \
  "$SKILL_DIR/charities.json" 2>/dev/null | head -n1)
[[ -z "$charity_name" ]] && charity_name="unknown ($to_addr)"

if [[ "$is_dry" == "1" ]]; then
  intent=$(jq -nc \
    --arg month "$month" \
    --arg name "$charity_name" \
    --arg addr "$to_addr" \
    --arg amount "$amount" \
    --arg paid_at "$paid_at" \
    '{action:"dry-run", month:$month, charity_name:$name, charity_addr:$addr,
      amount_usdc:($amount|tonumber), paid_at:$paid_at,
      note:"no on-chain tx — DRY mode (amount=0)"}')
  echo "$intent"
  bash "$LEDGER_APPEND" \
    --month "$month" \
    --charity "$charity_name" \
    --addr "$to_addr" \
    --amount "$amount" \
    --tx "" \
    --status "dry-run" \
    --paid-at "$paid_at" \
    >&2 || true
  exit 0
fi

# --- non-zero amount: call anicca-payout-wallet skill ----------------------
# Single source of truth = ~/.openclaw/skills/anicca-payout-wallet/scripts/payout.py
# (the skill's run.sh wrapper redirects stdout to its own log, so we invoke
#  payout.py directly with the same env loading the wrapper does, so we can
#  capture the canonical JSON response and use its `action` as the status.)
#
# DRY pass-through: UBI_LIVE != "1" → forward --dry-run to the skill. The
# skill emits {"action":"dry-run", ...} and exits 0 without invoking cdp.
# Set UBI_LIVE=1 only after wallet > $1 USDC + Dais sign-off.
UBI_LIVE="${UBI_LIVE:-0}"
PAYOUT_PY="$PAYOUT_WALLET_SKILL/scripts/payout.py"
if [[ ! -f "$PAYOUT_PY" ]]; then
  echo "[payout] missing anicca-payout-wallet payout.py: $PAYOUT_PY" >&2
  exit 66
fi

dry_flag=""
if [[ "$UBI_LIVE" != "1" ]]; then
  dry_flag="--dry-run"
fi

tmp_out=$(mktemp)
tmp_err=$(mktemp)
trap 'rm -f "$tmp_out" "$tmp_err"' EXIT

# Match run.sh's env loading exactly (single source of truth: anicca-payout-wallet)
(
  set -a
  # shellcheck source=/dev/null
  source "$HOME/.openclaw/.env" 2>/dev/null || true
  set +a
  /opt/homebrew/bin/timeout --kill-after=10 60 \
    /opt/homebrew/bin/python3 "$PAYOUT_PY" \
      --to "$to_addr" --amount "$amount" $dry_flag
) >"$tmp_out" 2>"$tmp_err"
rc=$?

# The skill emits exactly one JSON object on stdout. Parse it.
skill_json=$(tail -n 1 "$tmp_out" 2>/dev/null | head -c 4096)
if [[ -z "$skill_json" ]]; then
  skill_json='{}'
fi

# Read `action` field as status (dry-run / sent / send-failed / no-destination / no-funds)
status=$(echo "$skill_json" | jq -r '.action // "unknown"' 2>/dev/null)
if [[ -z "$status" || "$status" == "null" ]]; then
  status="unknown"
fi
# If skill crashed before emitting JSON, attribute to send-failed with stderr peek
if [[ $rc -ne 0 && "$status" == "unknown" ]]; then
  status="send-failed"
fi

# Extract tx hash from the JSON if present, else scan stdout+stderr
tx_hash=$(echo "$skill_json" | jq -r '.tx_hash // empty' 2>/dev/null)
if [[ -z "$tx_hash" || "$tx_hash" == "null" ]]; then
  tx_hash=$(grep -oE '0x[a-fA-F0-9]{64}' "$tmp_out" "$tmp_err" 2>/dev/null | head -n1 || true)
fi

bash "$LEDGER_APPEND" \
  --month "$month" \
  --charity "$charity_name" \
  --addr "$to_addr" \
  --amount "$amount" \
  --tx "$tx_hash" \
  --status "$status" \
  --paid-at "$paid_at" \
  >&2 || true

jq -nc \
  --arg month "$month" \
  --arg name "$charity_name" \
  --arg addr "$to_addr" \
  --arg amount "$amount" \
  --arg tx "$tx_hash" \
  --arg status "$status" \
  --arg paid_at "$paid_at" \
  '{action:$status, month:$month, charity_name:$name, charity_addr:$addr,
    amount_usdc:($amount|tonumber), tx_hash:$tx, paid_at:$paid_at}'

exit $rc
