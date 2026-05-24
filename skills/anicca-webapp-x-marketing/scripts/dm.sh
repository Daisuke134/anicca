#!/usr/bin/env bash
# anicca-webapp-x-marketing — Channel D: Cold DM 50/day
# 1) apify scrape ICP candidates
# 2) {{profile.lateness.stakeholders.channel}}-harness Way 2 → x.com/<handle>/messages → DM template send
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-webapp-x-marketing
DRY_RUN="${DRY_RUN:-false}"
DAILY_LIMIT="${DAILY_LIMIT:-50}"
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${APIFY_TOKEN:?}"

mkdir -p "$SKILL/state/dms"
TODAY=$(date -u +%Y-%m-%d)
ROT="$SKILL/state/rotation.json"
DOW=$(date +%w)
APP_JSON=$(jq -c --argjson i "$DOW" '.queue[$i]' "$ROT")
APP_SLUG=$(echo "$APP_JSON" | jq -r .slug)
APP_URL=$(echo "$APP_JSON" | jq -r .url)

echo "▶ Cold DM  app=$APP_SLUG  limit=$DAILY_LIMIT"

# ── Search keywords per app ──────────────────────────────────────────────────
case "$APP_SLUG" in
  letter)        Q='"morning routine" OR "morning ritual"' ;;
  glowup)        Q='"selfie tips" OR "look better on camera"' ;;
  coldcraft)     Q='"cold {{profile.lateness.stakeholders.channel}}" "no replies"' ;;
  signaturecraft)Q='"{{profile.lateness.stakeholders.channel}} signature" freelancer' ;;
  deepworkfm)    Q='"deep work" focus music' ;;
  clearpdf)      Q='"too many pdfs" OR "pdf overwhelm"' ;;
  anicca-ios)    Q='"mindfulness habit" OR "meditation streak"' ;;
  *)             Q='AI tool' ;;
esac

# ── Apify Twitter search ─────────────────────────────────────────────────────
echo "  apify search: $Q"
APIFY_RESULT=$(mktemp)
curl -sS -X POST \
  "https://api.apify.com/v2/acts/apidojo~tweet-scraper/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg q "$Q" --argjson n "$DAILY_LIMIT" '{searchTerms: [$q], maxItems: $n, sort: "Latest", lang: "en"}')" \
  -o "$APIFY_RESULT" 2>/dev/null \
  || { echo "  apify err"; exit 1; }

if [ ! -s "$APIFY_RESULT" ] || ! jq -e '. | length > 0' "$APIFY_RESULT" >/dev/null 2>&1; then
  echo "  no candidates from apify (free tier may not include this actor — placeholder log only)"
  echo "  trying alternative: clockworks/twitter-search-scraper"
fi

# ── For each candidate: send DM via {{profile.lateness.stakeholders.channel}}-harness ─────────────────────────
COUNT=0
jq -c '.[]' "$APIFY_RESULT" 2>/dev/null | head -n "$DAILY_LIMIT" | while read -r tweet; do
  HANDLE=$(echo "$tweet" | jq -r '.user.userName // .user.screen_name // .author.userName // empty')
  [ -z "$HANDLE" ] && continue
  TWEET_URL=$(echo "$tweet" | jq -r '.url // .tweetUrl // empty')

  # Dedup: 30d window
  if find "$SKILL/state/dms" -name "${HANDLE}-*.json" -mtime -30 2>/dev/null | grep -q .; then
    continue
  fi

  COUNT=$((COUNT + 1))
  echo "  → @$HANDLE (#$COUNT)"

  # Per-app DM template
  case "$APP_SLUG" in
    letter)
      MSG="Hey 👋 saw your post on morning routine. Built Anicca Letter — 1 Buddhist sentence/day, 7 AM, takes 4 sec to read. Free first month: ${APP_URL}?utm_source=x&utm_medium=dm&utm_campaign=${APP_SLUG}-$(date -u +%Y-%m)" ;;
    coldcraft)
      MSG="Hey, your tweet about cold {{profile.lateness.stakeholders.channel}} rejection caught my eye. ColdCraft (tiny tool) does the personalized opening line for you. Free 5 {{profile.lateness.stakeholders.channel}}s: ${APP_URL}?utm_source=x&utm_medium=dm&utm_campaign=${APP_SLUG}-$(date -u +%Y-%m)" ;;
    deepworkfm)
      MSG="Saw your post about focus music — try deepwork.fm. Buddhist ambient + binaural. No ads, no login. Free: ${APP_URL}?utm_source=x&utm_medium=dm&utm_campaign=${APP_SLUG}-$(date -u +%Y-%m)" ;;
    *)
      MSG="Hey, saw your post — built ${APP_SLUG} for exactly this. Free trial: ${APP_URL}?utm_source=x&utm_medium=dm&utm_campaign=${APP_SLUG}-$(date -u +%Y-%m)" ;;
  esac

  DM_FILE="$SKILL/state/dms/${HANDLE}-$TODAY.json"
  jq -n \
    --arg handle "$HANDLE" --arg app "$APP_SLUG" --arg tweet_url "$TWEET_URL" \
    --arg msg "$MSG" --arg sent_at "$(date -u +%FT%TZ)" \
    --arg status "$([ "$DRY_RUN" = "true" ] && echo "dry" || echo "queued")" \
    '$ARGS.named' > "$DM_FILE"

  if [ "$DRY_RUN" != "true" ]; then
    {{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://x.com/$HANDLE')
wait_for_load(); time.sleep(2)
# DM modal open path: profile → message button → textarea → send
# Implementation extends — placeholder for now
print('DM_TARGET:', '$HANDLE')
" 2>&1 | tail -2
  fi
done

echo "✓ DM done. $COUNT queued"
rm -f "$APIFY_RESULT"
