#!/usr/bin/env bash
# Channel A: Daily useful info — 5-tweet thread.
# Cron: 8:20 JST daily.
#
# The thread itself is written by Anicca (the LLM running this skill) per SKILL.md.
# This script handles the deterministic surroundings: pillar/product rotation,
# Postiz posting, history append.
#
# Two modes:
#   --print-config       Print today's pillar / product / postiz integration id / draft file path
#                        and exit. Anicca uses this to know what to write.
#   <draft.json>         Receive Anicca-written 5-tweet thread JSON and post it via Postiz.

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-x-marketing-skill"
DATA_DIR="$SKILL_DIR/data"
STATE_DIR="$SKILL_DIR/state"
mkdir -p "$STATE_DIR"

source "$SKILL_DIR/scripts/lib/postiz.sh"

CONFIG="$DATA_DIR/config.json"
HISTORY="$DATA_DIR/posts-history.json"
[ -f "$HISTORY" ] || echo '[]' > "$HISTORY"

# Today's pillar / product (deterministic rotation)
DOW=$(date +%u)
PILLAR=$(jq -r ".pillars[$(( (DOW - 1) % 6 ))]" "$CONFIG")
DOM=$(date +%d)
PRODUCT=$(jq -r --argjson i "$(( (10#$DOM - 1) % 6 ))" '.products[$i].slug' "$CONFIG")
INTEGRATION_ID=$(jq -r '.postiz_x_integration_id' "$CONFIG")

TS=$(date +%Y%m%d-%H%M%S)
DRAFT_FILE_DEFAULT="$STATE_DIR/channel-a-${TS}.json"

if [ "${1:-}" = "--print-config" ]; then
  jq -nc \
    --arg pillar "$PILLAR" \
    --arg product "$PRODUCT" \
    --arg integration_id "$INTEGRATION_ID" \
    --arg draft_file "$DRAFT_FILE_DEFAULT" \
    '{pillar:$pillar, product:$product, integration_id:$integration_id, draft_file:$draft_file}'
  exit 0
fi

DRAFT_FILE="${1:-${DRAFT_FILE:-}}"
if [ -z "$DRAFT_FILE" ] || [ ! -s "$DRAFT_FILE" ]; then
  echo "❌ A FAILED: draft file missing or empty (pillar=$PILLAR product=$PRODUCT)" >&2
  echo "  Anicca must write a JSON array of 5 tweet objects to a file and pass its path here." >&2
  echo "  Expected schema: [{\"content\": \"tweet 1 (hook with 🧵)\"}, {\"content\": \"tweet 2\"}, ..., {\"content\": \"tweet 5 (CTA)\"}]" >&2
  exit 1
fi

# Post via Postiz
RESULT=$(postiz_post_thread "$INTEGRATION_ID" "$DRAFT_FILE" || true)
POST_ID=$(echo "$RESULT" | cut -f1)
STATE=$(echo "$RESULT" | cut -f2)
URL=$(echo "$RESULT" | cut -f3)

if [ -z "$POST_ID" ] || [ "$STATE" != "PUBLISHED" ] || [ -z "$URL" ]; then
  echo "❌ A FAILED: postiz post (id=$POST_ID state=$STATE)"
  exit 1
fi

# Append to history
TMP=$(mktemp)
jq --arg id "$POST_ID" --arg url "$URL" --arg pillar "$PILLAR" --arg product "$PRODUCT" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '. += [{channel: "A", post_id: $id, url: $url, pillar: $pillar, product: $product, posted_at: $ts}]' \
  "$HISTORY" > "$TMP" && mv "$TMP" "$HISTORY"

echo "✅ A posted: $URL (pillar=$PILLAR product=$PRODUCT)"
