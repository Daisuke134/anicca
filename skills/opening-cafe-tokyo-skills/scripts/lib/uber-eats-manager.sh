#!/usr/bin/env bash
# lib/uber-eats-manager.sh — Uber Eats Manager scrape via camofox stealth.
#
# Why: post-launch daily ops needs sales / orders / reviews. Uber Manager has no
#      public API; only the merchant dashboard. agent-{{profile.lateness.stakeholders.channel}} is rejected by
#      Uber bot detection — camofox is required.
#
# Pipeline:
#   1. cf_open /manager/home/<merchant_id>
#   2. Scrape today's revenue + order count from snapshot (regex)
#   3. cf_navigate /manager/orders/<merchant_id>
#   4. List orders for last 24h (id / amount / status / created_at)
#   5. cf_navigate /manager/feedback/<merchant_id>
#   6. List new reviews (rating / comment / created_at) since last poll
#   7. Output aggregated JSON to stdout
#
# Idempotent: re-run safe; state diffs handled by caller (phase9-daily-ops.sh).
# Pre-live: gracefully exits with empty result + status_hint=pre_live.
#
# Actions:
#   sales            Fetch today's revenue + order count (1 page snapshot)
#   orders           Fetch last 24h orders array (id/amount/status)
#   reviews          Fetch new reviews since last poll
#   all              Run sales + orders + reviews, emit aggregated JSON
#   status           Print current state file
#
# stdout (JSON, single line):
#   {"date":"YYYY-MM-DD","revenue_jpy":N,"orders":[...],"reviews":[...],"status_hint":"...","ok":true}
#
# Required env: ~/.openclaw/.env with camofox running on :9377.

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
SIGNUP_FILE="$DATA_DIR/uber_signup.json"
STATE_FILE="$DATA_DIR/manager-state.json"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
ACTION="${1:-all}"

CAMOFOX_LIB="$SKILL/scripts/lib/camofox.sh"
export CF_USER="anicca"
export CF_SESSION="cafe-uber"

# shellcheck disable=SC1090
source "$CAMOFOX_LIB"

mid_or_die() {
  local mid
  mid=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$SIGNUP_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('merchant_store_id', '') or d.get('merchant_id', ''))
")
  if [ -z "$mid" ]; then
    "$PYTHON" -c "import json; print(json.dumps({'ok':False,'status_hint':'no_merchant_id'}))"
    exit 0
  fi
  echo "$mid"
}

# --- Subroutines -----------------------------------------------------------

scrape_sales() {
  local mid="$1"
  cf_open "https://merchants.ubereats.com/manager/home/$mid" >/dev/null
  if [ -z "$CF_TAB" ]; then
    "$PYTHON" -c "import json; print(json.dumps({'ok':False,'status_hint':'cf_open_failed'}))"
    return 1
  fi
  sleep 3
  local snap
  snap=$(cf_snapshot --limit 4000 2>/dev/null || echo '')

  # If page says "review" / "ob-center" → pre-live
  if echo "$snap" | grep -qi "ob-center\|under review\|store is under review"; then
    "$PYTHON" -c "import json; print(json.dumps({'ok':True,'status_hint':'pre_live','revenue_jpy':0,'orders_count':0}))"
    return 0
  fi

  # Extract ¥ values + order counts (best-effort regex)
  "$PYTHON" - "$snap" <<'PY'
import re, sys, json
snap = sys.argv[1]
# Revenue (¥+digits or "¥1,234")
yen = re.findall(r"¥\s?([\d,]+)", snap)
yen_vals = [int(v.replace(",", "")) for v in yen if v.replace(",", "").isdigit()]
revenue = max(yen_vals) if yen_vals else 0
# Orders
m = re.search(r"(\d+)\s+orders?", snap, re.I)
orders = int(m.group(1)) if m else 0
hint = "live_active" if revenue > 0 or orders > 0 else "live_no_orders"
print(json.dumps({"ok": True, "status_hint": hint, "revenue_jpy": revenue, "orders_count": orders}))
PY
  cf_close >/dev/null 2>&1 || true
}

