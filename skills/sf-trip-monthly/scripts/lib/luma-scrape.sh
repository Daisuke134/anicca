#!/usr/bin/env bash
# lib/luma-scrape.sh — Lu.ma calendar iterative scroll via camofox
# Usage: bash lib/luma-scrape.sh <slug> <out_dir>
set -euo pipefail

SLUG="${1:-sf}"
OUT_DIR="${2:-/tmp/luma-$SLUG}"
USER_ID="${LUMA_USER_ID:-anicca}"
SESSION_KEY="${LUMA_SESSION_KEY:-default}"
SCROLLS="${LUMA_SCROLLS:-25}"
SCROLL_PX="${LUMA_SCROLL_PX:-2500}"

mkdir -p "$OUT_DIR"

# Camofox must be running
if ! curl -sf http://localhost:9377/health > /dev/null 2>&1; then
  bash ~/.openclaw/skills/camofox-{{profile.lateness.stakeholders.channel}}/scripts/start.sh > /dev/null
fi

TAB_ID=$(curl -sS -X POST http://localhost:9377/tabs \
  -H 'Content-Type: application/json' \
  -d "{\"url\":\"https://lu.ma/${SLUG}\",\"userId\":\"${USER_ID}\",\"sessionKey\":\"${SESSION_KEY}\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('tabId',''))")
[ -z "$TAB_ID" ] && { echo "❌ camofox tab creation failed"; exit 1; }

sleep 3
for i in $(seq 0 "$SCROLLS"); do
  curl -sS "http://localhost:9377/tabs/$TAB_ID/snapshot?userId=${USER_ID}&sessionKey=${SESSION_KEY}" \
    > "$OUT_DIR/snap_$i.json"
  curl -sS -X POST "http://localhost:9377/tabs/$TAB_ID/scroll" \
    -H 'Content-Type: application/json' \
    -d "{\"deltaY\":${SCROLL_PX},\"userId\":\"${USER_ID}\",\"sessionKey\":\"${SESSION_KEY}\"}" > /dev/null
  sleep 1.2
done

curl -sS -X DELETE "http://localhost:9377/tabs/$TAB_ID?userId=${USER_ID}&sessionKey=${SESSION_KEY}" > /dev/null
echo "✅ luma-scrape $SLUG → $OUT_DIR (snaps: $((SCROLLS+1)))"
