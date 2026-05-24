#!/usr/bin/env bash
# sf-ai-lt-apply.sh — weekly: find an upcoming SF AI LT event (the "guarded" anchor)
# and apply for real (AI Tinkerers SF demo proposal via the proven auto-OTP flow),
# then surface a pattern-② SF trip proposal (Fri-night→Mon-morning, 0 days off) for Dais.
#
# SF trip constraints (memory sf_trip_constraints.md):
#   - Tue morning → Thu night = Tokyo-locked (event must be Fri/Sat/Sun)
#   - pattern ② ideal (leave Fri night → back Mon morning, no day off)
#   - AI LT = scarce anchor; mics fill around it; flights = propose+GO (never auto-book)
#
# Sources: sf.aitinkerers.org (speaker demo slot) primary. Real apply = aitinkerers-apply.sh.
# stdout last line: SF_AI_LT: {...}
set -uo pipefail

SKILL="$HOME/.openclaw/skills/anicca-meetup-talk-applier"
FC=/opt/homebrew/bin/firecrawl
[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
: "${GOG_ACCOUNT:={{profile.contact.personalEmail}}}"; : "${GOG_KEYRING_PASSWORD:=<password>}"
export GOG_ACCOUNT GOG_KEYRING_PASSWORD

# ── 1. Find an UPCOMING SF AI Tinkerers event (the anchor) — /events page only ─
SF_MD=$($FC scrape "https://sf.aitinkerers.org/events" markdown 2>/dev/null)
if echo "$SF_MD" | grep -qiE "No upcoming events"; then
  echo "SF_AI_LT: {\"status\":\"no_upcoming_sf_ai_lt\",\"note\":\"AI Tinkerers SF /events says no upcoming — weekly cron will catch it when announced\"}"
  command -v openclaw &>/dev/null && openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🛩️ SF AI-LT weekly: no upcoming SF AI Tinkerers event yet (anchor not announced). Will auto-apply + propose pattern-② trip when it appears." 2>/dev/null || true
  exit 0
fi
EVENT_URL=$(echo "$SF_MD" | grep -oE 'https://sf\.aitinkerers\.org/p/[a-z0-9-]+' | head -1)
[ -z "$EVENT_URL" ] && { echo "SF_AI_LT: {\"status\":\"no_event_url\"}"; exit 0; }

# ── 1b. Future-date + weekend guard (Tue-Thu = Tokyo-locked, must be Fri/Sat/Sun) ─
EV_MD=$($FC scrape "$EVENT_URL" markdown 2>/dev/null)
DATE_TXT=$(echo "$EV_MD" | grep -oE '(Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,? [A-Z][a-z]+ [0-9]{1,2}[a-z]*,? 2026' | head -1)
CLEAN=$(echo "$DATE_TXT" | sed -E 's/([0-9]+)(st|nd|rd|th)/\1/')
EV_DATE=$(date -j -f "%A, %B %d, %Y" "$CLEAN" +%Y-%m-%d 2>/dev/null || gdate -d "$CLEAN" +%Y-%m-%d 2>/dev/null || echo "")
TODAY=$(date +%F)
if [ -z "$EV_DATE" ] || [ "$EV_DATE" \< "$TODAY" ] || [ "$EV_DATE" = "$TODAY" ]; then
  echo "SF_AI_LT: {\"status\":\"skip_past_or_unparsed\",\"event\":\"$EVENT_URL\",\"date\":\"$EV_DATE\"}"; exit 0
fi
DOW=$(date -j -f "%Y-%m-%d" "$EV_DATE" +%u 2>/dev/null || gdate -d "$EV_DATE" +%u)
if [ "$DOW" = "2" ] || [ "$DOW" = "3" ] || [ "$DOW" = "4" ]; then
  echo "SF_AI_LT: {\"status\":\"skip_tue_thu_tokyo_locked\",\"event\":\"$EVENT_URL\",\"date\":\"$EV_DATE\",\"dow\":\"$DOW\"}"
  command -v openclaw &>/dev/null && openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🛩️ SF AI-LT found ($EV_DATE) but falls Tue-Thu (Tokyo-locked) — skipped. $EVENT_URL" 2>/dev/null || true
  exit 0
fi
echo "  found UPCOMING SF AI LT anchor: $EVENT_URL ($EV_DATE, dow=$DOW)"

# ── 2. Apply for real via the proven auto-OTP flow (sf subdomain supported) ───
APPLY_OUT=$(FORCE=true bash "$SKILL/scripts/aitinkerers-apply.sh" "$EVENT_URL" 2>&1 | tail -8)
echo "$APPLY_OUT"

# ── 3. Surface pattern-② trip proposal to Dais (flights = his GO, never auto-book) ──
DATE_ISO=$(echo "$APPLY_OUT" | grep -oE '2026-[0-9]{2}-[0-9]{2}' | head -1)
if [ -n "$DATE_ISO" ]; then
  command -v openclaw &>/dev/null && openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "🛩️ SF AI-LT applied: $EVENT_URL ($DATE_ISO). Proposing pattern-② trip (Fri-night→Mon-morning, 0 days off) around it + flight est. Reply GO to book. (Tue-Thu Tokyo-locked respected.)" 2>/dev/null || true
fi

echo "SF_AI_LT: {\"status\":\"applied\",\"event\":\"$EVENT_URL\",\"date\":\"$DATE_ISO\"}"
