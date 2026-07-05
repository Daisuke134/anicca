#!/bin/bash
# pm-trade run.sh — THIN HARNESS. THIS FILE DECIDES NOTHING. (spec §0.25)
# The base agent (BlockRunAI/polymarket-agent) does its OWN analysis / sizing /
# execution with its OWN wallet. This wrapper only: kill-switch gate → one real
# live pass (NO dry-run, HARD 0.24) → append a structured trace line (H1).
set -u
SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"
STATE_DIR="$SKILL_DIR/../state"; mkdir -p "$STATE_DIR"
TRACE="$STATE_DIR/pm-trade.trace.jsonl"
AGENT_HOME="${PM_TRADE_AGENT_HOME:-$HOME/.anicca-founder/agents/polymarket-agent}"

now() { date -u +%Y-%m-%dT%H:%M:%SZ; }

# money-safety guard #1: kill-switch (touch KILL next to this script to stop)
if [ -f "$SKILL_DIR/KILL" ]; then
  echo "{\"ts\":\"$(now)\",\"slot\":\"earn/pm-trade\",\"action\":\"skip\",\"reason\":\"kill-switch\"}" >> "$TRACE"
  exit 0
fi

if [ ! -d "$AGENT_HOME" ]; then
  echo "{\"ts\":\"$(now)\",\"slot\":\"earn/pm-trade\",\"action\":\"error\",\"error\":\"agent home missing: $AGENT_HOME\"}" >> "$TRACE"
  echo "agent home missing: $AGENT_HOME" >&2
  exit 1
fi

# --- per-instance identity resolution (#26 EQUALIZE, R3) -----------------------------
# claude-p 温存 (R6, zero regression): if POLYGON_WALLET_PRIVATE_KEY is ALREADY resolvable
# the way it is today — either exported in this shell's env, or present in the agent's own
# .env (python's load_dotenv() reads it there; we check existence only, never the value) —
# we export NOTHING and change NOTHING: the agent resolves its key exactly as before.
# Only when NEITHER exists (a genuinely unconfigured / fresh instance) do we reach for
# resolve-identity to give THIS instance its own key (env override / $ANICCA_HOME wallet /
# legacy $HOME wallet) and export it. If that also comes up empty, fail closed: skip + warn
# (R5, money-safety) instead of letting the agent crash mid-run.
if [ -z "${POLYGON_WALLET_PRIVATE_KEY:-}" ] && ! grep -q '^POLYGON_WALLET_PRIVATE_KEY=.\+' "$AGENT_HOME/.env" 2>/dev/null; then
  RESOLVE_IDENTITY="$SKILL_DIR/../lib/resolve-identity.mjs"
  RESOLVED_EVM_KEY=""
  [ -f "$RESOLVE_IDENTITY" ] && RESOLVED_EVM_KEY="$(node "$RESOLVE_IDENTITY" evm 2>/dev/null || true)"
  if [ -n "$RESOLVED_EVM_KEY" ]; then
    export POLYGON_WALLET_PRIVATE_KEY="$RESOLVED_EVM_KEY"
  else
    echo "{\"ts\":\"$(now)\",\"slot\":\"earn/pm-trade\",\"action\":\"skip\",\"reason\":\"no-identity-key\"}" >> "$TRACE"
    echo "no EVM identity key resolvable (env / agent .env / \$ANICCA_HOME / \$HOME) — skipping pm-trade pass" >&2
    exit 0
  fi
  unset RESOLVED_EVM_KEY
fi

# #27: ensure THIS instance's deposit wallet is REGISTERED via the bridge Collateral Onramp (idempotent)
# + approve the neg-risk spenders, so EVERY self-funded AI can trade on Polymarket from birth. Registry
# gate is the CONFIRMED root cause of "error resolving address" — never raw-deploy + raw-transfer pUSD;
# always fund THROUGH the bridge (see SKILL.md "DEPOSIT-WALLET REGISTRY GATE" + fund_via_bridge.py).
# Best-effort / non-blocking: an already-registered wallet just re-approves; an unfunded one no-ops.
if [ -f "$SKILL_DIR/fund_via_bridge.py" ] && [ -x "$AGENT_HOME/.venv/bin/python" ]; then
  "$AGENT_HOME/.venv/bin/python" "$SKILL_DIR/fund_via_bridge.py" >> "$TRACE" 2>&1 \
    || echo "{\"ts\":\"$(now)\",\"slot\":\"earn/pm-trade\",\"action\":\"register-skip\"}" >> "$TRACE"
fi

# money-safety guard #2: per-trade cap lives in the agent's own config
# (.env MAX_BET_PERCENTAGE × INITIAL_BANKROLL, plus executor MAX_BET_SIZE).
cd "$AGENT_HOME"
OUT=$(printf 'yes\n' | timeout 900 .venv/bin/python main.py --live 2>&1); RC=$?
echo "$OUT" | tail -40

TRADES=$(echo "$OUT" | sed -n 's/.*Trades executed: \([0-9][0-9]*\).*/\1/p' | tail -1)
TAIL_ERR=""
[ "$RC" -ne 0 ] && TAIL_ERR=$(echo "$OUT" | tail -3 | tr '\n' ' ')

TRACE_FILE="$TRACE" RC="$RC" TRADES="${TRADES:-}" ERR="$TAIL_ERR" python3 - <<'PY'
import json, os, datetime
rec = {
    "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "slot": "earn/pm-trade",
    "action": "live-pass",
    "exit": int(os.environ["RC"]),
    "trades": int(os.environ["TRADES"]) if os.environ["TRADES"] else None,
    "error": os.environ["ERR"] or None,
}
with open(os.environ["TRACE_FILE"], "a") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
PY
exit "$RC"
