#!/usr/bin/env bash
# phase8-launch-day.sh — 6/1 LAUNCH DAY orchestrator.
# cron: `0 0 1 6 *` JST (yearly fire on June 1 00:00 — noop until launch year).
# Also event-triggered when uber-status.json transitions to live_active.
#
# Steps:
#   00:00 — Resend bulk {{profile.lateness.stakeholders.channel}} to all cafe_waitlist subscribers
#   09:00 — SNS burst (Postiz: TT + IG + X simultaneous)
#   any   — LP banner toggle is automatic via /cafe page.tsx (Date.now())
#
# Idempotent: state file data/cafe/launch-day.json prevents re-runs.

set -uo pipefail

SKILL=~/.openclaw/skills/opening-cafe-tokyo-skills
DATA_DIR="$SKILL/data/cafe"
STATE_FILE="$DATA_DIR/launch-day.json"
LAUNCH_DATE="2026-06-01"
mkdir -p "$DATA_DIR"

set -a; source "$HOME/.openclaw/.env"; set +a

TODAY=$(date +%Y-%m-%d)
NOW_HOUR=$(date +%H)
PY=python3

# Only fire on or after launch date
if [[ "$TODAY" < "$LAUNCH_DATE" ]]; then
  echo "▶ phase8: today=$TODAY < launch=$LAUNCH_DATE — skip"
  exit 0
fi

# Read state
EMAIL_DONE="false"
SNS_DONE="false"
if [ -f "$STATE_FILE" ]; then
  EMAIL_DONE=$(jq -r '.{{profile.lateness.stakeholders.channel}}_blast_done // false' "$STATE_FILE")
  SNS_DONE=$(jq -r '.sns_burst_done // false' "$STATE_FILE")
fi

echo "▶ phase8: launch_day $TODAY hour=$NOW_HOUR {{profile.lateness.stakeholders.channel}}=$EMAIL_DONE sns=$SNS_DONE"

# === Step 1: Email blast ===================================================
if [ "$EMAIL_DONE" != "true" ]; then
  echo "  📧 sending Resend bulk {{profile.lateness.stakeholders.channel}} to waitlist..."
  EMAILS=$($PY - <<'PY' 2>/dev/null || echo '[]'
import os, json, urllib.request, urllib.parse
url = os.environ["SUPABASE_URL"] + "/rest/v1/cafe_waitlist"
url += "?" + urllib.parse.urlencode({"select": "{{profile.lateness.stakeholders.channel}}", "limit": "5000"})
req = urllib.request.Request(url, headers={
    "apikey": os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    "Authorization": f"Bearer {os.environ['SUPABASE_SERVICE_ROLE_KEY']}",
})
try:
    with urllib.request.urlopen(req, timeout=15) as r:
        rows = json.loads(r.read().decode())
        print(json.dumps([row["{{profile.lateness.stakeholders.channel}}"] for row in rows if row.get("{{profile.lateness.stakeholders.channel}}")]))
except Exception as e:
    print("[]")
PY
)

  COUNT=$(echo "$EMAILS" | jq 'length')
  echo "  → $COUNT recipients"

  if [ -n "${RESEND_API_KEY:-}" ] && [ "$COUNT" -gt 0 ]; then
    UBER_URL=$(jq -r '.public_url // "https://aniccaai.com/cafe"' "$DATA_DIR/menu-publish.json" 2>/dev/null || echo "https://aniccaai.com/cafe")
    echo "$EMAILS" | $PY - "$UBER_URL" <<'PY' 2>/dev/null || true
import os, json, sys, urllib.request
{{profile.lateness.stakeholders.channel}}s = json.loads(sys.stdin.read())
uber_url = sys.argv[1]
subject = "Mango Reset is live. One drink. One reset."
html = f"""
<div style="font-family:Georgia,serif;background:#FBF7EF;color:#14100E;padding:48px 24px;text-align:center">
<h1 style="font-size:42px;font-style:italic;margin:0">It's time.</h1>
<p style="font-size:20px;margin:24px auto;max-width:560px">
  Mango Reset is now available on Uber Eats Tokyo.<br>
  Sat–Sun 11am–3pm. ¥1,500. 30-minute delivery.
</p>
<a href="{uber_url}" style="display:inline-block;background:#E89A3C;color:#14100E;padding:18px 48px;text-decoration:none;font-weight:600;letter-spacing:0.1em">ORDER ON UBER EATS →</a>
<p style="font-size:13px;color:#6B6258;margin-top:48px">Built to disappear. — anicca</p>
</div>
"""
url = "https://api.resend.com/{{profile.lateness.stakeholders.channel}}s"
hdr = {
  "Authorization": f"Bearer {os.environ['RESEND_API_KEY']}",
  "Content-Type": "application/json",
}
sent = 0
# Resend supports `to` array up to 50 per call; chunk it.
chunk = []
for e in {{profile.lateness.stakeholders.channel}}s:
    chunk.append(e)
    if len(chunk) >= 50:
        body = json.dumps({"from":"Anicca Cafe <hello@aniccaai.com>","to":chunk,"subject":subject,"html":html}).encode()
        try:
            urllib.request.urlopen(urllib.request.Request(url, data=body, headers=hdr, method="POST"), timeout=20).read()
            sent += len(chunk)
        except Exception:
            pass
        chunk = []
