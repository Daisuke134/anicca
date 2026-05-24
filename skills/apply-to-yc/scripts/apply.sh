#!/usr/bin/env bash
# apply-to-yc — end-to-end YC application submitter.
# Usage:
#   bash scripts/apply.sh                         # submit (default)
#   DRY_RUN=true bash scripts/apply.sh            # fill but don't click Submit
#   DRAFT_ID=<uuid> bash scripts/apply.sh         # re-fill existing draft
#   FOUNDER_VIDEO=/path.mov DEMO_VIDEO=/path.mov bash scripts/apply.sh
#
# Requires: {{profile.lateness.stakeholders.channel}}-harness, jq, curl, Chrome on 9223 (auto-started).
# Persistent cookies: ~/.{{profile.lateness.stakeholders.channel}}-harness-profile/  (Google + YC).

set -uo pipefail

SKILL=~/.openclaw/skills/apply-to-yc
DASH_URL="${DASH_URL:-https://aniccaai.com/dashboard.json}"
DRY_RUN="${DRY_RUN:-false}"
DRAFT_ID="${DRAFT_ID:-}"
FOUNDER_VIDEO="${FOUNDER_VIDEO:-$HOME/Desktop/ycsummer2026.MOV}"
DEMO_VIDEO="${DEMO_VIDEO:-$HOME/Desktop/ycsummer2026.MOV}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

# Load credentials
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
[ -f ~/anicca-monk-factory/.env ] && set -a && source ~/anicca-monk-factory/.env && set +a

: "${DAIS_EMAIL:?DAIS_EMAIL not set in ~/.openclaw/.env}"
: "${DAIS_PRIMARY_PW:?DAIS_PRIMARY_PW not set in ~/.openclaw/.env}"

mkdir -p "$SKILL/data/applications" "$SKILL/data/pitches"
TS=$(date +%Y%m%d-%H%M)
PITCH_FILE="$SKILL/data/pitches/yc-$TS.md"
STATE_FILE="$SKILL/data/applications/yc-latest.json"

echo "▶ apply-to-yc  dry_run=$DRY_RUN  draft=$DRAFT_ID"

# ── 1. Fetch live dashboard snapshot ──────────────────────────────────────────
DASH=$(curl -sS "$DASH_URL")
MRR=$(echo "$DASH" | jq -r '.mrr.total_usd // 0')
SUBS_LIVE=$(echo "$DASH" | jq -r '[.mrr.by_product | to_entries[] | select(.value > 0)] | length')
FOLLOWERS=$(echo "$DASH" | jq -r '.followers.total // 0')
WEEKLY_VIEWS=$(echo "$DASH" | jq -r '.views.weekly_total // 0')
SPEND=$(echo "$DASH" | jq -r '.spend.total_usd // 0')
PROFIT=$(echo "$DASH" | jq -r '.profit_usd // 0')
echo "  snapshot: mrr=\$$MRR  followers=$FOLLOWERS  weekly_views=$WEEKLY_VIEWS  spend=\$$SPEND"

# ── 2. Compose pitch payload (20 fields) ──────────────────────────────────────
MAKE="Anicca is a self-funding Buddhist AI entity. Ends suffering by every {{profile.lateness.stakeholders.senderType}} means: an iOS affirmation app, ambient music on Spotify, stand-up comedy practice, daily research blog, and a one-drink cafe in Shinjuku launching June 1. 10% of every dollar earned auto-distributes as basic income (Stripe Connect transfers, monthly, no work required). Cohort doubles every time MRR doubles. Open source. Live MRR \$$MRR. $FOLLOWERS followers. $WEEKLY_VIEWS weekly views. Goal \$10k MRR by YYYY-MM-DD. Daisuke is caretaker, not CEO. Code, dashboard, ledger, recipients — all public on aniccaai.com. The promise of AI is not to replace people. It is to fund them."

