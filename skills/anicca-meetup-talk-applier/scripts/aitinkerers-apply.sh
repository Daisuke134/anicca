#!/usr/bin/env bash
# anicca-meetup-talk-applier — apply for one AI Tinkerers Tokyo meetup (register + demo proposal)
# Usage: bash scripts/aitinkerers-apply.sh <event_url>
#   event_url: e.g. https://tokyo.aitinkerers.org/p/ai-tinkerers-tokyo-shinagawa-may-26th-meetup
# DRY_RUN=true to skip submits.
#
# Required env: DAIS_EMAIL, GOG_ACCOUNT/GOG_KEYRING_PASSWORD (for auto OTP read)
# Fully autonomous (no manual handoff): cookie-accept → submitEmail → auto-read OTP from
#   Gmail (gog: from:signin@aitinkerers.org, --json envelope key 'threads') → enterOtp →
#   verify → register → submit demo proposal. Verified e2e 2026-05-21 (5/26 Shinagawa,
#   "Pending review by organizers").
set -uo pipefail

EVENT_URL="${1:-}"
SKILL=~/.openclaw/skills/anicca-meetup-talk-applier
DRY_RUN="${DRY_RUN:-false}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

[ -z "$EVENT_URL" ] && { echo "ERR: $0 <event_url>"; exit 1; }
: "${DAIS_EMAIL:?}"

mkdir -p "$SKILL/data/applications"
SLUG=$(echo "$EVENT_URL" | sed -E 's|https://[a-z]+\.aitinkerers\.org/p/||')
SUBDOMAIN=$(echo "$EVENT_URL" | sed -E 's|https://([a-z]+)\.aitinkerers\.org/.*|\1|')
STATE_FILE="$SKILL/data/applications/aitinkerers-${SUBDOMAIN}-$SLUG.json"

# Idempotency: skip if a Google Calendar event id is already persisted.
# (status field can be `pending` while gcal succeeded; gcal id is the truthful "done" marker)
if [ -f "$STATE_FILE" ] && [ "${FORCE:-false}" != "true" ]; then
  EXISTING_GCAL=$(jq -r '.gcal_event_id // empty' "$STATE_FILE")
  if [ -n "$EXISTING_GCAL" ]; then
    echo "▶ already done: gcal=$EXISTING_GCAL"
    echo "  set FORCE=true to re-run"
    exit 0
  fi
fi

