#!/usr/bin/env bash
# #327c auto-watcher — fires Phase B (real anicca-001 spawn) autonomously once BOTH gates clear:
#   gate 1: parent wallet USDC >= MIN_USDC   (via anicca-wallet/scripts/balance.sh)
#   gate 2: Daytona org has >= 1 compute region (via /api/regions; CLI has no `regions` cmd)
# Idempotent: if anicca-001 already alive in colony.jsonl, it exits 0 without re-spawning.
# Logs one decision row per run to ~/.hermes/state/spawn-watcher.jsonl.
# Intended to run hourly from a Hermes cron (--no-agent). No human poll.
set -euo pipefail
JQ="$(command -v /opt/homebrew/bin/jq || command -v jq)"

MIN_USDC="${MIN_USDC:-5}"
CHILD_NAME="${CHILD_NAME:-anicca-001}"
HERMES_SKILLS="${HERMES_SKILLS:-/Users/anicca/.hermes/skills}"
SPAWN_CHILD="$HERMES_SKILLS/spawn-child/scripts/spawn-child.sh"
WALLET_BALANCE="$HERMES_SKILLS/anicca-wallet/scripts/balance.sh"
COLONY="${COLONY:-/Users/anicca/.hermes/state/colony.jsonl}"
WATCHLOG="${WATCHLOG:-/Users/anicca/.hermes/state/spawn-watcher.jsonl}"
SPEC="${SPEC:-/Users/anicca/anicca-oss/specs/00-MASTER.md}"
mkdir -p "$(dirname "$WATCHLOG")"

log_decision() {  # log_decision <decision> <usdc> <regions> <note>
  "$JQ" -nc \
    --arg ts "$(date -u +%FT%TZ)" \
    --arg decision "$1" --arg usdc "$2" --arg regions "$3" --arg note "$4" \
    '{ts:$ts, decision:$decision, wallet_usdc:($usdc|tonumber? // $usdc), daytona_regions:($regions|tonumber? // $regions), note:$note}' \
    >> "$WATCHLOG"
}

# Load env (Daytona key)
set -a
[ -f /Users/anicca/.hermes/.env ] && . /Users/anicca/.hermes/.env
[ -f /Users/anicca/.openclaw/.env ] && . /Users/anicca/.openclaw/.env
set +a

# Idempotency: already-alive child? then nothing to do.
if [ -f "$COLONY" ] && tail -n 50 "$COLONY" | "$JQ" -e --arg n "$CHILD_NAME" \
     'select(.child_id==$n and .status=="alive")' >/dev/null 2>&1; then
  log_decision "skip-already-alive" "n/a" "n/a" "$CHILD_NAME already alive in colony.jsonl"
  echo "spawn-watcher: $CHILD_NAME already alive — nothing to do"
  exit 0
fi

# Gate 1: wallet balance
USDC="0"
if [ -x "$WALLET_BALANCE" ]; then
  USDC=$("$WALLET_BALANCE" 2>/dev/null | "$JQ" -r '.usdc // 0' 2>/dev/null || echo 0)
fi

# Gate 2: Daytona regions (CLI has no `regions`; query the control-plane API)
REGION_COUNT=0
if [ -n "${DAYTONA_API_KEY:-}" ]; then
  REGION_COUNT=$(curl -sS --max-time 15 -H "Authorization: Bearer $DAYTONA_API_KEY" \
    "https://app.daytona.io/api/regions" 2>/dev/null \
    | "$JQ" 'if type=="array" then length elif type=="object" then ((.items // []) | length) else 0 end' 2>/dev/null || echo 0)
fi

WALLET_OK=$(awk -v b="$USDC" -v m="$MIN_USDC" 'BEGIN{print (b+0 >= m+0) ? 1 : 0}')
REGION_OK=$(awk -v r="$REGION_COUNT" 'BEGIN{print (r+0 >= 1) ? 1 : 0}')

if [ "$WALLET_OK" != "1" ] || [ "$REGION_OK" != "1" ]; then
  log_decision "gated" "$USDC" "$REGION_COUNT" "wallet_ok=$WALLET_OK region_ok=$REGION_OK (need usdc>=$MIN_USDC AND regions>=1)"
  echo "spawn-watcher: GATED — usdc=$USDC (need >=$MIN_USDC), regions=$REGION_COUNT (need >=1). No spawn."
  exit 0
fi

# Both gates clear — fire the REAL spawn (no overrides; live wallet probe path).
log_decision "spawning" "$USDC" "$REGION_COUNT" "both gates clear; invoking spawn-child --confirm $CHILD_NAME"
echo "spawn-watcher: gates clear (usdc=$USDC regions=$REGION_COUNT) — spawning $CHILD_NAME"

if "$SPAWN_CHILD" --confirm "$CHILD_NAME"; then
  log_decision "spawned" "$USDC" "$REGION_COUNT" "$CHILD_NAME spawned; promoting spec 00-MASTER row 5c"
  # On success: flip spec 00-MASTER row ⑤c to checked-off ✓ (Phase B proof now exists).
  if [ -f "$SPEC" ] && grep -q 'Phase B GATED on funding' "$SPEC"; then
    sed -i.bak \
      -e 's/⑤c「クラウド上で自己増殖」(skill BUILT,/⑤c「クラウド上で自己増殖」✓ (Wave 1 DONE,/' \
      -e 's/Phase B GATED on funding)/Phase B fired by spawn-watcher #327c)/' \
      "$SPEC" && rm -f "$SPEC.bak"
  fi
  echo "spawn-watcher: $CHILD_NAME spawned + spec promoted. Notify team-lead + close #327."
  exit 0
else
  rc=$?
  log_decision "spawn-failed" "$USDC" "$REGION_COUNT" "spawn-child exited $rc; colony row marked failed by orchestrator"
  echo "spawn-watcher: spawn-child failed (exit $rc) — see colony.jsonl + daytona logs $CHILD_NAME" >&2
  exit "$rc"
fi
