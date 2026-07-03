#!/usr/bin/env bash
# defi-yield/run.sh — ONE bounded DeFi-yield pass (CLOUD-portable: wallet/API only, no browser).
# DEFAULT = DRY_RUN plan (decide-yield.py reads live DefiLlama pools + wallet balance, picks the pool via
# pure lib.pick_pool, sizes via lib.size_supply, PRINTS the plan). The real Aave/Spark supply() is the gated
# real-money increment (needs a wired signer + Base ETH gas) and is NOT present yet = fail-closed.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
DRY_RUN="${DRY_RUN:-true}"
EARN_MODE="${EARN_MODE:-observe}"
PLAN="$("$PY" "$HERE/decide-yield.py" 2>/dev/null | tail -1)"
if [ "$DRY_RUN" = "false" ] && [ "$EARN_MODE" = "execute" ]; then
  echo "{\"slot\":\"earn/defi-yield\",\"mode\":\"execute-blocked\",\"note\":\"real Aave supply() not wired yet (needs signer + Base ETH gas) — fail-closed\",\"plan\":${PLAN:-null}}"
  exit 0
fi
echo "{\"slot\":\"earn/defi-yield\",\"mode\":\"plan\",\"dry_run\":${DRY_RUN},\"plan\":${PLAN:-null}}"