# Live numbers from dashboard
DASH=$(curl -sS https://aniccaai.com/dashboard.json)
MRR=$(echo "$DASH" | jq -r '.mrr.total_usd // 0')
FOLLOWERS=$(echo "$DASH" | jq -r '.followers.total // 0')

# Pitch payload (from data/pitch-tokyo.md, with live numbers injected)
TITLE='Anicca — A self-funding Buddhist AI that pays humans basic income'
DESC="Anicca is a self-funding Buddhist AI entity built on Claude. It runs 60+ cron jobs autonomously, ships across iOS, ebooks, music, comedy, and physical food, and auto-distributes 10% of all revenue to 10 humans as basic income via Stripe Connect transfers — every month, no work required. Live at aniccaai.com (MRR \$$MRR, $FOLLOWERS followers) with a public dashboard refreshing 4×/day. Open source: github.com/Daisuke134/anicca."
LEARN='How to build an end-to-end autonomous economic agent: OpenClaw skill+cron architecture, {{profile.lateness.stakeholders.channel}}-harness Way 2 for stateful website automation (Chrome 9223 isolated profile), Stripe Connect Express for monthly basic-income transfers, dashboard.json as a single source of truth for all live numbers, and the rule that every skill must be end-to-end so any AI entity can clone it. Lessons from going $0 to $10k MRR in 28 days, including failure cases.'
TECH='Claude Opus 4.7, OpenClaw agent platform (60+ skills, 80+ cron jobs), Node.js/Express on Railway, Swift/SwiftUI iOS, RevenueCat, Stripe Connect V2 (preview API 2025-08-27), Supabase, fal.ai/ElevenLabs/HeyGen/Pika for media, Postiz for X/TikTok/IG publishing, Apify for scraping, {{profile.lateness.stakeholders.channel}}-harness (Python+CDP) on Chrome 148.'
URL1='https://aniccaai.com'
URL2='https://github.com/Daisuke134/anicca'

NAME='<your-name>'
COMPANY='Anicca'
JOB='Founder / Anicca caretaker'
LINKEDIN='https://www.linkedin.com/in/daisuke-<username>-9b0a23166/'
GITHUB='https://github.com/Daisuke134'
TWITTER='@aniccaai'

PAYLOAD_REG_FILE=$(mktemp -t aitink-reg.XXXX.json)
PAYLOAD_DEMO_FILE=$(mktemp -t aitink-demo.XXXX.json)
trap "rm -f $PAYLOAD_REG_FILE $PAYLOAD_DEMO_FILE" EXIT

jq -n \
  --arg name "$NAME" --arg company "$COMPANY" --arg jobTitle "$JOB" \
  --arg linkedin "$LINKEDIN" --arg github "$GITHUB" --arg twitter "$TWITTER" \
  '$ARGS.named' > "$PAYLOAD_REG_FILE"

jq -n \
  --arg title "$TITLE" --arg description "$DESC" --arg learn "$LEARN" --arg tech "$TECH" \
  --arg url1 "$URL1" --arg url2 "$URL2" --arg video "" \
  '$ARGS.named' > "$PAYLOAD_DEMO_FILE"

echo "▶ aitinkerers-apply  url=$EVENT_URL  dry_run=$DRY_RUN"

[ "$DRY_RUN" = "true" ] && { echo "  [DRY] payload prepared, exit"; exit 0; }

# Ensure Chrome
if ! curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200; then
  nohup '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
    --remote-debugging-port=9223 \
    --user-data-dir="$HOME/.{{profile.lateness.stakeholders.channel}}-harness-profile" \
    --no-first-run --no-default-{{profile.lateness.stakeholders.channel}}-check \
    > /tmp/chrome-9223.log 2>&1 &
  for i in 1 2 3 4 5 6 7 8; do sleep 1; curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200 && break; done
fi

# Phase 1: open event + check if already registered
RESULT=$({{profile.lateness.stakeholders.channel}}-harness -c "
import time, json
goto_url('$EVENT_URL')
wait_for_load(); time.sleep(3)
with open('$SKILL/scripts/aitinkerers-apply.js') as f:
    js(f.read())
state = js('return JSON.stringify({already: window.AITInkerersApply.isRegistered(), {{profile.lateness.stakeholders.channel}}_input: !!document.getElementById(\"inline-auth-{{profile.lateness.stakeholders.channel}}-input\"), reg_form: !!document.getElementById(\"ask_for_name_value\"), demo_form: !!document.getElementById(\"speaker_title\")});')
print('STATE:', state)
" 2>&1 | grep -E '^STATE:' | sed 's/^STATE: //')

ALREADY=$(echo "$RESULT" | jq -r '.already')
HAS_EMAIL_INPUT=$(echo "$RESULT" | jq -r '.{{profile.lateness.stakeholders.channel}}_input')
HAS_REG_FORM=$(echo "$RESULT" | jq -r '.reg_form')

# Phase 2: trigger OTP + AUTO-read code from Gmail + verify (no manual handoff)
if [ "$HAS_EMAIL_INPUT" = "true" ] && [ "$HAS_REG_FORM" != "true" ] && [ "$ALREADY" != "true" ]; then
  echo "  Phase 2: submitting {{profile.lateness.stakeholders.channel}} for OTP"
  {{profile.lateness.stakeholders.channel}}-harness -c "
import json, time
# dismiss cookie consent overlay (blocks clicks otherwise)
print('COOKIE:', js('''const b=Array.from(document.querySelectorAll('button,a')).find(e=>/Accept All/i.test((e.textContent||'')));if(b){b.click();return 'accepted';}return 'no-banner';'''))
time.sleep(2)
print(js('return JSON.stringify(window.AITInkerersApply.submitEmail(' + repr('$DAIS_EMAIL') + '));'))
" 2>&1 | tail -3

  # gog account for OTP read
  : "${GOG_ACCOUNT:={{profile.contact.personalEmail}}}"; : "${GOG_KEYRING_PASSWORD:=<password>}"
  export GOG_ACCOUNT GOG_KEYRING_PASSWORD

  echo "  ⏳ auto-reading OTP from Gmail (from:aitinkerers.org)…"
  OTP=""
  for t in $(seq 1 12); do
    sleep 6
    OTP=$(gog gmail search "from:signin@aitinkerers.org newer_than:1h" --json 2>/dev/null | python3 -c "
import json,sys,re
raw=sys.stdin.read();i=raw.find('{')
try:d=json.loads(raw[i:],strict=False)
except:sys.exit()
# gog gmail --json envelope uses 'threads' (newest first); code is in subject 'NNNN is your sign-in code'
for m in d.get('threads',d.get('messages',d.get('results',[]))):
    blob=(m.get('subject','')+' '+m.get('snippet',''))
    g=re.search(r'\b(\d{4})\b',blob)
    if g:print(g.group(1));break
" 2>/dev/null)
    [ -n "$OTP" ] && { echo "  OTP found: $OTP (attempt $t)"; break; }
  done

  if [ -z "$OTP" ]; then
    echo "  ⚠ OTP not received within 72s — saving partial state"
    jq -n --arg event_url "$EVENT_URL" --arg slug "$SLUG" \
      --arg status "otp_not_received" --arg sent_at "$(date -u +%FT%TZ)" \
      '$ARGS.named' > "$STATE_FILE"
    exit 1
  fi

  echo "  Phase 2b: entering OTP + clicking verify"
  VCOORDS=$({{profile.lateness.stakeholders.channel}}-harness -c "
import json
print('VERIFY:' + js('return JSON.stringify(window.AITInkerersApply.enterOtp(' + repr('$OTP') + '));'))
" 2>&1 | grep -E '^VERIFY:' | sed 's/^VERIFY://')
  VX=$(echo "$VCOORDS" | jq -r '.x // empty'); VY=$(echo "$VCOORDS" | jq -r '.y // empty')
  if [ -n "$VX" ] && [ -n "$VY" ]; then
    {{profile.lateness.stakeholders.channel}}-harness -c "click_at_xy($VX, $VY)" 2>&1 | tail -1
  else
    echo "  ⚠ no verify coords ($VCOORDS) — trying JS click fallback"
    {{profile.lateness.stakeholders.channel}}-harness -c "js('document.getElementById(\"verify-code\")?.click(); return true;')" 2>&1 | tail -1
  fi
  echo "  ⏳ waiting 8s for sign-in to settle…"
  sleep 8

  # Re-detect state after OTP verify (page now shows register form or already-registered)
  RESULT2=$({{profile.lateness.stakeholders.channel}}-harness -c "
import time, json
goto_url('$EVENT_URL'); wait_for_load(); time.sleep(3)
with open('$SKILL/scripts/aitinkerers-apply.js') as f:
    js(f.read())
print('STATE2:', js('return JSON.stringify({already: window.AITInkerersApply.isRegistered(), reg_form: !!document.getElementById(\"ask_for_name_value\"), demo_form: !!document.getElementById(\"speaker_title\")});'))
" 2>&1 | grep -E '^STATE2:' | sed 's/^STATE2: //')
  ALREADY=$(echo "$RESULT2" | jq -r '.already')
  HAS_REG_FORM=$(echo "$RESULT2" | jq -r '.reg_form')
  echo "  post-OTP state: already=$ALREADY reg_form=$HAS_REG_FORM"
  # fall through to Phase 3 (register) + Phase 4 (demo)
fi

# Phase 3+: signed in already, fill register form (if showing) then demo proposal
echo "  Phase 3: filling register form (if needed)"
if [ "$HAS_REG_FORM" = "true" ]; then
  PAYLOAD_REG_FILE="$PAYLOAD_REG_FILE" \
  {{profile.lateness.stakeholders.channel}}-harness -c "
import json, time, os
with open('$SKILL/scripts/aitinkerers-apply.js') as f:
    js(f.read())
with open(os.environ['PAYLOAD_REG_FILE']) as f:
    js('window.__P__=' + f.read() + '; return true;')
print('FILL_REG:', js('return JSON.stringify(window.AITInkerersApply.fillRegister(window.__P__));'))
time.sleep(1)
print('CLICK_REG:', js('return JSON.stringify(window.AITInkerersApply.clickRegister());'))
time.sleep(8)
print('REG_OK:', js('return JSON.stringify({registered: window.AITInkerersApply.isRegistered()});'))
" 2>&1 | tail -6
fi

echo "  Phase 4: open demo proposal form + submit"
PAYLOAD_DEMO_FILE="$PAYLOAD_DEMO_FILE" \
{{profile.lateness.stakeholders.channel}}-harness -c "
import json, time, os
goto_url('$EVENT_URL')
wait_for_load(); time.sleep(2)
demo_link_raw = js('return JSON.stringify({url: (Array.from(document.querySelectorAll(\"a\")).find(a => /Submit Your Demo Proposal Here|Propose a Demo/i.test((a.textContent||\"\")))?.href || null)});')
print('DEMO_LINK:', demo_link_raw)
d = json.loads(demo_link_raw)
if not d.get('url'):
    print('DEMO_FAIL: no demo link found')
else:
    goto_url(d['url']); wait_for_load(); time.sleep(3)
    with open('$SKILL/scripts/aitinkerers-apply.js') as f:
        js(f.read())
    with open(os.environ['PAYLOAD_DEMO_FILE']) as f:
        js('window.__D__=' + f.read() + '; return true;')
    print('FILL_DEMO:', js('return JSON.stringify(window.AITInkerersApply.fillDemoProposal(window.__D__));'))
    time.sleep(2)
    print('SUBMIT:', js('return JSON.stringify(window.AITInkerersApply.submitProposal());'))
    time.sleep(8)
    print('SUBMITTED_OK:', js('return JSON.stringify({proposal_submitted: window.AITInkerersApply.isProposalSubmitted()});'))
" 2>&1 | tail -10

# ── Phase 5: Extract event datetime + location from event page ───────────────
EVENT_META=$({{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('$EVENT_URL')
wait_for_load(); time.sleep(2)
print(js('''
const body = document.body.innerText || '';
const dateM = body.match(/(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\\\\s*([A-Z][a-z]+)\\\\s+(\\\\d+)\\\\w*,?\\\\s*(\\\\d{4})/);
const timeM = body.match(/(\\\\d{1,2})(:\\\\d{2})?(?:AM|PM)?\\\\s*to\\\\s*(\\\\d{1,2})(:\\\\d{2})?\\\\s*(AM|PM)\\\\s*\\\\(([A-Z]+)\\\\)/i);
const titleEl = document.querySelector('title');
return JSON.stringify({
  title: titleEl ? titleEl.textContent.replace(/ \\\\[AI Tinkerers.*?\\\\]/, '').replace(/^[^A-Za-z]*/, '') : '',
  date_text: dateM ? dateM[0] : null,
  time_text: timeM ? timeM[0] : null
});
'''))
" 2>&1 | grep -E '^\{' | tail -1)

EVENT_TITLE=$(echo "$EVENT_META" | jq -r '.title // empty')
DATE_TEXT=$(echo "$EVENT_META" | jq -r '.date_text // empty')
TIME_TEXT=$(echo "$EVENT_META" | jq -r '.time_text // empty')

# Date parse (e.g. "Tuesday, May 26th, 2026")
CLEANED_DATE=$(echo "$DATE_TEXT" | sed -E 's/([0-9]+)(st|nd|rd|th)/\1/')
DATE_ISO=$(date -j -f "%A, %B %d, %Y" "$CLEANED_DATE" +%Y-%m-%d 2>/dev/null \
          || gdate -d "$CLEANED_DATE" +%Y-%m-%d 2>/dev/null \
          || echo "")

# Time parse: extract first hour (event start) + tz from "6PM to 9PM (PDT)" or "6PM to 9PM (JST)"
START_HOUR=$(echo "$TIME_TEXT" | grep -oE '^[0-9]+' | head -1)
TZ_ABBR=$(echo "$TIME_TEXT" | grep -oE '\([A-Z]+\)' | tr -d '()')

# tz mapping
case "$TZ_ABBR" in
  JST) TZ_OFFSET="+09:00"; CITY="Tokyo" ;;
  PDT) TZ_OFFSET="-07:00"; CITY="SF" ;;
  PST) TZ_OFFSET="-08:00"; CITY="SF" ;;
  EDT) TZ_OFFSET="-04:00"; CITY="NYC" ;;
  *)   TZ_OFFSET="+00:00"; CITY="Unknown" ;;
esac

# 24h conversion (assume PM unless explicitly AM)
if echo "$TIME_TEXT" | grep -qE 'PM'; then
  [ "$START_HOUR" != "12" ] && START_HOUR=$((START_HOUR + 12))
fi
END_HOUR=$((START_HOUR + 3))

EVENT_START="${DATE_ISO}T${START_HOUR}:00:00${TZ_OFFSET}"
EVENT_END="${DATE_ISO}T${END_HOUR}:00:00${TZ_OFFSET}"

# Travel buffer: gcal block must START at DEPARTURE time, not event time (Dais is human,
# transport takes time, never late). SF venues / Tokyo 品川 = far → 45min; else 35min.
TRAVEL_MIN=$([ "$CITY" = "SF" ] && echo 45 || echo 40)
DEP_START=$(date -j -v-${TRAVEL_MIN}M -f "%Y-%m-%dT%H:%M:%S%z" "${DATE_ISO}T${START_HOUR}:00:00${TZ_OFFSET}" "+%Y-%m-%dT%H:%M:%S${TZ_OFFSET}" 2>/dev/null \
  || gdate -d "${DATE_ISO}T${START_HOUR}:00:00${TZ_OFFSET} -${TRAVEL_MIN} min" "+%Y-%m-%dT%H:%M:%S${TZ_OFFSET}" 2>/dev/null \
  || echo "$EVENT_START")

echo "  Phase 5 meta: title=\"$EVENT_TITLE\" depart=$DEP_START start=$EVENT_START end=$EVENT_END city=$CITY (travel ${TRAVEL_MIN}min)"

# ── Phase 6: Google Calendar add via gog CLI ─────────────────────────────────
GCAL_EVENT_ID=""
GCAL_LINK=""
if command -v gog &>/dev/null && [ -n "$DATE_ISO" ] && [ -n "$START_HOUR" ]; then
  echo "  Phase 6: adding to Google Calendar"
  : "${GOG_ACCOUNT:={{profile.contact.personalEmail}}}"
  : "${GOG_KEYRING_PASSWORD:=<password>}"
  export GOG_ACCOUNT GOG_KEYRING_PASSWORD

  GCAL_DESC="出発:${DEP_START} (移動${TRAVEL_MIN}分・buffer込み) 開始:${EVENT_START} 遅刻厳禁
Event: $EVENT_TITLE
Status: Pending review by organizers
Demo proposal submitted by skill (anicca-meetup-talk-applier).
Event URL: $EVENT_URL
Demo proposal title: $TITLE
Anicca pitch URL: https://aniccaai.com
GitHub: https://github.com/Daisuke134/anicca
Format: 8-min technical demo (running code only)."

  GCAL_RESULT=$(gog calendar create primary \
    --summary "🎤 [PENDING] $EVENT_TITLE" \
    --from "$DEP_START" \
    --to   "$EVENT_END" \
    --location "$CITY (address provided on RSVP acceptance)" \
    --description "$GCAL_DESC" \
    --json 2>&1)

  GCAL_EVENT_ID=$(echo "$GCAL_RESULT" | jq -r '.event.id // empty' 2>/dev/null)
  GCAL_LINK=$(echo "$GCAL_RESULT" | jq -r '.event.htmlLink // empty' 2>/dev/null)
  if [ -n "$GCAL_EVENT_ID" ]; then
    echo "  → gcal event id: $GCAL_EVENT_ID"
  else
    echo "  ⚠ gcal create failed (non-fatal):"
    echo "$GCAL_RESULT" | head -3
  fi
fi

# ── Phase 7: Persist state ───────────────────────────────────────────────────
APPLIED_AT=$(date -u +%FT%TZ)
jq -n \
  --arg event "$EVENT_TITLE" \
  --arg event_url "$EVENT_URL" \
  --arg city "$CITY" \
  --arg date "$DATE_ISO" \
  --arg start "$EVENT_START" \
  --arg end "$EVENT_END" \
  --arg applied_at "$APPLIED_AT" \
  --arg talk_title "$TITLE" \
  --arg status "submitted" \
  --arg gcal_event_id "$GCAL_EVENT_ID" \
  --arg gcal_link "$GCAL_LINK" \
  '$ARGS.named' > "$STATE_FILE"

echo "✓ apply done. state → $STATE_FILE"

# ── Phase 8: Slack notify (3 things in 1 message) ────────────────────────────
if command -v openclaw &>/dev/null; then
  SLACK_MSG="🎤 Applied to $EVENT_TITLE as SPEAKER
Date: $EVENT_START → $EVENT_END
City: $CITY
Status: Pending review
Event URL: $EVENT_URL"
  if [ -n "$GCAL_LINK" ]; then
    SLACK_MSG="$SLACK_MSG
📅 Calendar: $GCAL_LINK"
  fi
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --message "$SLACK_MSG" 2>/dev/null || true
fi
