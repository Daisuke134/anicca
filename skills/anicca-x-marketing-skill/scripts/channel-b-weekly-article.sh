#!/usr/bin/env bash
# Channel B: Weekly long-form X article (12-tweet thread) — Mon 9 JST.
#
# The article itself is written by Anicca (the LLM running this skill) per SKILL.md.
# This script handles the deterministic surroundings.
#
# Two modes:
#   --print-config       Print this week's pillar / product / postiz integration id / draft file path
#   <draft.json>         Receive Anicca-written 12-tweet article JSON and post via Postiz.

set -euo pipefail

SKILL_DIR="$HOME/.openclaw/skills/anicca-x-marketing-skill"
DATA_DIR="$SKILL_DIR/data"
STATE_DIR="$SKILL_DIR/state"
mkdir -p "$STATE_DIR"

source "$SKILL_DIR/scripts/lib/postiz.sh"

CONFIG="$DATA_DIR/config.json"
HISTORY="$DATA_DIR/posts-history.json"
[ -f "$HISTORY" ] || echo '[]' > "$HISTORY"

# This week's pillar / product (ISO week rotation)
WEEK=$(date +%V)
PILLAR_IDX=$(( (10#$WEEK - 1) % 6 ))
PRODUCT_IDX=$(( (10#$WEEK - 1) % 6 ))
PILLAR=$(jq -r ".pillars[$PILLAR_IDX]" "$CONFIG")
PRODUCT=$(jq -r ".products[$PRODUCT_IDX].slug" "$CONFIG")
INTEGRATION_ID=$(jq -r '.postiz_x_integration_id' "$CONFIG")

TS=$(date +%Y%m%d-%H%M%S)
DRAFT_FILE_DEFAULT="$STATE_DIR/channel-b-${TS}.json"

if [ "${1:-}" = "--print-config" ]; then
  jq -nc \
    --arg pillar "$PILLAR" \
    --arg product "$PRODUCT" \
    --arg integration_id "$INTEGRATION_ID" \
    --arg draft_file "$DRAFT_FILE_DEFAULT" \
    --arg week "$WEEK" \
    '{pillar:$pillar, product:$product, integration_id:$integration_id, draft_file:$draft_file, iso_week:$week}'
  exit 0
fi

DRAFT_FILE="${1:-${DRAFT_FILE:-}}"
if [ -z "$DRAFT_FILE" ] || [ ! -s "$DRAFT_FILE" ]; then
  echo "❌ B FAILED: draft file missing or empty (pillar=$PILLAR product=$PRODUCT)" >&2
  echo "  Anicca must write a JSON array of 12 tweet objects to a file and pass its path here." >&2
  echo "  Expected schema: [{\"content\": \"tweet 1\"}, ..., {\"content\": \"tweet 12 (CTA + github.com/Daisuke134/anicca)\"}]" >&2
  exit 1
fi

RESULT=$(postiz_post_thread "$INTEGRATION_ID" "$DRAFT_FILE" || true)
POST_ID=$(echo "$RESULT" | cut -f1)
STATE=$(echo "$RESULT" | cut -f2)
URL=$(echo "$RESULT" | cut -f3)

if [ -z "$POST_ID" ] || [ "$STATE" != "PUBLISHED" ] || [ -z "$URL" ]; then
  echo "❌ B FAILED: postiz post (id=$POST_ID state=$STATE)"
  exit 1
fi

TMP=$(mktemp)
jq --arg id "$POST_ID" --arg url "$URL" --arg pillar "$PILLAR" --arg product "$PRODUCT" --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '. += [{channel: "B", post_id: $id, url: $url, pillar: $pillar, product: $product, posted_at: $ts}]' \
  "$HISTORY" > "$TMP" && mv "$TMP" "$HISTORY"

echo "✅ B posted: $URL (pillar=$PILLAR product=$PRODUCT)"