scrape_orders() {
  local mid="$1"
  cf_open "https://merchants.ubereats.com/manager/orders/$mid" >/dev/null
  if [ -z "$CF_TAB" ]; then
    "$PYTHON" -c "import json; print(json.dumps([]))"
    return 1
  fi
  sleep 3
  local snap
  snap=$(cf_snapshot --limit 8000 2>/dev/null || echo '')
  "$PYTHON" - "$snap" <<'PY'
import re, sys, json
snap = sys.argv[1]
out = []
for m in re.finditer(r"#([A-Z0-9]{4,})\s+.*?¥\s?([\d,]+).*?(Delivered|Cancelled|Preparing|Ready)", snap, re.S):
    oid, amt, status = m.group(1), m.group(2).replace(",", ""), m.group(3)
    out.append({"order_id": oid, "amount_jpy": int(amt), "status": status})
print(json.dumps(out[:50]))
PY
  cf_close >/dev/null 2>&1 || true
}

scrape_reviews() {
  local mid="$1"
  cf_open "https://merchants.ubereats.com/manager/feedback/$mid" >/dev/null
  if [ -z "$CF_TAB" ]; then
    "$PYTHON" -c "import json; print(json.dumps([]))"
    return 1
  fi
  sleep 3
  local snap
  snap=$(cf_snapshot --limit 8000 2>/dev/null || echo '')
  "$PYTHON" - "$snap" <<'PY'
import re, sys, json
snap = sys.argv[1]
out = []
# Best-effort: lines with N stars + free text
for m in re.finditer(r"(\d)\s*(?:stars?|★).{0,400}", snap):
    rating = int(m.group(1))
    if 1 <= rating <= 5:
        out.append({"rating": rating, "raw_excerpt": m.group(0)[:200]})
print(json.dumps(out[:30]))
PY
  cf_close >/dev/null 2>&1 || true
}

# --- Action dispatch -------------------------------------------------------

case "$ACTION" in
  status)
    if [ -f "$STATE_FILE" ]; then cat "$STATE_FILE"; else echo '{}'; fi
    ;;
  sales)
    MID=$(mid_or_die); cf_health >/dev/null || { echo '{"ok":false,"status_hint":"camofox_down"}'; exit 0; }
    scrape_sales "$MID"
    ;;
  orders)
    MID=$(mid_or_die); cf_health >/dev/null || { echo '[]'; exit 0; }
    scrape_orders "$MID"
    ;;
  reviews)
    MID=$(mid_or_die); cf_health >/dev/null || { echo '[]'; exit 0; }
    scrape_reviews "$MID"
    ;;
  all|*)
    MID=$(mid_or_die)
    if ! cf_health >/dev/null 2>&1; then
      echo '{"ok":false,"status_hint":"camofox_down"}'
      exit 0
    fi
    SALES=$(scrape_sales "$MID")
    ORDERS=$(scrape_orders "$MID")
    REVIEWS=$(scrape_reviews "$MID")
    DATE=$(date +%Y-%m-%d)
    "$PYTHON" - "$DATE" "$SALES" "$ORDERS" "$REVIEWS" <<'PY' | tee "$STATE_FILE"
import json, sys, os
date, sales, orders, reviews = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
def safe(s, default):
    try:
        return json.loads(s)
    except Exception:
        return default
s = safe(sales, {"ok": False, "status_hint": "parse_error"})
o = safe(orders, [])
r = safe(reviews, [])
out = {
  "date": date,
  "ok": s.get("ok", False),
  "status_hint": s.get("status_hint", "unknown"),
  "revenue_jpy": s.get("revenue_jpy", 0),
  "orders_count": s.get("orders_count", len(o)),
  "orders": o,
  "reviews": r,
  "captured_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
}
print(json.dumps(out))
PY
    ;;
esac
