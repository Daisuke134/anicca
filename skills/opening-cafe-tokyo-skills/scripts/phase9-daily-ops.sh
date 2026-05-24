#!/usr/bin/env bash
# phase9-daily-ops.sh — daily Uber Eats sales/orders/reviews sync
# cron: `0 23 * * *` JST
#
# Calls lib/uber-eats-manager.sh, persists daily JSON + Supabase + Slack.
# Pre-live (in_review) → graceful no-op with single Slack heartbeat per week.
set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

TODAY=$(date +%Y-%m-%d)
SALES_DIR="$SKILL/data/cafe/sales"
mkdir -p "$SALES_DIR"
OUT="$SALES_DIR/$TODAY.json"

echo "▶ phase9: daily ops sync $TODAY"

RAW=$(bash "$SKILL/scripts/lib/uber-eats-manager.sh" all 2>/dev/null || echo '{"ok":false,"status_hint":"manager_error"}')
echo "$RAW" > "$OUT"

OK=$(echo "$RAW" | jq -r '.ok // false')
HINT=$(echo "$RAW" | jq -r '.status_hint // "unknown"')
REV=$(echo "$RAW" | jq -r '.revenue_jpy // 0')
NORD=$(echo "$RAW" | jq -r '.orders_count // 0')

# Pre-live: skip Supabase / Slack (heartbeat once per week on Mon)
if [ "$HINT" = "pre_live" ] || [ "$HINT" = "no_merchant_id" ]; then
  DOW=$(date +%u)
  if [ "$DOW" = "1" ] && command -v openclaw &>/dev/null; then
    openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
      --message "🟡 cafe daily-ops: still pre-live ($HINT) — heartbeat $TODAY" 2>/dev/null || true
  fi
  echo "✓ phase9 pre-live skip ($HINT)"
  exit 0
fi

# Live: persist to Supabase cafe_orders (best-effort)
if [ -n "${SUPABASE_URL:-}" ] && [ -n "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
  python3 - "$RAW" <<'PY' 2>/dev/null || true
import json, os, sys, urllib.request
data = json.loads(sys.argv[1])
url = os.environ["SUPABASE_URL"] + "/rest/v1/cafe_orders"
hdr = {
  "apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"],
  "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_ROLE_KEY']}",
  "Content-Type": "application/json",
  "Prefer": "resolution=merge-duplicates",
}
for o in data.get("orders", []):
    body = json.dumps({
      "order_id": o["order_id"],
      "amount_jpy": o["amount_jpy"],
      "status": o["status"],
      "captured_at": data.get("captured_at"),
      "date": data.get("date"),
    }).encode()
    req = urllib.request.Request(url, data=body, headers=hdr, method="POST")
    try:
        urllib.request.urlopen(req, timeout=10).read()
    except Exception:
        pass
PY
fi

# Update dashboard.json mrr.by_product.cafe (best-effort, push to landing)
DASHBOARD=~/anicca-products/apps/landing/public/dashboard.json
if [ -f "$DASHBOARD" ] && [ "$REV" -gt 0 ]; then
  python3 - "$DASHBOARD" "$REV" "$NORD" <<'PY' 2>/dev/null || true
import json, sys, pathlib
p = pathlib.Path(sys.argv[1])
d = json.loads(p.read_text())
mrr = d.setdefault("mrr", {}).setdefault("by_product", {})
cur = mrr.get("cafe", {"jpy_mtd": 0, "orders_mtd": 0})
cur["jpy_mtd"] = int(cur.get("jpy_mtd", 0)) + int(sys.argv[2])
cur["orders_mtd"] = int(cur.get("orders_mtd", 0)) + int(sys.argv[3])
mrr["cafe"] = cur
p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
PY
fi

# Slack #metrics
if command -v openclaw &>/dev/null; then
  REVIEWS_BAD=$(echo "$RAW" | jq '[.reviews[]? | select(.rating < 4)] | length')
  MSG="🍹 cafe $TODAY · ¥${REV} · ${NORD} orders · ${REVIEWS_BAD} bad reviews"
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --message "$MSG" 2>/dev/null || true
fi

echo "✅ phase9: revenue=¥$REV orders=$NORD hint=$HINT"