if chunk:
    body = json.dumps({"from":"Anicca Cafe <hello@aniccaai.com>","to":chunk,"subject":subject,"html":html}).encode()
    try:
        urllib.request.urlopen(urllib.request.Request(url, data=body, headers=hdr, method="POST"), timeout=20).read()
        sent += len(chunk)
    except Exception:
        pass
print(json.dumps({"sent": sent}))
PY
  fi

  EMAIL_DONE="true"
  jq --arg t "$(date -u +%FT%TZ)" --argjson n "$COUNT" \
    '.{{profile.lateness.stakeholders.channel}}_blast_done = true | .{{profile.lateness.stakeholders.channel}}_blast_at = $t | .{{profile.lateness.stakeholders.channel}}_blast_count = $n' \
    <<<"$(cat "$STATE_FILE" 2>/dev/null || echo '{}')" > "$STATE_FILE"
fi

# === Step 2: SNS burst (only after 09:00 JST) ==============================
if [ "$SNS_DONE" != "true" ] && [ "$NOW_HOUR" -ge 9 ]; then
  echo "  📣 SNS burst → Postiz TT + IG + X..."
  UBER_URL=$(jq -r '.public_url // "https://aniccaai.com/cafe"' "$DATA_DIR/menu-publish.json" 2>/dev/null)
  CAPTION="Mango Reset is live. One drink. One reset.

Sat–Sun · 11am–3pm · Tokyo only · ¥1,500
$UBER_URL

#anicca #tokyocafe #mango #諸行無常"

  if [ -n "${POSTIZ_API_KEY:-}" ] && [ -n "${POSTIZ_TIKTOK_INTEGRATION_ID:-}" ]; then
    for INT_VAR in POSTIZ_TIKTOK_INTEGRATION_ID POSTIZ_INSTAGRAM_INTEGRATION_ID POSTIZ_X_INTEGRATION; do
      INT_ID=$(eval echo "\$$INT_VAR")
      [ -z "$INT_ID" ] && continue
      $PY - "$INT_ID" "$CAPTION" <<'PY' 2>/dev/null || true
import os, json, sys, urllib.request
integration_id, caption = sys.argv[1], sys.argv[2]
body = json.dumps({
  "type": "draft",
  "shortLink": False,
  "posts": [{"integration": {"id": integration_id}, "value": [{"content": caption, "media": []}]}],
}).encode()
req = urllib.request.Request(
  os.environ.get("POSTIZ_BASE_URL","https://app.postiz.com") + "/public/v1/posts",
  data=body,
  headers={"Authorization": f"Bearer {os.environ['POSTIZ_API_KEY']}", "Content-Type":"application/json"},
  method="POST",
)
try:
    urllib.request.urlopen(req, timeout=15).read()
    print(json.dumps({"posted": integration_id}))
except Exception as e:
    print(json.dumps({"error": str(e)[:200]}))
PY
    done
  fi

  SNS_DONE="true"
  jq --arg t "$(date -u +%FT%TZ)" \
    '.sns_burst_done = true | .sns_burst_at = $t' \
    <<<"$(cat "$STATE_FILE" 2>/dev/null || echo '{}')" > "$STATE_FILE"
fi

# Slack
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --message "🚀 cafe LAUNCH DAY $TODAY · {{profile.lateness.stakeholders.channel}}=$EMAIL_DONE sns=$SNS_DONE" 2>/dev/null || true
fi

echo "✅ phase8: {{profile.lateness.stakeholders.channel}}=$EMAIL_DONE sns=$SNS_DONE"
