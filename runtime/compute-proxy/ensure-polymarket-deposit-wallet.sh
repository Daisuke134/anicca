#!/usr/bin/env bash
# ensure-polymarket-deposit-wallet.sh — born-with-Polygon (#27 EQUALIZE next step).
#
# Given this instance's own EVM wallet.json (from start-local.sh step 1), deploy its
# Polymarket CLOB V2 deposit wallet — GASLESS (Polymarket's relayer pays; the EOA only
# SIGNS a SIWE message, no funds needed or moved). This is best-effort and NON-BLOCKING:
# any missing python/pip/network/deps WARNS to stderr and returns 0 so callers (namely
# start-local.sh) never fail wallet creation because of this step.
#
# Usage: ensure-polymarket-deposit-wallet.sh <wallet.json path> <ANICCA_HOME>
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WALLET="${1:-}"
HOME_DIR="${2:-$HOME/.anicca}"

if [ -z "$WALLET" ] || [ ! -f "$WALLET" ]; then
  echo "[local] Polymarket: no EVM wallet.json yet, skipping deposit-wallet bootstrap" >&2
  exit 0
fi

PRIVATE_KEY="$(WALLET_PATH="$WALLET" node -e '
  try {
    const w = JSON.parse(require("fs").readFileSync(process.env.WALLET_PATH, "utf8"));
    if (w.privateKey) process.stdout.write(w.privateKey);
  } catch (e) { /* non-fatal */ }
')"
if [ -z "$PRIVATE_KEY" ]; then
  echo "[local] Polymarket: could not read private key from wallet.json, skipping (non-blocking)" >&2
  exit 0
fi

# Reuse any venv on this machine that already has the deps (e.g. claude-p's own
# polymarket-agent venv) before spending time/disk creating a new one.
VENV_PY=""
for CANDIDATE in \
  "$HOME_DIR/.automaton/.pm-venv/bin/python3" \
  "$HOME/.anicca-founder/agents/polymarket-agent/.venv/bin/python3"
do
  if [ -x "$CANDIDATE" ] && "$CANDIDATE" -c "import polymarket, eth_account, web3" >/dev/null 2>&1; then
    VENV_PY="$CANDIDATE"
    break
  fi
done

if [ -z "$VENV_PY" ]; then
  echo "[local] Polymarket: setting up a small venv for the deposit-wallet bootstrap (one-time, best-effort)..." >&2
  VENV_DIR="$HOME_DIR/.automaton/.pm-venv"
  if command -v python3 >/dev/null 2>&1 \
     && python3 -m venv "$VENV_DIR" >/dev/null 2>&1 \
     && "$VENV_DIR/bin/pip" install --quiet --disable-pip-version-check polymarket-client eth-account web3 requests >/dev/null 2>&1; then
    VENV_PY="$VENV_DIR/bin/python3"
  else
    echo "[local] WARN: Polymarket deposit-wallet venv setup failed (offline / pip error?) — skipping, non-blocking" >&2
    exit 0
  fi
fi

RESULT_JSON="$(POLYGON_WALLET_PRIVATE_KEY="$PRIVATE_KEY" "$VENV_PY" "$HERE/ensure-polymarket-deposit-wallet.py" || true)"
if [ -z "$RESULT_JSON" ]; then
  echo "[local] WARN: Polymarket deposit-wallet bootstrap produced no result (non-blocking)" >&2
  exit 0
fi

DEPOSIT_ADDR="$(node -e '
  try { console.log(JSON.parse(process.argv[1]).deposit_wallet || ""); } catch (e) { console.log(""); }
' "$RESULT_JSON")"

if [ -n "$DEPOSIT_ADDR" ]; then
  echo "[local] Polymarket deposit wallet ready: $DEPOSIT_ADDR — fund with pUSD/USDC to trade (see skills/earn/polymarket-trade/SKILL.md)" >&2
else
  echo "[local] WARN: Polymarket deposit-wallet bootstrap returned no address (non-blocking)" >&2
fi
exit 0
