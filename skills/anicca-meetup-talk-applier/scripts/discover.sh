#!/usr/bin/env bash
# anicca-meetup-talk-applier — discover AI meetups in Tokyo (verified working source)
# Output: data/discovered/<source>-<slug>.json
#
# Verified 2026-05-05 working sources:
#   - tokyo.aitinkerers.org/p/tokyo  (UPCOMING section listing) ✅
# TODO sources (need DOM scraper iteration):
#   - lu.ma /discover/tokyo (events lazy-loaded, plain DOM returns 0)
#   - connpass API (blocked by CloudFront 403)
#   - meetup.com (auth required)
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-meetup-talk-applier
CDP_URL="${BU_CDP_URL:-http://127.0.0.1:9223}"
export BU_CDP_URL="$CDP_URL"
mkdir -p "$SKILL/data/discovered"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a

NOW=$(date -u +%FT%TZ)
echo "▶ discover  $NOW"

# Ensure Chrome 9223
if ! curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200; then
  nohup '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
    --remote-debugging-port=9223 \
    --user-data-dir="$HOME/.{{profile.lateness.stakeholders.channel}}-harness-profile" \
    --no-first-run --no-default-{{profile.lateness.stakeholders.channel}}-check \
    > /tmp/chrome-9223.log 2>&1 &
  for i in 1 2 3 4 5 6 7 8; do sleep 1; curl -sS -o /dev/null -w '%{http_code}' "$CDP_URL/json/version" | grep -q 200 && break; done
fi

# ── Source A: AI Tinkerers Tokyo (proven working 2026-05-05) ────────────────
echo "  source: tokyo.aitinkerers.org"
EVENTS_JSON=$({{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('https://tokyo.aitinkerers.org')
wait_for_load(); time.sleep(2)
print(js('''
const links = Array.from(document.querySelectorAll(\"a\"))
  .filter(a => /aitinkerers\\\\.org\\\\/p\\\\//.test(a.href) && /View event/i.test((a.textContent||\"\")));
return JSON.stringify(links.slice(0, 10).map(a => ({href: a.href})));
'''))
" 2>&1 | grep -E '^\[' | tail -1)

if [ -n "$EVENTS_JSON" ] && echo "$EVENTS_JSON" | jq -e 'length > 0' >/dev/null 2>&1; then
  echo "$EVENTS_JSON" | jq -c '.[]' | while read -r e; do
    URL=$(echo "$e" | jq -r '.href')
    SLUG=$(echo "$URL" | sed 's|https://tokyo.aitinkerers.org/p/||')
    OUT="$SKILL/data/discovered/aitinkerers-tokyo-$SLUG.json"

    # Fetch event detail to extract date + title
    DETAIL=$({{profile.lateness.stakeholders.channel}}-harness -c "
import time
goto_url('$URL')
wait_for_load(); time.sleep(2)
print(js('''
const titleEl = document.querySelector(\"title\");
const titleStr = titleEl ? titleEl.textContent : \"\";
const bodyFull = document.body.innerText || \"\";
const body = bodyFull.slice(0, 4000);
const dateMatch = body.match(/(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\\\\s*[A-Z][a-z]+\\\\s+\\\\d+\\\\w*,?\\\\s*\\\\d{4}/);
return JSON.stringify({title: titleStr, date_text: dateMatch ? dateMatch[0] : null, has_demo_form: /Submit Your Demo Proposal|Propose a Demo/i.test(bodyFull)});
'''))
" 2>&1 | grep -E '^\{' | tail -1)

    TITLE=$(echo "$DETAIL" | jq -r '.title // empty' | sed 's/ \[AI Tinkerers - Tokyo\]//' | sed 's/^[^A-Za-z]*//')
    DATE_TEXT=$(echo "$DETAIL" | jq -r '.date_text // empty')
    HAS_DEMO_FORM=$(echo "$DETAIL" | jq -r '.has_demo_form // false')

    # Date parse: "Tuesday, May 26th, 2026" → 2026-05-26
    # macOS date(1) needs %dst dropped. Strip the suffix first.
    CLEANED_DATE=$(echo "$DATE_TEXT" | sed -E 's/([0-9]+)(st|nd|rd|th)/\1/')
    DATE_ISO=$(date -j -f "%A, %B %d, %Y" "$CLEANED_DATE" +%Y-%m-%d 2>/dev/null \
              || gdate -d "$CLEANED_DATE" +%Y-%m-%d 2>/dev/null \
              || echo "")

    jq -n \
      --arg event "$TITLE" \
      --arg url "$URL" \
      --arg city "Tokyo" \
      --arg date "$DATE_ISO" \
      --arg date_text "$DATE_TEXT" \
      --arg source "aitinkerers" \
      --argjson has_demo_form "$HAS_DEMO_FORM" \
      --arg discovered_at "$NOW" \
      --argjson status null \
      '$ARGS.named' > "$OUT"
    echo "  + aitinkerers: $TITLE ($DATE_ISO)"
  done
fi

# ── Source B: connpass — disabled (CloudFront 403). Re-enable via {{profile.lateness.stakeholders.channel}} scraper later.
# ── Source C: lu.ma /discover/tokyo — disabled (lazy-load, plain DOM returns 0).
# ── Source D: meetup.com — disabled (auth required).

echo "✓ discover done. files in $SKILL/data/discovered/"
ls -1 "$SKILL/data/discovered/" 2>/dev/null | head
