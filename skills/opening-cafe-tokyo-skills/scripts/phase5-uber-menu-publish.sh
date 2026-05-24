#!/usr/bin/env bash
# phase5-uber-menu-publish.sh — Phase 5: Uber Eats menu publish (skill-ified 5/8 v3)
#
# Pipeline:
#   1. lib/uber-menu-maker.sh submit
#      → create-menu (Mango Reset Menu, Sat/Sun 11-15 by default)
#      → add-item × N from data/cafe/menu.json items array
#      → state save in data/cafe/menu-publish.json
#   2. Slack #metrics 報告
#
# Idempotent: lib/uber-menu-maker.sh が既存 menu_id / item 重複検知 → skip
# Entity-agnostic: data/cafe/menu.json から items 全部 pull
#
# Prerequisites:
#   - merchant_store_id (data/cafe/uber_signup.json) — Phase 4 完了
#   - data/cafe/menu.json (items array, hours_start/end/days)
#   - camofox running :9377
#
# stdout final line:
#   ✅ phase5-uber-menu-publish: <menu_id> <N items>
#   ❌ phase5-uber-menu-publish FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
MENU_FILE="$DATA_DIR/menu.json"
PUBLISH_FILE="$DATA_DIR/menu-publish.json"
CONFIG="$SKILL/data/config.json"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"

# Generate menu.json from config.product if missing
if [ ! -f "$MENU_FILE" ] || ! "$PYTHON" -c "import json,pathlib; d=json.loads(pathlib.Path('$MENU_FILE').read_text()); assert d.get('items')" 2>/dev/null; then
  echo "▶ generating menu.json from config.product"
  "$PYTHON" - "$CONFIG" "$MENU_FILE" <<'PY'
import sys, json, pathlib
config = json.loads(pathlib.Path(sys.argv[1]).read_text()) if pathlib.Path(sys.argv[1]).exists() else {}
prod = config.get("product", {})
menu = {
    "menu_name":   "Mango Reset Menu",
    "hours_start": "11:00 AM",
    "hours_end":   "3:00 PM",
    "hours_days":  ["Sat", "Sun"],
    "items": [{
        "name":        prod.get("name", "Mango Reset"),
        "price_jpy":   prod.get("price_jpy", 1500),
        "description": prod.get("description", "Cold-pressed Mexican mango. 350ml. One drink. One fruit. One reset."),
        "category":    prod.get("category", "Juice"),
        "allergens":   prod.get("allergens", ["mango"]),
    }],
}
pathlib.Path(sys.argv[2]).write_text(json.dumps(menu, ensure_ascii=False, indent=2))
print("menu.json generated")
PY
fi

# Submit (idempotent — skips already-created menu/items)
RESULT=$(bash "$SKILL/scripts/lib/uber-menu-maker.sh" submit 2>&1) || {
  echo "❌ phase5-uber-menu-publish FAILED: $(echo "$RESULT" | tail -1)"
  exit 1
}
RESULT_LINE=$(echo "$RESULT" | tail -1)

# Slack
MENU_ID=$("$PYTHON" -c "import json,pathlib; p=pathlib.Path('$PUBLISH_FILE'); d=json.loads(p.read_text()) if p.exists() else {}; print(d.get('menu_id','none'))")
ITEMS_N=$("$PYTHON" -c "import json,pathlib; p=pathlib.Path('$PUBLISH_FILE'); d=json.loads(p.read_text()) if p.exists() else {}; print(len(d.get('items',[])))")
PUBLIC_URL=$("$PYTHON" -c "import json,pathlib; p=pathlib.Path('$PUBLISH_FILE'); d=json.loads(p.read_text()) if p.exists() else {}; print(d.get('public_url',''))")

"$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$MENU_ID" "$ITEMS_N" "$PUBLIC_URL" "$RESULT_LINE" <<'PY'
import sys, json, urllib.request
ch, token, menu_id, n, public_url, result_line = sys.argv[1:7]
payload = {
    "channel": ch,
    "text": f"🥭 phase5 menu publish: menu_id={menu_id} items={n}",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"🥭 Phase 5 — Mango Reset Menu Published"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*menu_id:*\n`{menu_id}`"},
            {"type":"mrkdwn","text":f"*items:*\n{n}"},
        ]},
        {"type":"section","text":{"type":"mrkdwn",
          "text": f"*Public Uber Eats URL:* {public_url}\n*result:* `{result_line}`"}},
    ]
}
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception:
    print("?")
PY

echo "✅ phase5-uber-menu-publish: menu_id=$MENU_ID items=$ITEMS_N"