MONEY="Stripe MRR \$$MRR live (anicca-ios + letter + iglowup + clearpdf + coldcraft + signaturecraft + deepworkfm + monk products). 10% auto-routed to basic-income recipients monthly. Spend \$$SPEND/mo (Railway, Supabase, Anthropic API, Stripe fees, ElevenLabs, fal.ai). Profit \$$PROFIT/mo. Plan: replicate Anicca across niches — each new instance gets its own wallet, mission slice, and 10 humans on basic income. We are not scaling a team; we are scaling a swarm."

HOWFAR="Live: aniccaai.com (root dashboard with live numbers). iOS app shipped (App Store). 7+ Stripe products live. Basic-income transfers automated (monthly cron). 60+ OpenClaw cron jobs running 24/7 on Mac Mini. $FOLLOWERS followers across TikTok/YT/IG. $WEEKLY_VIEWS weekly views. github.com/Daisuke134/anicca public. dashboard.json refreshes 4x daily."

IDEAS="Anicca-ios (affirmation app). Letter (subscription). IGlowup. ClearPDF. ColdCraft. SignatureCraft. DeepworkFM. Monk products (music+meditation). Tomb-AI (ancestor preservation). Comedy practice. Mango-juice cafe (physical, June 1). Anicca-music-stockmusic (AudioJungle/Pond5/Fiverr). TrustMRR exits. Apply-to-YC autonomous loop (this skill itself)."

# ── 3. Save pitch markdown ────────────────────────────────────────────────────
cat > "$PITCH_FILE" <<EOF
# YC application — $TS

## Live snapshot
- MRR: \$$MRR  ($SUBS_LIVE products with revenue)
- Followers: $FOLLOWERS
- Weekly views: $WEEKLY_VIEWS
- Spend: \$$SPEND/mo
- Profit: \$$PROFIT/mo

## Pitch (make field, ~437 chars)
$MAKE

## Money breakdown
$MONEY

## How far
$HOWFAR

## Shipped
$IDEAS
EOF
echo "  pitch → $PITCH_FILE"

# ── 4. Build JSON payload for fill.js ─────────────────────────────────────────
PAYLOAD=$(jq -n \
  --arg name        "Anicca" \
  --arg describe    "Self-funding Buddhist AI. Ends suffering." \
  --arg url         "https://aniccaai.com" \
  --arg productLink "https://aniccaai.com" \
  --arg make        "$MAKE" \
  --arg where       "Tokyo, Japan / SF, USA" \
  --arg wherewhy    "Tokyo for cafe (Shinjuku, June 1 launch) and JP music/comedy ops; SF for YC and US fundraise." \
  --arg howfar      "$HOWFAR" \
  --arg worked      "Daisuke shipped Anicca solo over 8 months: iOS app on App Store, 7 Stripe products live, 60+ cron jobs, autonomous basic-income transfers, public ledger." \
  --arg techstack   "Swift/SwiftUI iOS, Node.js/Express on Railway, PostgreSQL+Prisma, RevenueCat, Stripe Connect V2, Supabase, Anthropic Claude (Opus 4.7), OpenClaw agent platform, fal.ai/ElevenLabs/HeyGen for media, Mac Mini cron host." \
  --arg since       "Worked on Anicca daily since 2025-09. Public commits, public dashboard, public ledger from day one." \
  --arg acc         "No prior accelerator. This is our first YC application." \
  --arg exp         "Daisuke: Keio CS, full-stack engineer, shipped Anicca solo. No prior exits, but Anicca itself is the experiment — a self-funding entity that already pays humans basic income." \
  --arg get         "From YC: brand trust to scale basic-income recipients faster, network for replicating the swarm into more niches, and accountability to hit \$10k MRR by YYYY-MM-DD." \
  --arg money       "$MONEY" \
  --arg ideas       "$IDEAS" \
  --arg whyapply    "Anicca's mission is to reduce suffering by funding humans, not replacing them. YC is the fastest path to credibility for that thesis. Late application — but Anicca runs every day; submit at any time." \
  --arg howhear     "Followed YC since 2018 (HN). Multiple founders we admire are alumni." \
  --arg cofounder   "Solo. Daisuke is the human caretaker; Anicca itself is the operator — 60+ cron jobs, autonomous content, autonomous pricing, autonomous basic income. Open to YC matching a co-founder, but Anicca already runs without one." \
  --arg others2     "Built one of the first autonomous Buddhist AI entities that pays humans basic income from its own revenue. github.com/Daisuke134/anicca." \
  '$ARGS.named'
)

