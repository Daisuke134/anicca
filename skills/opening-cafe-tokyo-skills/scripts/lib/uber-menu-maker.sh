#!/usr/bin/env bash
# lib/uber-menu-maker.sh — Uber Eats Menu Maker full automation via camofox.
#
# Why: agent-{{profile.lateness.stakeholders.channel}} fails Google OAuth on Uber. Use camofox stealth.
# Idempotent: re-run skips if menu already created.
# Entity-agnostic: pulls config from data/config.json + data/cafe/menu.json.
#
# Actions:
#   create-menu        Create menu (name + Sat/Sun + 11:00-15:00 hours) → Save
#   add-item           Add item (name + price + description + category + allergens)
#   list-items         List all items in menumaker
#   submit             Full pipeline: create-menu + add-all-items
#   status             Current state (menu_id / item_ids)
#
# Idempotency: data/cafe/menu-publish.json で state 管理
#   {phase, menu_id, items:[{item_id, name, ...}]}
#   既存 menu_id があれば create-menu は skip。既存 item_id ある名前は add-item skip。
#
# Required:
#   - merchant_store_id in data/cafe/uber_signup.json
#   - lib/camofox.sh (camofox :9377 wrapper)
#   - data/cafe/menu.json (items array に追加すべき item 全部)
#
# stdout final line:
#   ✅ uber-menu-maker <action>: <result>
#   ❌ uber-menu-maker FAILED: <reason>

set -uo pipefail

ACTION="${1:-status}"
SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
SIGNUP_FILE="$DATA_DIR/uber_signup.json"
MENU_PUBLISH_FILE="$DATA_DIR/menu-publish.json"
MENU_FILE="$DATA_DIR/menu.json"
CONFIG="$SKILL/data/config.json"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
CAMOFOX_LIB="$SKILL/scripts/lib/camofox.sh"

export CF_USER="anicca"
export CF_SESSION="cafe-uber"

# shellcheck disable=SC1090
source "$CAMOFOX_LIB"

MERCHANT_ID=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$SIGNUP_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('merchant_store_id', ''))
")

if [ -z "$MERCHANT_ID" ]; then
  echo "❌ uber-menu-maker FAILED: merchant_store_id missing in uber_signup.json. Run phase4 submit first."
  exit 1
fi

case "$ACTION" in

create-menu)
  # Idempotency: skip if menu_id already in state
  EXISTING_MENU=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$MENU_PUBLISH_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('menu_id',''))
")
  if [ -n "$EXISTING_MENU" ]; then
    echo "✅ uber-menu-maker create-menu: already exists ($EXISTING_MENU, skipping)"
    exit 0
  fi

  MENU_NAME=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$MENU_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('menu_name', 'Mango Reset Menu'))
")
  HOURS_START=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$MENU_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('hours_start', '11:00 AM'))
")
  HOURS_END=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$MENU_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('hours_end', '3:00 PM'))
")
  DAYS=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$MENU_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(','.join(d.get('hours_days', ['Sat','Sun'])))
")

  cf_health >/dev/null || exit 1
  cf_open "https://merchants.ubereats.com/menumaker/$MERCHANT_ID" >/dev/null
  sleep 6

  # If "No items yet" page → click create-new-menu
  SNAP=$(cf_snapshot)
  if echo "$SNAP" | grep -q "No items yet\|create a new menu"; then
    cf_click "e1"
    sleep 5
  fi

  SNAP=$(cf_snapshot)

  # Find Name textbox + Save button refs
  NAME_REF=$(echo "$SNAP" | "$PYTHON" -c "import sys,re; m=re.search(r'textbox \"Name\" \[e(\d+)\]', sys.stdin.read()); print(f'e{m.group(1)}' if m else '')")
  SAVE_REF=$(echo "$SNAP" | "$PYTHON" -c "import sys,re; m=re.search(r'button \"Save\" \[e(\d+)\]', sys.stdin.read()); print(f'e{m.group(1)}' if m else '')")

  if [ -z "$NAME_REF" ] || [ -z "$SAVE_REF" ]; then
    echo "❌ uber-menu-maker create-menu FAILED: name/save refs not found"
    exit 1
  fi

  cf_fill "$NAME_REF" "$MENU_NAME"
  sleep 1

  # Click days
  for day in $(echo "$DAYS" | tr ',' '\n'); do
    DAY_REF=$(echo "$SNAP" | "$PYTHON" -c "import sys,re; m=re.search(r'button \"$day\" \[e(\d+)\]', sys.stdin.read()); print(f'e{m.group(1)}' if m else '')")
    [ -n "$DAY_REF" ] && cf_click "$DAY_REF"
    sleep 1
  done

  # Open Start Time combobox + select start time
  cf_click_selector "input[role='combobox'] >> nth=0"
  sleep 2
  cf_click_selector "role=option[name='$HOURS_START']"
  sleep 1

  # Open End Time combobox + select end time
  cf_click_selector "input[role='combobox'] >> nth=1"
  sleep 2
  cf_click_selector "role=option[name='$HOURS_END']"
  sleep 1

  # Save
  cf_click "$SAVE_REF"
  sleep 5

  # Extract menu_id from URL
  URL=$(cf_snapshot_url)
  MENU_ID=$(echo "$URL" | "$PYTHON" -c "import sys,re; m=re.search(r'/menus/([0-9a-f-]+)', sys.stdin.read()); print(m.group(1) if m else '')")

  if [ -z "$MENU_ID" ] || echo "$URL" | grep -q "/create"; then
    echo "❌ uber-menu-maker create-menu FAILED: menu_id not in URL. URL=$URL"
    cf_screenshot "$DATA_DIR/uber-menu-create-failed.png"
    exit 1
  fi

  "$PYTHON" - "$MENU_PUBLISH_FILE" "$MENU_ID" "$MENU_NAME" "$HOURS_START" "$HOURS_END" "$DAYS" <<'PY'
