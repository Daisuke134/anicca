#!/usr/bin/env bash
# MODE=news — daily AI-policy news pulse via Google News RSS (no API key needed).
set -euo pipefail
SKILL="${SKILL:-$(cd "$(dirname "$0")/.." && pwd)}"
MODE=news
source "$SKILL/scripts/lib/api_clients.sh"
source "$SKILL/scripts/lib/slack_format.sh"

POL_API_DRY=1 pol_news_rss_ai_policy >&2 || true

RESP="$(POL_API_DRY=0 pol_news_rss_ai_policy 2>/dev/null || echo '')"

# Parse RSS — first 3 titles. RSS not JSON, so awk it.
TOP3=$(echo "$RESP" | grep -oE '<title>[^<]+</title>' | sed -n '2,4p' | sed 's|<[^>]*>||g' | tr '\n' '|' | sed 's/|$//' | cut -c1-220)
TITLE_COUNT=$(echo "$RESP" | grep -c '<title>' || echo 0)

slack_post "📰 AI policy news pulse" \
  "items=$TITLE_COUNT top3=\"${TOP3:-rss-empty}\""
