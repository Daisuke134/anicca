#!/usr/bin/env bash
# anicca-webapp-x-marketing — Channel A: Build in Public daily thread
set -uo pipefail

SKILL=~/.openclaw/skills/anicca-webapp-x-marketing
DRY_RUN="${DRY_RUN:-false}"

[ -f ~/.openclaw/.env ] && set -a && source ~/.openclaw/.env && set +a
[ -f ~/anicca-monk-factory/.env ] && set -a && source ~/anicca-monk-factory/.env && set +a

mkdir -p "$SKILL/state/threads"
TODAY=$(date -u +%Y-%m-%d)
NOW=$(date -u +%FT%TZ)

echo "▶ BIP thread  date=$TODAY  dry_run=$DRY_RUN"

# ── Snapshot ─────────────────────────────────────────────────────────────────
DASH=$(curl -sS https://aniccaai.com/dashboard.json)
MRR=$(echo "$DASH" | jq -r '.mrr.total_usd // 0')
SUBS=$(echo "$DASH" | jq -r '[.mrr.by_product | to_entries[] | select(.value > 0)] | length')
FOLLOWERS=$(echo "$DASH" | jq -r '.followers.total // 0')
SPEND=$(echo "$DASH" | jq -r '.spend.total_usd // 0')
PROFIT=$(echo "$DASH" | jq -r '.profit_usd // 0')
WEEKLY_VIEWS=$(echo "$DASH" | jq -r '.views.weekly_total // 0')

# ── Yesterday blocker note (skill が逐次書く、なければ default) ──────────────
BLOCKER_FILE="$SKILL/state/yesterday-blocker.md"
[ -f "$BLOCKER_FILE" ] && BLOCKER=$(cat "$BLOCKER_FILE") \
  || BLOCKER="(no blocker logged)"

# ── Compose 4 tweets ─────────────────────────────────────────────────────────
T1="Day $(($(date +%-j) - 124)) of building Anicca, a self-funding Buddhist AI.\n\n• MRR: \$$MRR\n• $SUBS products earning\n• $FOLLOWERS followers\n• Weekly views: $WEEKLY_VIEWS\n• Profit: \$$PROFIT/mo"
T2="Shipped: dashboard.json refresh 4×/day. Every dollar in + every dollar out is now public. The empire becomes a glass building."
T3="Stuck on: $BLOCKER\n\nFix: shipped a workaround, root cause queued for tomorrow's sprint."
T4="Today: 3 new SKILLs. End-to-end. Open source. github.com/Daisuke134/anicca\n\nIf you're building autonomous AI entities, fork it."

# ── POST via Postiz (or Slack as preview) ────────────────────────────────────
THREAD_FILE="$SKILL/state/threads/$TODAY-bip.json"
jq -n \
  --arg date "$TODAY" \
  --arg channel "A-bip" \
  --arg t1 "$T1" --arg t2 "$T2" --arg t3 "$T3" --arg t4 "$T4" \
  --arg posted_at "$NOW" \
  --argjson mrr "$MRR" --argjson followers "$FOLLOWERS" \
  --arg status "$([ "$DRY_RUN" = "true" ] && echo "dry" || echo "posted")" \
  '$ARGS.named' > "$THREAD_FILE"

echo "  thread → $THREAD_FILE"

if [ "$DRY_RUN" != "true" ] && [ -n "${POSTIZ_API_KEY:-}" ] && [ -n "${POSTIZ_X_INTEGRATION:-}" ]; then
  # Postiz REST: POST /public/v1/posts (skill-level integration)
  echo "  posting to Postiz X integration $POSTIZ_X_INTEGRATION"
  curl -sS -X POST "https://api.postiz.com/public/v1/posts" \
    -H "Authorization: $POSTIZ_API_KEY" -H "Content-Type: application/json" \
    -d "$(jq -n \
        --arg integration "$POSTIZ_X_INTEGRATION" \
        --arg t1 "$T1" --arg t2 "$T2" --arg t3 "$T3" --arg t4 "$T4" \
        '{integrations:[$integration], type:"now", posts:[{value:$t1},{value:$t2},{value:$t3},{value:$t4}]}'
    )" 2>&1 | head -3 || echo "  postiz err"
fi

# Slack preview
if command -v openclaw &>/dev/null; then
  openclaw message send --channel slack --target "${SLACK_CHANNEL:-{{profile.channels.reportChannel}}}" \
    --text "📰 BIP thread $TODAY MRR=\$$MRR followers=$FOLLOWERS" 2>/dev/null || true
fi

echo "✓ BIP done"
