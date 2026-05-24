#!/usr/bin/env bash
# lib/uber-status-check.sh — Uber Eats Merchant approval status check via camofox.
#
# Why: Uber account proceeds through "Account in review" → "approved live" within 1-3 days.
#      We need daily poll to detect transition and trigger Phase 5 menu publish auto.
#
# Pipeline:
#   1. camofox open /manager/home/<merchant_id>
#   2. snapshot で "Account in review" / "Live" / "Approved" / 売上 dashboard 検出
#   3. status → data/cafe/uber-status.json に永続
#   4. transition (review→live) 検知時 Slack alert + Phase 5 trigger
#
# Idempotent: 既 "live" なら skip。
#
# stdout final line:
#   ✅ uber-status: <current_status> (changed_from=<prev>)
#   ❌ uber-status FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
SIGNUP_FILE="$DATA_DIR/uber_signup.json"
STATUS_FILE="$DATA_DIR/uber-status.json"

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
  echo "❌ uber-status FAILED: merchant_store_id missing"
  exit 1
fi

# Previous status
PREV_STATUS=$("$PYTHON" -c "
import json, pathlib
p = pathlib.Path('$STATUS_FILE')
d = json.loads(p.read_text()) if p.exists() else {}
print(d.get('status', 'unknown'))
")

# Open dashboard — call cf_open in current shell so CF_TAB export propagates
cf_health >/dev/null || { echo "❌ uber-status FAILED: camofox not running"; exit 1; }
cf_open "https://merchants.ubereats.com/manager/home/$MERCHANT_ID" >/dev/null
if [ -z "$CF_TAB" ]; then
  echo "❌ uber-status FAILED: cf_open did not set CF_TAB"
  exit 1
fi
sleep 6

SNAP=$(cf_snapshot)
URL=$(cf_snapshot_url)

# Detect status from snapshot + URL (use tmpfile to avoid heredoc/quote conflict)
SNAP_FILE=$(mktemp -t uber-snap)
trap "rm -f $SNAP_FILE" EXIT
echo "$SNAP" > "$SNAP_FILE"

STATUS=$("$PYTHON" - "$URL" "$SNAP_FILE" <<'PY'
import sys, pathlib
url = sys.argv[1]
txt = pathlib.Path(sys.argv[2]).read_text()
if 'Account suspended' in txt:
    print('suspended')
elif '/ob-center' in url or 'store is under review' in txt.lower() or 'Account in review' in txt:
    print('in_review')
elif 'Total orders' in txt or ('¥' in txt and 'Sales' in txt):
    print('live_active')
elif 'No orders' in txt or 'Total sales' in txt:
    print('live_no_orders')
else:
    print('unknown')
PY
)

# Status transition detection
TRANSITIONED="no"
if [ "$PREV_STATUS" != "$STATUS" ] && [ "$PREV_STATUS" != "unknown" ]; then
  TRANSITIONED="yes"
fi

# Persist
"$PYTHON" - "$STATUS_FILE" "$STATUS" "$PREV_STATUS" "$TRANSITIONED" "$MERCHANT_ID" <<'PY'
import sys, json, datetime, pathlib
p = pathlib.Path(sys.argv[1])
db = json.loads(p.read_text()) if p.exists() else {"history": []}
db.update({
    "status":          sys.argv[2],
    "previous_status": sys.argv[3],
    "transitioned":    sys.argv[4] == "yes",
    "merchant_store_id": sys.argv[5],
    "checked_at":      datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
})
db.setdefault("history", []).append({
    "checked_at": db["checked_at"],
    "status": sys.argv[2],
})
db["history"] = db["history"][-90:]
p.write_text(json.dumps(db, ensure_ascii=False, indent=2))
PY

# Slack — only post on transition or new install
if [ "$TRANSITIONED" = "yes" ] || [ "$PREV_STATUS" = "unknown" ]; then
  "$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$STATUS" "$PREV_STATUS" "$TRANSITIONED" <<'PY'
import sys, json, urllib.request
ch, token, status, prev, transitioned = sys.argv[1:6]
emoji = {
    "in_review": "🟡",
    "live_no_orders": "🟢",
    "live_active": "💴",
    "suspended": "🔴",
    "unknown": "⚪",
}.get(status, "⚪")
title = f"{emoji} Uber Status: {status}"
if transitioned == "yes":
    title += f" (was: {prev})"
payload = {
    "channel": ch,
    "text": title,
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":title}},
        {"type":"section","text":{"type":"mrkdwn",
          "text":(f"*current:* `{status}`\n"
                  f"*previous:* `{prev}`\n"
                  f"*next action:* "
                  + ("Phase 5 menu publish auto-trigger" if status.startswith("live") else
                     "wait Uber 承認 (1-3 days from submit)" if status == "in_review" else
                     "investigate suspension / contact Uber rep" if status == "suspended" else
                     "manual investigation"))}},
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
fi

# Phase 5 auto-trigger on transition to live
if [ "$TRANSITIONED" = "yes" ] && [[ "$STATUS" =~ ^live ]]; then
  echo "▶ live transition detected — auto-triggering Phase 5 menu publish"
  bash "$SKILL/scripts/phase5-uber-menu-publish.sh" 2>&1 | tail -3 || echo "  ⚠️ phase5 trigger failed"
fi

echo "✅ uber-status: $STATUS (changed_from=$PREV_STATUS)"
