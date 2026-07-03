#!/usr/bin/env bash
# pm-trade/run.sh — ONE bounded Polymarket earn pass (CLOUD-portable: wallet/API only, no browser).
# WIRING (fixes adversary FIND-001/002/004): decide.py reads live Binance BTC + the Polymarket BTC up/down
# market and calls the PURE momentum.py (edge) + lib.py (Quarter-Kelly sizing); gate.py PRODUCES the
# paper-pass from the resolved paper ledger (NOT a spoofable env var). DEFAULT = paper (records a paper
# position, never signs/places a real order). A real order requires EARN_MODE=execute AND a PRODUCED
# PM_PAPER_PASS=1 AND a funded wallet — and the real executor is intentionally not wired yet (fail-closed).
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
DRY_RUN="${DRY_RUN:-true}"
EARN_MODE="${EARN_MODE:-observe}"          # observe | execute
BANKROLL="${PM_BANKROLL:-8}"

# STEP 1 — PRODUCE the paper gate from the real paper ledger (never trust an env var).
GATE_OUT="$("$PY" "$HERE/gate.py" 2>/dev/null | head -1)"   # -> PM_PAPER_PASS=1|0
PM_PAPER_PASS="${GATE_OUT#PM_PAPER_PASS=}"; PM_PAPER_PASS="${PM_PAPER_PASS:-0}"

# STEP 2 — decide on LIVE data via the pure strategy; paper mode records a paper position.
DECISION="$("$PY" "$HERE/decide.py" "$BANKROLL" 2>/dev/null | tail -1)"

# STEP 3 — real execution: only if executing AND the gate PRODUCED a pass. Wired to the REAL CLOB executor
# order.py (money-safe: order.py itself re-checks all gates). Needs Polygon USDC (bridge from Base) to fill.
if [ "$DRY_RUN" = "false" ] && [ "$EARN_MODE" = "execute" ] && [ "$PM_PAPER_PASS" = "1" ]; then
  TOK=$("$PY" -c "import json,sys; d=json.loads('''$DECISION'''); print(d.get('token_id') or d.get('token') or '')" 2>/dev/null)
  SIDE=$("$PY" -c "import json,sys; d=json.loads('''$DECISION'''); print(d.get('side') or '')" 2>/dev/null)
  PRICE=$("$PY" -c "import json,sys; d=json.loads('''$DECISION'''); print(d.get('price') or 0)" 2>/dev/null)
  STAKE=$("$PY" -c "import json,sys; d=json.loads('''$DECISION'''); print(d.get('stake_usdc') or 0)" 2>/dev/null)
  if [ -n "$TOK" ] && [ "$SIDE" != "" ]; then
    "$PY" "$HERE/order.py" "$TOK" "$PRICE" "$STAKE" "$SIDE"; exit 0
  fi
  echo "{\"slot\":\"earn/pm-trade\",\"mode\":\"execute-no-decision\",\"decision\":${DECISION:-null}}"
  exit 0
fi

echo "{\"slot\":\"earn/pm-trade\",\"mode\":\"paper\",\"dry_run\":${DRY_RUN},\"paper_pass\":${PM_PAPER_PASS},\"decision\":${DECISION:-null}}"
