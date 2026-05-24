#!/usr/bin/env bash
# anicca-webapp-x-marketing — Channel B: Pain-Point thread per app per day
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-webapp-x-marketing
DRY_RUN="${DRY_RUN:-false}"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
ROT="$SKILL/state/rotation.json"
mkdir -p "$SKILL/state/threads"
TODAY=$(date -u +%Y-%m-%d)
MONTH=$(date -u +%Y-%m)
NOW=$(date -u +%FT%TZ)

# Pick today's app (rotation: index = day-of-week mod 7)
DOW=$(date +%w)
APP_JSON=$(jq -c --argjson i "$DOW" '.queue[$i]' "$ROT")
APP_SLUG=$(echo "$APP_JSON" | jq -r .slug)
APP_URL=$(echo "$APP_JSON" | jq -r .url)
APP_ICP=$(echo "$APP_JSON" | jq -r .icp)
APP_PAIN=$(echo "$APP_JSON" | jq -r .pain)

echo "▶ Pain-point  app=$APP_SLUG  ICP=$APP_ICP  pain=$APP_PAIN"

UTM="?utm_source=x&utm_medium=thread&utm_campaign=${APP_SLUG}-${MONTH}&utm_content=channel-B"
CTA_URL="${APP_URL}${UTM}"

# Templates per app — extend as products grow
case "$APP_SLUG" in
  letter)
    T1="The first 30 minutes of your morning decide your day. Not because of productivity. Because of what your mind grabs onto."
    T2="Most people grab anxiety, news, or a task list. The grip lasts hours."
    T3="Anicca Letter: one sentence in your inbox at 7 AM. From 2,500 years of Buddhist text. You read it in 4 seconds and your morning has a different shape."
    T4="Free for the first month. ${CTA_URL}"
    ;;
  glowup)
    T1="Selfies feel off and you don't know why. The lighting is fine. The angle is fine. The face is fine. But the photo is dead."
    T2="The reason is almost never aesthetic. It's micro-expression — the half-second your face holds before the shutter."
    T3="GlowUp AI looks at 50 of your photos and tells you which expressions photograph well on you. Not generic advice. Your face only."
    T4="Free trial. ${CTA_URL}"
    ;;
  coldcraft)
    T1="Cold {{profile.lateness.stakeholders.channel}} stops working when you write the same opening line 200 people have already received."
    T2="The fix isn't longer copy. It's a reference to something specific from the recipient's last 30 days that nobody else would notice."
    T3="ColdCraft scans the prospect's posts/repos/papers and writes the opening line for you. You write the rest. Reply rate 4×."
    T4="Free first 5 {{profile.lateness.stakeholders.channel}}s. ${CTA_URL}"
    ;;
  signaturecraft)
    T1="Your {{profile.lateness.stakeholders.channel}} signature says more about you than your job title. Two lines of misalignment and you're 'small biz'."
    T2="Designers charge \$200 for 5-min work because most freelancers don't have a CSS-savvy friend at 11 PM."
    T3="SignatureCraft: pick a layout, type 4 fields, paste the HTML in Gmail. 3 minutes total. Looks like Apple's design team made it."
    T4="\$0 forever for the basic 5. ${CTA_URL}"
    ;;
  deepworkfm)
    T1="Lo-fi beats stopped working for me 6 months in. The novelty wore off and the loop became a distraction."
    T2="Switched to Buddhist ambient + 40Hz binaural. 90-min focus blocks went from 'often' to 'always.'"
    T3="DeepWork.fm is a no-ad, no-account station built for that exact pattern. One click, one tab, one focus block."
    T4="Free. No login. ${CTA_URL}"
    ;;
  clearpdf)
    T1="Reading a 60-page PDF on a phone is not a knowledge activity. It's a survival activity."
    T2="The fix isn't summarization. It's restructuring — sections, takeaways, and the questions the paper actually answers."
    T3="ClearPDF does that in one upload. You skim 4 minutes and know whether to read the whole thing."
    T4="Free 3 PDFs/month. ${CTA_URL}"
    ;;
  anicca-ios)
    T1="Habit apps fail because they confuse you for someone with discipline. You don't need discipline. You need a nudge at the right second."
    T2="Anicca iOS sends one nudge per day, timed to your usual relapse window. No streaks. No gamification."
    T3="It works because it's small. 1 sentence on screen, gone in 2 seconds. The next time you reach for the bad thing, the sentence is in your head."
    T4="\$9.99/mo. Cancel any time. ${CTA_URL}"
    ;;
  *)
    T1="(template missing for $APP_SLUG)"
    T2="(...)"
    T3="(...)"
    T4="${CTA_URL}"
    ;;
esac

THREAD_FILE="$SKILL/state/threads/$TODAY-painpoint-$APP_SLUG.json"
jq -n \
  --arg date "$TODAY" --arg channel "B-painpoint" --arg app "$APP_SLUG" \
  --arg t1 "$T1" --arg t2 "$T2" --arg t3 "$T3" --arg t4 "$T4" \
  --arg cta_url "$CTA_URL" --arg posted_at "$NOW" \
  --arg status "$([ "$DRY_RUN" = "true" ] && echo "dry" || echo "posted")" \
  '$ARGS.named' > "$THREAD_FILE"

echo "  thread → $THREAD_FILE"

if [ "$DRY_RUN" != "true" ] && [ -n "${POSTIZ_API_KEY:-}" ] && [ -n "${POSTIZ_X_INTEGRATION:-}" ]; then
  curl -sS -X POST "https://api.postiz.com/public/v1/posts" \
    -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg integration "$POSTIZ_X_INTEGRATION" \
        --arg t1 "$T1" --arg t2 "$T2" --arg t3 "$T3" --arg t4 "$T4" \
        '{type:"now", date:"'$NOW'", shortLink:false, tags:[], posts:[{integration:{id:$integration}, value:[{content:$t1,image:[]}], settings:{who_can_reply_post:"everyone"}},{integration:{id:$integration}, value:[{content:$t2,image:[]}], settings:{who_can_reply_post:"everyone"}},{integration:{id:$integration}, value:[{content:$t3,image:[]}], settings:{who_can_reply_post:"everyone"}},{integration:{id:$integration}, value:[{content:$t4,image:[]}], settings:{who_can_reply_post:"everyone"}}]}'
    )" 2>&1 | head -3 || echo "  postiz err"
fi

if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🧵 Pain-point thread $TODAY app=$APP_SLUG → $CTA_URL" 2>/dev/null || true
fi

echo "✓ pain-point done"
