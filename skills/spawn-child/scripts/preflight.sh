#!/usr/bin/env bash
# Preflight checks for spawn-child. Exits 0 on success; 64 on bad input; 75 on cost-cap fail.
# Emits a JSON status object to stdout on success.
#
# Env input:
#   __TEST_WALLET_OVERRIDE=<float>  — test-only; bypasses wallet.json balance read.
#                                     ONLY honored when ANICCA_TEST_MODE=1 is ALSO set.
#                                     Production runs MUST NOT set this; if set without
#                                     ANICCA_TEST_MODE=1 the preflight refuses with exit 64.
#   ANICCA_TEST_MODE=1              — gate for __TEST_WALLET_OVERRIDE
set -euo pipefail
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"

NAME="${1:-}"
[ -n "$NAME" ] || { echo "preflight: missing child name" >&2; exit 64; }
[[ "$NAME" =~ ^[a-z][a-z0-9-]{2,30}$ ]] || { echo "preflight: invalid name $NAME (must be ^[a-z][a-z0-9-]{2,30}\$)" >&2; exit 64; }

# Tool checks
command -v daytona >/dev/null || { echo "preflight: daytona CLI missing" >&2; exit 64; }
[ -n "$JQ" ] || { echo "preflight: jq missing" >&2; exit 64; }

# Env checks
set -a
[ -f /Users/anicca/.hermes/.env ] && . /Users/anicca/.hermes/.env
[ -f /Users/anicca/.openclaw/.env ] && . /Users/anicca/.openclaw/.env
set +a
[ -n "${DAYTONA_API_KEY:-}" ] || { echo "preflight: DAYTONA_API_KEY unset" >&2; exit 64; }

# Cost cap — read wallet balance.
# Refuse stray __TEST_WALLET_OVERRIDE in production (no ANICCA_TEST_MODE).
if [ -n "${__TEST_WALLET_OVERRIDE:-}" ] && [ "${ANICCA_TEST_MODE:-}" != "1" ]; then
  echo "preflight: __TEST_WALLET_OVERRIDE set without ANICCA_TEST_MODE=1 — refusing (real spawn must use live wallet probe)" >&2
  exit 64
fi
MIN_BALANCE=5.00
if [ -n "${__TEST_WALLET_OVERRIDE:-}" ] && [ "${ANICCA_TEST_MODE:-}" = "1" ]; then
  BAL="$__TEST_WALLET_OVERRIDE"
  echo "preflight: TEST MODE — wallet balance overridden to ${BAL}" >&2
elif [ -f /Users/anicca/.hermes/state/wallet.json ]; then
  BAL=$("$JQ" -r '.balance_usdc // 0' /Users/anicca/.hermes/state/wallet.json)
else
  BAL=0
fi

# Cost cap does not apply to a dry-run (it never spends money). SPAWN_DRY_RUN=1 skips it but
# still validates name/env/duplicate above.
if [ "${SPAWN_DRY_RUN:-0}" != "1" ]; then
  # Numeric compare via awk (bash can't do float). Message uses bare "5" to match DoD #7.
  if awk -v b="$BAL" -v m="$MIN_BALANCE" 'BEGIN{exit !(b+0 < m+0)}'; then
    echo "cost cap: ${BAL} USDC < 5 USDC required — child cannot be funded" >&2
    exit 75
  fi
fi

# Duplicate name guard — daytona list --format json returns {items:[...]}, use .items.
if daytona list --format json 2>/dev/null | "$JQ" -e --arg n "$NAME" '(.items // [])[] | select(.name == $n)' >/dev/null; then
  echo "preflight: a Daytona sandbox named $NAME already exists" >&2
  exit 64
fi

"$JQ" -n \
  --arg name "$NAME" \
  --arg balance "$BAL" \
  --arg min "$MIN_BALANCE" \
  '{name:$name, balance_usdc:($balance|tonumber), min_required:($min|tonumber), ok:true}'
