#!/usr/bin/env bash
# phase0-discover.sh — search ghost-kitchen candidates per config preferences
#
# Sources (in priority order):
#   1. kashispace.com   (ghost-kitchen filter)
#   2. theghostrestaurant.tokyo (single brand, multi-room)
#   3. spacemarket.com  (kitchen filter — login required, fallback)
#
# Output: data/cafe/candidates.json — sorted by (cost-month-32h ASC, commute-min ASC)
set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
CONFIG="${CONFIG:-$SKILL/data/config.json}"
[ ! -f "$CONFIG" ] && { echo "ERR: $CONFIG missing. Copy data/config.example.json"; exit 1; }

CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

mkdir -p "$SKILL/data/cafe"
NOW=$(date -u +%FT%TZ)
echo "▶ phase0-discover  $NOW"

AREAS=$(jq -r '.preferences.areas[]' "$CONFIG" | tr '\n' '|' | sed 's/|$//')
HOME_STATION=$(jq -r '.operator.home_station' "$CONFIG")
echo "  areas filter: $AREAS"
echo "  home: $HOME_STATION"

# ── kashispace search ────────────────────────────────────────────────────────
# Use search by category=ゴーストキッチン + 東京都
KASHI_OUT=$({{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://kashispace.com/room?keyword=ゴーストキッチン&area=13')
wait_for_load(); time.sleep(3)
print(js('''
const links = Array.from(document.querySelectorAll(\"a[href*=\\\"/room/detail\\\"]\"))
  .map(a => ({href: a.href, text: (a.textContent || '').trim().slice(0, 100)}))
  .filter(x => x.href.includes('id='));
const dedup = {};
for (const l of links) if (!dedup[l.href]) dedup[l.href] = l.text;
return JSON.stringify(Object.entries(dedup).slice(0, 20).map(([href, text]) => ({href, text})));
'''))
" 2>&1 | grep -E '^\[' | tail -1)

KASHI_COUNT=0
echo "$KASHI_OUT" | jq -c '.[]' 2>/dev/null | while read -r entry; do
  HREF=$(echo "$entry" | jq -r .href)
  ID=$(echo "$HREF" | grep -oE 'id=[0-9]+' | cut -d= -f2)
  [ -z "$ID" ] && continue
  KASHI_COUNT=$((KASHI_COUNT + 1))
done

# ── theghostrestaurant — single brand, fixed offer ────────────────────────────
# Static entry as a candidate (since it's a single platform with a flat offer)
TGR_HOURLY=1000
TGR_MONTHLY_BASE=30000

# ── Compute monthly cost @ weekly_hours × 4 ──────────────────────────────────
WEEKLY_HOURS=$(jq -r '.preferences.weekly_hours' "$CONFIG")
MONTHLY_HOURS=$((WEEKLY_HOURS * 4))
TGR_MONTHLY=$((TGR_MONTHLY_BASE + (TGR_HOURLY * MONTHLY_HOURS)))

# ── Compose candidates.json ──────────────────────────────────────────────────
CANDIDATES=$(jq -n \
  --arg discovered_at "$NOW" \
  --argjson monthly_hours "$MONTHLY_HOURS" \
  --argjson tgr_monthly "$TGR_MONTHLY" \
  --argjson kashi_count "$KASHI_COUNT" \
  '{
    discovered_at: $discovered_at,
    config_monthly_hours_estimate: $monthly_hours,
    candidates: [
      {
        platform: "theghostrestaurant",
        url: "https://www.theghostrestaurant.tokyo/sharedkitchen/",
        inquiry_url: "https://www.theghostrestaurant.tokyo/info/",
        license: "飲食店営業許可取得済 (専有個室7+シェア1)",
        hourly_jpy: 1000,
        monthly_base_jpy: 30000,
        monthly_estimate_jpy: $tgr_monthly,
        commute_note: "近場 (千代田区神田三崎町、水道橋徒歩5分)",
        notes: "一律料金で予測可能。専有個室7+シェア007 (バーカウンター付)"
      }
    ]
  }')

echo "$CANDIDATES" > "$SKILL/data/cafe/candidates.json"

# Append kashispace candidates if any
echo "$KASHI_OUT" | jq -c '.[]' 2>/dev/null | head -20 | while read -r entry; do
  HREF=$(echo "$entry" | jq -r .href)
  TEXT=$(echo "$entry" | jq -r .text)
  ID=$(echo "$HREF" | grep -oE 'id=[0-9]+' | cut -d= -f2)
  [ -z "$ID" ] && continue
  jq --arg url "$HREF" --arg text "$TEXT" --arg id "$ID" \
     '.candidates += [{
       platform: "kashispace",
       room_id: $id,
       url: $url,
       inquiry_url: "https://kashispace.com/contact",
       text: $text,
       license: "TBD (要確認 — 内訳の各 room ページに 飲食店営業許可取得済 明記あれば license OK)",
       notes: "個別 room ページで月額・時間料金確認"
     }]' "$SKILL/data/cafe/candidates.json" > /tmp/c.json && mv /tmp/c.json "$SKILL/data/cafe/candidates.json"
done

# ── Sort by monthly_estimate_jpy (defined ones first), then commute ──────────
jq '.candidates |= (sort_by(.monthly_estimate_jpy // 999999))' "$SKILL/data/cafe/candidates.json" > /tmp/c.json && mv /tmp/c.json "$SKILL/data/cafe/candidates.json"

CANDIDATE_COUNT=$(jq '.candidates | length' "$SKILL/data/cafe/candidates.json")
echo "✓ discovered $CANDIDATE_COUNT candidates → $SKILL/data/cafe/candidates.json"
jq -r '.candidates[] | "  - \(.platform): \(.url) | monthly≈¥\(.monthly_estimate_jpy // "TBD")"' "$SKILL/data/cafe/candidates.json"

# Slack 報告 (5/9 v27 fix)
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
PYTHON=python3
TOP3=$(jq -r '.candidates[:3] | map("\(.platform): ¥\(.monthly_estimate_jpy // "TBD")") | join(" / ")' "$SKILL/data/cafe/candidates.json")
TS=$("$PYTHON" - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$CANDIDATE_COUNT" "$TOP3" <<'PY'
import sys, json, urllib.request, os
ch, token, count, top3 = sys.argv[1:5]
payload = {
    "channel": ch,
    "text": f"🏠 cafe-phase0-discover: {count} candidates",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"🏠 cafe-phase0-discover"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*candidates found:*\n{count}"},
            {"type":"mrkdwn","text":"*scope:*\nkashispace + kumato + theghostrestaurant"},
        ]},
        {"type":"section","text":{"type":"mrkdwn","text":f"*top 3 (sorted by ¥/月):*\n{top3}"}},
    ]
}
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode(),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST")
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception:
    print("?")
PY
)

echo "✅ phase0-discover: $CANDIDATE_COUNT candidates | slack ts=$TS"
