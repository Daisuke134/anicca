#!/usr/bin/env bash
# pm-trade/run.sh — ONE bounded Polymarket earn pass (CLOUD-portable: wallet/API only, no browser).
# DEFAULT = DRY_RUN paper mode (HARD 0.31 + REQ-PMTRADE paper-first). Real orders ONLY when a human-free
# gate is met: EARN_MODE=execute AND PM_PAPER_PASS=1 (paper P&L tracked backtest) AND a funded Polygon
# wallet. The MODEL (the loop) decides market/side/size; lib.py is the pure sizing math; pm-paper.py is the
# read-only mechanics. Never posts a real order in the default path. Reports one-line JSON.
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$(command -v python3)"
DRY_RUN="${DRY_RUN:-true}"                 # default paper
EARN_MODE="${EARN_MODE:-observe}"          # observe | execute
LEDGER_DIR="$HOME/loops/earn-pm-trade"; mkdir -p "$LEDGER_DIR"

# STEP 1 — paper mechanics on LIVE data (no key, no money): discover contested markets + touch.
DISCOVER="$("$PY" "$HERE/pm-paper.py" discover 5 2>/dev/null | tail -1)"

# STEP 2 — real execution is GATED. Never fire unless explicitly executing AND paper gate passed.
if [ "$DRY_RUN" = "false" ] && [ "$EARN_MODE" = "execute" ] && [ "${PM_PAPER_PASS:-0}" = "1" ]; then
  # real path deferred to a verified executor increment (polymarket-agent, RPC-fixed); fail closed for now.
  echo '{"slot":"earn/pm-trade","mode":"execute-blocked","note":"real executor not wired yet; paper-only build increment","paper_gate":1}'
  exit 0
fi

echo "{\"slot\":\"earn/pm-trade\",\"mode\":\"paper\",\"dry_run\":${DRY_RUN},\"discover\":${DISCOVER:-null}}"