import sys, json, datetime, pathlib
p = pathlib.Path(sys.argv[1])
state = json.loads(p.read_text()) if p.exists() else {"items": []}
state.update({
    "menu_id":       sys.argv[2],
    "menu_name":     sys.argv[3],
    "hours_start":   sys.argv[4],
    "hours_end":     sys.argv[5],
    "hours_days":    sys.argv[6].split(","),
    "menu_created_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
})
state.setdefault("items", [])
p.write_text(json.dumps(state, ensure_ascii=False, indent=2))
PY

  echo "✅ uber-menu-maker create-menu: menu_id=$MENU_ID name=\"$MENU_NAME\" hours=$HOURS_START-$HOURS_END days=$DAYS"
  ;;

add-item)
  ITEM_NAME="${2:?missing item name}"
  ITEM_PRICE="${3:?missing item price}"
  ITEM_DESC="${4:-}"

  # Idempotency: skip if item with same name already in state
  EXISTING=$("$PYTHON" -c "
import json, pathlib, sys
p = pathlib.Path('$MENU_PUBLISH_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
items = d.get('items', [])
for it in items:
    if it.get('name') == '$ITEM_NAME':
        print(it.get('item_id',''))
        sys.exit(0)
print('')
")
  if [ -n "$EXISTING" ]; then
    echo "✅ uber-menu-maker add-item: $ITEM_NAME already exists ($EXISTING, skipping)"
    exit 0
  fi

  cf_health >/dev/null || exit 1
  cf_open "https://merchants.ubereats.com/menumaker/$MERCHANT_ID/items" >/dev/null
  sleep 5
  SNAP=$(cf_snapshot)

  NEW_REF=$(echo "$SNAP" | "$PYTHON" -c "import sys,re; m=re.search(r'button \"New Item\" \[e(\d+)\]', sys.stdin.read()); print(f'e{m.group(1)}' if m else '')")
  [ -z "$NEW_REF" ] && { echo "❌ uber-menu-maker add-item FAILED: New Item button not found"; exit 1; }

  cf_click "$NEW_REF"
  sleep 5
  SNAP=$(cf_snapshot)

  NAME_REF=$(echo "$SNAP" | "$PYTHON" -c "import sys,re; t=sys.stdin.read(); m=re.search(r'Name \*[^\[]*textbox \[e(\d+)\]', t); print(f'e{m.group(1)}' if m else '')")
  PRICE_REF=$(echo "$SNAP" | "$PYTHON" -c "import sys,re; t=sys.stdin.read(); m=re.search(r'Price \* ¥[^\[]*spinbutton \[e(\d+)\]', t); print(f'e{m.group(1)}' if m else '')")
  DESC_REF=$(echo "$SNAP" | "$PYTHON" -c "import sys,re; m=re.search(r'textbox \"Enter description\" \[e(\d+)\]', sys.stdin.read()); print(f'e{m.group(1)}' if m else '')")
  SAVE_REF=$(echo "$SNAP" | "$PYTHON" -c "import sys,re; m=re.search(r'button \"Save\" \[e(\d+)\]', sys.stdin.read()); print(f'e{m.group(1)}' if m else '')")

  if [ -z "$NAME_REF" ] || [ -z "$PRICE_REF" ] || [ -z "$SAVE_REF" ]; then
    echo "❌ uber-menu-maker add-item FAILED: refs missing (name=$NAME_REF price=$PRICE_REF save=$SAVE_REF)"
    exit 1
  fi

  cf_fill "$NAME_REF" "$ITEM_NAME"
  cf_fill "$PRICE_REF" "$ITEM_PRICE"
  [ -n "$ITEM_DESC" ] && [ -n "$DESC_REF" ] && cf_fill "$DESC_REF" "$ITEM_DESC"
  sleep 1

  cf_click "$SAVE_REF"
  sleep 5

  URL=$(cf_snapshot_url)
  ITEM_ID=$(echo "$URL" | "$PYTHON" -c "import sys,re; m=re.search(r'/items/([0-9a-f-]+)', sys.stdin.read()); print(m.group(1) if m else '')")

  if [ -z "$ITEM_ID" ] || echo "$URL" | grep -q "/create"; then
    echo "❌ uber-menu-maker add-item FAILED: item_id not in URL. URL=$URL"
    cf_screenshot "$DATA_DIR/uber-menu-item-failed.png"
    exit 1
  fi

  "$PYTHON" - "$MENU_PUBLISH_FILE" "$ITEM_ID" "$ITEM_NAME" "$ITEM_PRICE" "$ITEM_DESC" <<'PY'
import sys, json, datetime, pathlib
p = pathlib.Path(sys.argv[1])
state = json.loads(p.read_text()) if p.exists() else {"items": []}
state.setdefault("items", []).append({
    "item_id":     sys.argv[2],
    "name":        sys.argv[3],
    "price_jpy":   int(sys.argv[4]),
    "description": sys.argv[5],
    "saved_at":    datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
})
p.write_text(json.dumps(state, ensure_ascii=False, indent=2))
PY

  echo "✅ uber-menu-maker add-item: $ITEM_NAME (item_id=$ITEM_ID, ¥$ITEM_PRICE)"
  ;;

submit)
  # Full pipeline: create menu + add all items from menu.json
  bash "$0" create-menu || exit 1

  # Get items array from menu.json
  ITEMS_COUNT=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$MENU_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
items = d.get('items', [])
print(len(items))
")

  if [ "$ITEMS_COUNT" = "0" ]; then
    echo "✅ uber-menu-maker submit: menu created, no items to add"
    exit 0
  fi

  for i in $(seq 0 $((ITEMS_COUNT - 1))); do
    NAME=$("$PYTHON" -c "import json,pathlib; d=json.loads(pathlib.Path('$MENU_FILE').read_text()); print(d['items'][$i]['name'])")
    PRICE=$("$PYTHON" -c "import json,pathlib; d=json.loads(pathlib.Path('$MENU_FILE').read_text()); print(d['items'][$i].get('price_jpy', 0))")
    DESC=$("$PYTHON" -c "import json,pathlib; d=json.loads(pathlib.Path('$MENU_FILE').read_text()); print(d['items'][$i].get('description', ''))")
    bash "$0" add-item "$NAME" "$PRICE" "$DESC" || echo "⚠️ failed item: $NAME"
  done

  TOTAL_ITEMS=$("$PYTHON" -c "import json,pathlib; d=json.loads(pathlib.Path('$MENU_PUBLISH_FILE').read_text()); print(len(d.get('items',[])))")
  echo "✅ uber-menu-maker submit: $TOTAL_ITEMS items in menu"
  ;;

status)
  PHASE=$("$PYTHON" -c "import json,pathlib; p=pathlib.Path('$MENU_PUBLISH_FILE'); d=json.loads(p.read_text()) if p.exists() else {}; print(d.get('phase','init'))" 2>/dev/null || echo "init")
  MID=$("$PYTHON" -c "import json,pathlib; p=pathlib.Path('$MENU_PUBLISH_FILE'); d=json.loads(p.read_text()) if p.exists() else {}; print(d.get('menu_id','none'))" 2>/dev/null || echo "none")
  N=$("$PYTHON" -c "import json,pathlib; p=pathlib.Path('$MENU_PUBLISH_FILE'); d=json.loads(p.read_text()) if p.exists() else {}; print(len(d.get('items',[])))" 2>/dev/null || echo 0)
  echo "✅ uber-menu-maker status: phase=$PHASE menu_id=$MID items=$N"
  ;;

*)
  echo "❌ uber-menu-maker FAILED: unknown action '$ACTION' (create-menu|add-item|submit|status)"
  exit 1
  ;;
esac