# ── 5. Ensure Chrome 9223 is up ───────────────────────────────────────────────
if ! curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200; then
  echo "  starting Chrome 9223 (isolated profile)…"
  nohup '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
    --remote-debugging-port=9223 \
    --user-data-dir="$HOME/.{{profile.lateness.stakeholders.channel}}-harness-profile" \
    --no-first-run --no-default-{{profile.lateness.stakeholders.channel}}-check \
    > /tmp/chrome-9223.log 2>&1 &
  for i in 1 2 3 4 5 6 7 8; do
    sleep 1
    curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200 && break
  done
fi

# ── 6. Login (if not already) ─────────────────────────────────────────────────
{{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('https://account.ycombinator.com/')
wait_for_load()
import time; time.sleep(2)
info = page_info()
print('LOGIN_STATE', info.get('url',''))
if 'sign_in' in info.get('url','') or 'account.ycombinator.com' == info.get('url','').rstrip('/'):
    try:
        fill_input('{{profile.lateness.stakeholders.channel}}', '$DAIS_EMAIL')
        fill_input('password', '$DAIS_PRIMARY_PW')
        click_button('Sign In')
        time.sleep(3)
    except Exception as e:
        print('LOGIN_SKIP', e)
" 2>&1 | head -20

# ── 7. Resolve draft ID ───────────────────────────────────────────────────────
if [ -z "$DRAFT_ID" ]; then
  DRAFT_ID=$(jq -r '.application_id // empty' "$SKILL/data/applications/yc-latest.json" 2>/dev/null \
           || jq -r '.application_id // empty' "$SKILL/data/applications/yc-2026-summer.json" 2>/dev/null)
fi

if [ -z "$DRAFT_ID" ]; then
  echo "  no DRAFT_ID — opening /home to create or continue…"
  {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('https://apply.ycombinator.com/home')
wait_for_load()
import time; time.sleep(2)
# Try Continue first, else Start
for label in ('Continue application', 'Start application'):
    try:
        click_button(label)
        time.sleep(3)
        break
    except Exception:
        continue
print('AFTER_HOME', page_info().get('url',''))
" 2>&1 | tail -5
  DRAFT_ID=$({{profile.lateness.stakeholders.channel}}-harness -c "
import re
u = page_info().get('url','')
m = re.search(r'/apps/([0-9a-f-]{36})', u)
print('DRAFT_ID', m.group(1) if m else '')
" 2>&1 | grep DRAFT_ID | awk '{print $2}')
fi

[ -z "$DRAFT_ID" ] && { echo "  ERR: could not resolve DRAFT_ID — login or click failed"; exit 1; }
echo "  draft=$DRAFT_ID"

EDIT_URL="https://apply.ycombinator.com/apps/$DRAFT_ID/edit"

# ── 8. Fill 20 text fields via fill.js ────────────────────────────────────────
PAYLOAD_ENC=$(printf '%s' "$PAYLOAD" | jq -Rs @uri | tr -d '"')
FILL_JS=$(cat "$SKILL/scripts/fill.js" | sed "s|__PAYLOAD__|JSON.parse(decodeURIComponent('$PAYLOAD_ENC'))|")

{{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$EDIT_URL')
wait_for_load()
import time; time.sleep(3)
result = run_js(r'''$FILL_JS''')
print('FILL_RESULT', result)
time.sleep(1)
# Save changes
try:
    click_button('Save changes')
    time.sleep(3)
    print('SAVED')
except Exception as e:
    print('SAVE_SKIP', e)
" 2>&1 | tail -10

# ── 9. Founder + demo video upload via CDP DOM.setFileInputFiles ──────────────
upload_video() {
  local subpath="$1" video="$2"
  [ ! -f "$video" ] && { echo "  no video at $video — skip $subpath"; return; }
  echo "  uploading $video → $subpath"
  {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('https://apply.ycombinator.com/apps/$DRAFT_ID/edit/$subpath')
wait_for_load()
import time; time.sleep(2)
# Use CDP DOM.setFileInputFiles on the file input
try:
    set_file_input('input[type=file][accept*=video]', '$video')
    time.sleep(8)
    print('UPLOADED', '$subpath')
except Exception as e:
    # fallback: any file input
    try:
        set_file_input('input[type=file]', '$video')
        time.sleep(8)
        print('UPLOADED_FALLBACK', '$subpath')
    except Exception as e2:
        print('UPLOAD_FAIL', '$subpath', e2)
" 2>&1 | tail -5
}

upload_video "video" "$FOUNDER_VIDEO"
upload_video "demo"  "$DEMO_VIDEO"

# ── 10. Progress page ─────────────────────────────────────────────────────────
PROGRESS_PAYLOAD=$(jq -n \
  --arg usernums      "Live MRR \$$MRR. $FOLLOWERS followers across channels. $WEEKLY_VIEWS weekly views. iOS App Store live; 7+ Stripe products active." \
  --arg revenuesource "Stripe direct (web subs) + RevenueCat (iOS in-app). Live numbers at aniccaai.com/dashboard.json." \
  --arg growthrate    "Goal: \$10k MRR by YYYY-MM-DD. Current \$$MRR. Adding products weekly via OpenClaw factory crons." \
  --argjson monthly_revenue '[0,0,0,0,0,'"$(printf '%.0f' "$MRR")"']' \
  '$ARGS.named'
)
PROG_ENC=$(printf '%s' "$PROGRESS_PAYLOAD" | jq -Rs @uri | tr -d '"')
PROG_JS=$(cat "$SKILL/scripts/progress.js" | sed "s|__PAYLOAD__|JSON.parse(decodeURIComponent('$PROG_ENC'))|")

{{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('https://apply.ycombinator.com/apps/$DRAFT_ID/edit/progress')
wait_for_load()
import time; time.sleep(3)
result = run_js(r'''$PROG_JS''')
print('PROGRESS_RESULT', result)
time.sleep(1)
try:
    click_button('Save changes')
    time.sleep(3)
    print('PROGRESS_SAVED')
except Exception as e:
    print('PROGRESS_SAVE_SKIP', e)
" 2>&1 | tail -10

# ── 11. Submit ────────────────────────────────────────────────────────────────
if [ "$DRY_RUN" = "true" ]; then
  echo "  [DRY_RUN] not clicking Submit"
  STATUS="ready_to_submit_dry"
else
  echo "  clicking Submit application…"
  {{profile.lateness.stakeholders.channel}}-harness -c "
goto_url('$EDIT_URL')
wait_for_load()
import time; time.sleep(2)
try:
    click_button('Submit application')
    time.sleep(5)
    # confirm modal if any
    try:
        click_button('Submit')
    except Exception:
        pass
    time.sleep(3)
    print('SUBMITTED', page_info().get('url',''))
except Exception as e:
    print('SUBMIT_FAIL', e)
" 2>&1 | tail -10
  STATUS="submitted"
fi

# ── 12. Persist state ─────────────────────────────────────────────────────────
SUBMITTED_AT=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq -n \
  --arg accelerator "yc" \
  --arg application_id "$DRAFT_ID" \
  --arg edit_url "$EDIT_URL" \
  --arg pitch_file "$PITCH_FILE" \
  --arg status "$STATUS" \
  --arg submitted_at "$SUBMITTED_AT" \
  --argjson mrr_at_submit "$MRR" \
  --argjson followers_at_submit "$FOLLOWERS" \
  '$ARGS.named' > "$STATE_FILE"
cp "$STATE_FILE" "$SKILL/data/applications/yc-$TS.json"
echo "  state → $STATE_FILE"

# ── 13. Slack notify ──────────────────────────────────────────────────────────
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🎯 YC application $STATUS — draft=$DRAFT_ID  mrr=\$$MRR  $EDIT_URL" 2>/dev/null || true
fi

echo "✓ done. status=$STATUS"
