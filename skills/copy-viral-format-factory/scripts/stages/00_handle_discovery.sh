#!/usr/bin/env bash
# Stage 0: HANDLE DISCOVERY — find new AI viral TT handles via nitter (X mirror) + firecrawl.
# DETERMINISTIC ONLY. No LLM subprocess. Agent (Claude / cron gpt-5.4) reads the scrape
# output AFTERWARDS and decides which @handles are real AI viral creators.
#
# Output:
#   ~/anicca-monk-factory/state/nitter_scrape_YYYYMMDD.txt  (raw concat of nitter pages)
#   ~/anicca-monk-factory/state/seed_ai_handles_candidates.txt  (regex-extracted, agent reviews)
set -euo pipefail
ROOT="$HOME/anicca-monk-factory"
mkdir -p "$ROOT/state"

if ! command -v firecrawl >/dev/null 2>&1; then
  echo "  ⏭ firecrawl not installed, skipping handle discovery"
  exit 0
fi
export FIRECRAWL_API_KEY="${FIRECRAWL_API_KEY:-}"

NITTER_QUERIES=(
  'https://nitter.net/search?f=tweets&q=AI+tiktok+%22M+views%22&since=2026-04-01'
  'https://nitter.net/search?f=tweets&q=%22made+with+veo%22+tiktok&since=2026-04-01'
  'https://nitter.net/search?f=tweets&q=%22made+with+sora%22+tiktok&since=2026-04-01'
  'https://nitter.net/search?f=tweets&q=%22viral+AI%22+tiktok+%40&since=2026-04-15'
  'https://nitter.net/shalevhvs'
  'https://nitter.net/chrisdadiva'
)

OUT_RAW="$ROOT/state/nitter_scrape_$(date +%Y%m%d).txt"
: > "$OUT_RAW"
for url in "${NITTER_QUERIES[@]}"; do
  echo "  scraping $url" >&2
  T=$(firecrawl scrape "$url" markdown 2>/dev/null || true)
  printf '\n=== %s ===\n%s\n' "$url" "${T:0:30000}" >> "$OUT_RAW"
done

# Regex extraction — ONLY tiktok.com/@<handle> URLs (those are guaranteed TikTok handles,
# not X handles). This is deterministic, no AI.
OUT_CANDIDATES="$ROOT/state/seed_ai_handles_candidates.txt"
grep -oE 'tiktok\.com/@[a-zA-Z0-9._]+' "$OUT_RAW" \
  | sed 's|tiktok\.com/@||' \
  | grep -vE '^(yangmun|isshin|anicca|monk_anicca|obou_anicca)' \
  | sort -u > "$OUT_CANDIDATES"

CANDIDATES_COUNT=$(wc -l < "$OUT_CANDIDATES" | tr -d ' ')
echo "  ✅ $CANDIDATES_COUNT TikTok handle candidates → $OUT_CANDIDATES"
echo "  📝 raw scrape → $OUT_RAW"
echo "  ⚠ Agent must review candidates and append verified-AI handles to seed_ai_handles.txt manually."
