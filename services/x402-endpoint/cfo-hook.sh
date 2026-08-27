#!/bin/bash
# Spec 09 § 2 T9 — cfo-hook.
# Invoked by monitor.sh on every paying 200 (REVENUE line in /tmp/anicca-x402.log).
# Appends a structured event to the CFO event log AND updates a running summary
# JSON so cfo-core's bridge-to-dashboard pass can bump dashboard.lineage[*].x402_revenue
# without re-reading the entire revenue ledger.
#
# Arguments:
#   $1  the raw REVENUE line as emitted by server.ts, e.g.
#       REVENUE route=echo value_usdc=0.001 tx=0x... from=0x... block=... at=...
#
# Side effects (all atomic — mv from .tmp.<pid>):
#   ~/.openclaw/state/cfo_x402_events.jsonl
#       append-only structured event log for CFO consumers
#   ~/.openclaw/state/x402_revenue_summary.json
#       running totals shape:
#         {
#           "wallet": "0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21",
#           "x402_revenue_usdc_total": 0.011,
#           "x402_revenue_count": 2,
#           "x402_revenue_by_route": {"echo": 0.001, "learn": 0.01},
#           "last_event_at":  "2026-06-03T15:30:00Z",
#           "last_tx_hash":   "0x...",
#           "schema": "anicca-x402/cfo-hook/v1"
#         }
#
# Compatible with macOS /bin/bash 3.2.

set -u

LINE="${1:-}"
if [ -z "${LINE}" ]; then
  echo "[cfo-hook] usage: cfo-hook.sh '<REVENUE line>'" >&2
  exit 1
fi

WALLET="0xa3CDd4Ec6b94F01826Aaf90a6d5538A2Aa8C4C21"
EVENTS="${HOME}/.openclaw/state/cfo_x402_events.jsonl"
SUMMARY="${HOME}/.openclaw/state/x402_revenue_summary.json"

mkdir -p "${HOME}/.openclaw/state"
: >>"${EVENTS}"
[ -s "${SUMMARY}" ] || cat >"${SUMMARY}" <<JSON
{"schema":"anicca-x402/cfo-hook/v1","wallet":"${WALLET}","x402_revenue_usdc_total":0,"x402_revenue_count":0,"x402_revenue_by_route":{},"last_event_at":null,"last_tx_hash":null}
JSON

now="$(date -u +%FT%TZ)"

# Parse the REVENUE line via python (robust against quoting / extra tokens).
event_json=$(
  EVENT_LINE="${LINE}" CFO_NOW="${now}" python3 - <<'PY'
import json, os, re, sys
line = os.environ["EVENT_LINE"]
# REVENUE route=echo value_usdc=0.001 tx=0x... from=0x... block=NNN at=ISO ...
def grab(key, pattern=r'([^\s]+)'):
    m = re.search(rf'\b{key}=({pattern})', line)
    return m.group(1) if m else None
parsed = {
    "ts":       os.environ["CFO_NOW"],
    "route":    grab("route", r'[a-z]+'),
    "value_usdc": float(grab("value_usdc") or 0),
    "tx":       grab("tx"),
    "from":     grab("from"),
    "block":    grab("block"),
    "at":       grab("at"),
    "schema":   "anicca-x402/cfo-event/v1",
}
print(json.dumps(parsed))
PY
)
if [ -z "${event_json}" ] || ! printf '%s' "${event_json}" | python3 -c "import json,sys; json.loads(sys.stdin.read())" >/dev/null 2>&1; then
  echo "[cfo-hook] failed to parse REVENUE line: ${LINE}" >&2
  exit 2
fi

# Append the structured event.
printf '%s\n' "${event_json}" >>"${EVENTS}"

# Recompute the rolling summary atomically.
EVENT="${event_json}" SUMMARY_PATH="${SUMMARY}" WALLET_ADDR="${WALLET}" python3 - <<'PY'
import json, os, sys, tempfile, shutil
path = os.environ["SUMMARY_PATH"]
try:
    with open(path) as f:
        cur = json.load(f)
except Exception:
    cur = {"schema":"anicca-x402/cfo-hook/v1","wallet":os.environ["WALLET_ADDR"],
           "x402_revenue_usdc_total":0,"x402_revenue_count":0,"x402_revenue_by_route":{},
           "last_event_at":None,"last_tx_hash":None}

ev = json.loads(os.environ["EVENT"])
amt = float(ev.get("value_usdc") or 0)
route = ev.get("route") or "unknown"

cur["x402_revenue_usdc_total"] = round(cur.get("x402_revenue_usdc_total", 0) + amt, 6)
cur["x402_revenue_count"]      = cur.get("x402_revenue_count", 0) + 1
by = cur.get("x402_revenue_by_route", {}) or {}
by[route] = round(by.get(route, 0) + amt, 6)
cur["x402_revenue_by_route"] = by
cur["last_event_at"] = ev.get("at") or ev.get("ts")
cur["last_tx_hash"]  = ev.get("tx")

tmp = path + ".tmp." + str(os.getpid())
with open(tmp, "w") as f:
    json.dump(cur, f, indent=2)
os.replace(tmp, path)
print(json.dumps({"ok": True, "total": cur["x402_revenue_usdc_total"],
                  "count": cur["x402_revenue_count"],
                  "last_route": route, "last_amt": amt}))
PY

exit 0
