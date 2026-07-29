#!/usr/bin/env bash
# reality-verify-on-new-earn.sh — AUTONOMOUS trigger for the AGENTIC verification layer (#5 last mile).
#
# The reality-verifier (skills/self/reality-verify-spawn.sh) is expensive (a fresh claude spawn), so
# it must NOT run every tick. This script fires it ONLY when a loop books a NEW external:true earn
# row since the last check — i.e. exactly when there is a real "I earned" CLAIM worth auditing. With
# zero new earns (today's state) it spawns nothing and costs nothing. Called at the end of the
# deterministic verify-loops audit (6h cadence) so the colony self-verifies its earnings honesty with
# NO human in the loop ("they can't stop").
#
# Fail-safe: any error is swallowed (never breaks the caller). DRYRUN=1 prints intended spawns only.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SPAWN="$HERE/reality-verify-spawn.sh"
CURSOR_DIR="$HOME/.local/state/life-manager/state"; mkdir -p "$CURSOR_DIR" 2>/dev/null || true
DRYRUN="${REALITY_VERIFY_ON_EARN_DRYRUN:-}"

# (loop-name : GATE-0 earn ledger) — where each instance's external:true rows land. A missing file is
# simply skipped (that instance hasn't earned yet). Add rows here as new self-funded instances spawn.
LEDGERS=(
  "claude-p:$HOME/.anicca-founder/state/earn-ledger.jsonl"
  "franklin:$HOME/.blockrun/skills/earn/state/earn-ledger.jsonl"
  "franklin:$HOME/.blockrun/state/earn-ledger.jsonl"
  "franklin2:$HOME/.franklin2-home/.blockrun/state/earn-ledger.jsonl"
)

# newest external:true row's ts + a one-line claim, via python (portable, no jq). Empty if none.
newest_external() {  # $1=ledger path -> prints "<ts>\t<claim>" or nothing
  python3 - "$1" <<'PY' 2>/dev/null || true
import json,sys
p=sys.argv[1]
best=None
try:
    for l in open(p):
        l=l.strip()
        if not l: continue
        try: d=json.loads(l)
        except: continue
        if d.get("external") is True:
            ts=int(d.get("ts",0) or 0)
            if best is None or ts>best[0]: best=(ts,d)
except FileNotFoundError:
    sys.exit(0)
if best:
    d=best[1]
    claim=f"{d.get('source','?')} claims net {d.get('net_usdc','?')} USDC (tx {str(d.get('tx') or d.get('sig') or '-')[:16]}) — verify this is a real external earn, not internal/mock/narrate."
    print(f"{best[0]}\t{claim}")
PY
}

fired=0
for entry in "${LEDGERS[@]}"; do
  loop="${entry%%:*}"; ledger="${entry#*:}"
  [ -f "$ledger" ] || continue
  line="$(newest_external "$ledger")"; [ -z "$line" ] && continue
  ts="${line%%$'\t'*}"; claim="${line#*$'\t'}"
  # cursor keyed by loop+ledger basename so franklin's two ledgers don't clobber each other
  cur_key="$(printf '%s' "$loop-$(basename "$(dirname "$ledger")")" | tr -c 'a-zA-Z0-9._-' '_')"
  cursor="$CURSOR_DIR/.reality-verify-cursor-$cur_key"
  last="$(cat "$cursor" 2>/dev/null || echo 0)"
  [ "${ts:-0}" -le "${last:-0}" ] 2>/dev/null && continue   # already verified this (or older) earn
  if [ "$DRYRUN" = "1" ]; then
    echo "[reality-verify-on-earn] WOULD spawn: loop=$loop ledger=$ledger ts=$ts claim=\"$claim\""
    # DRYRUN must NOT mutate state — cursor is only advanced on a real spawn below.
  else
    echo "[reality-verify-on-earn] new external earn (loop=$loop ts=$ts) — spawning reality-verifier"
    bash "$SPAWN" "$loop" "$ledger" "$claim" >/dev/null 2>&1 || echo "[reality-verify-on-earn] spawn failed (non-fatal)"
    echo "$ts" > "$cursor"   # advance cursor only after a real verification spawn
  fi
  fired=$((fired+1))
done
echo "[reality-verify-on-earn] checked ${#LEDGERS[@]} ledgers, fired=$fired"
exit 0
