#!/usr/bin/env bash
# phase--1_waitlist-collect-daily.sh
# cron: `0 14 * * *` JST (5/7 - 5/31 daily, post-launch も継続)
#
# Collection そのものは Netlify function `cafe-waitlist.js` が自動で
#   Supabase cafe_waitlist + Resend 確認メール を行う。
# この cron は **日次サマリ** を Slack #metrics に報告:
#   - 累計 signup 数 / 24h delta / 今日の送信先 sample 3 件
#   - data/prelaunch/waitlist.json に snapshot を 30 件保持
#
# stdout final line:
#   ✅ waitlist: total=<N> (+<delta>) days_to_launch=<N>
#   ❌ waitlist FAILED: <reason>

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
PRELAUNCH_DIR="$SKILL/data/prelaunch"
WAITLIST_FILE="$PRELAUNCH_DIR/waitlist.json"
mkdir -p "$PRELAUNCH_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a

PYTHON="python3"
LAUNCH_DATE="2026-06-01"
TODAY_TS=$(date +%s)
LAUNCH_TS=$(date -j -f "%Y-%m-%d" "$LAUNCH_DATE" +%s 2>/dev/null || python3 -c "import datetime;print(int(datetime.datetime.fromisoformat('$LAUNCH_DATE').timestamp()))")
DAYS=$(( (LAUNCH_TS - TODAY_TS) / 86400 ))

# Pull current waitlist via Supabase REST
ROWS=$($PYTHON - <<PY
import os, json, urllib.request, urllib.parse
url = os.environ["SUPABASE_URL"] + "/rest/v1/cafe_waitlist"
params = {"select": "{{profile.lateness.stakeholders.channel}},signed_up_at,source", "order": "signed_up_at.desc", "limit": "200"}
url += "?" + urllib.parse.urlencode(params)
req = urllib.request.Request(url, headers={
    "apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_ROLE_KEY']}",
})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(r.read().decode())
except Exception as e:
    print(json.dumps({"_error": str(e)[:200]}))
PY
)

TOTAL=$(echo "$ROWS" | $PYTHON -c "import sys,json
d=json.load(sys.stdin)
print(0 if isinstance(d, dict) else len(d))")

# Yesterday total from previous snapshot
PREV_TOTAL=0
if [ -f "$WAITLIST_FILE" ]; then
  PREV_TOTAL=$($PYTHON -c "
import json,pathlib
p=pathlib.Path('$WAITLIST_FILE')
try:
    d=json.loads(p.read_text())
    snaps=d.get('snapshots',[])
    print(snaps[-1].get('total',0) if snaps else 0)
except Exception:
    print(0)
")
fi

DELTA=$(( TOTAL - PREV_TOTAL ))

# Last 24h subset (for sample) — pass ROWS via tmpfile to avoid stdin/heredoc conflict
ROWS_FILE=$(mktemp -t waitlist-rows)
trap "rm -f $ROWS_FILE" EXIT
echo "$ROWS" > "$ROWS_FILE"

SAMPLE=$($PYTHON - "$ROWS_FILE" <<'PY'
import sys, json, datetime
data = json.loads(open(sys.argv[1]).read())
if isinstance(data, dict):
    print(json.dumps([]))
else:
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    recent = []
    for row in data:
        ts = row.get("signed_up_at","")
        try:
            t = datetime.datetime.fromisoformat(ts.replace("Z","+00:00")).replace(tzinfo=None)
            if t >= cutoff:
                recent.append(row.get("{{profile.lateness.stakeholders.channel}}",""))
        except Exception:
            pass
    print(json.dumps(recent[:3]))
PY
)

# snapshot persist
$PYTHON - <<PY
import json, datetime, pathlib
p = pathlib.Path("$WAITLIST_FILE")
db = json.loads(p.read_text()) if p.exists() else {"snapshots": []}
db.setdefault("snapshots", []).append({
    "captured_at": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "total": $TOTAL,
    "delta_24h": $DELTA,
    "days_to_launch": $DAYS,
})
db["snapshots"] = db["snapshots"][-30:]
p.write_text(json.dumps(db, ensure_ascii=False, indent=2))
PY

# Slack
$PYTHON - "$SLACK_CHANNEL_ID" "$SLACK_BOT_TOKEN" "$TOTAL" "$DELTA" "$DAYS" "$SAMPLE" <<'PY'
import sys, json, urllib.request
ch, token, total, delta, days, sample_json = sys.argv[1:7]
total, delta, days = int(total), int(delta), int(days)
sample = json.loads(sample_json) if sample_json else []
sample_block = "\n".join(f"• `{e}`" for e in sample) if sample else "_no signups in last 24h_"

payload = {
    "channel": ch,
    "text": f"📨 waitlist: {total} signups (+{delta}/24h), {days} days to launch",
    "blocks": [
        {"type":"header","text":{"type":"plain_text","text":"📨 cafe-waitlist-collect-daily"}},
        {"type":"section","fields":[
            {"type":"mrkdwn","text":f"*total signups:*\n{total}"},
            {"type":"mrkdwn","text":f"*last 24h:*\n+{delta}"},
            {"type":"mrkdwn","text":f"*days to launch:*\n{days}"},
            {"type":"mrkdwn","text":f"*launch date:*\n2026-06-01"},
        ]},
        {"type":"section","text":{"type":"mrkdwn","text":f"*recent signups (24h):*\n{sample_block}"}},
    ]
}
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Authorization":f"Bearer {token}","Content-Type":"application/json; charset=utf-8"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        print(json.loads(r.read().decode()).get("ts","?"))
except Exception:
    print("?")
PY
TS_OUT=$(tail -1)

echo "✅ waitlist: total=$TOTAL (+$DELTA) days_to_launch=$DAYS"
