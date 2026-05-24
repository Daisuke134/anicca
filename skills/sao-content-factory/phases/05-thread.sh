#!/usr/bin/env bash
# 05-thread.sh — assemble the X thread + social caption.
#
# Where do the tweets come from?
#   (a) entity JSON has `x_thread_seeds` with >=8 strings → use as-is.
#   (b) Anicca (the LLM running this skill, per SKILL.md) wrote 12 tweets to
#       $VERSION_DIR/docs/llm_thread.json before calling this phase → ingest.
#
# This phase is purely deterministic — it does NOT call any LLM API.
set -euo pipefail

[ -n "${VERSION_DIR:-}" ] || { echo "VERSION_DIR not set" >&2; exit 2; }
ENTITY_LOCAL="$VERSION_DIR/docs/entity.json"

THREAD_OUT="$VERSION_DIR/docs/x_thread.json"
SOCIAL_OUT="$VERSION_DIR/docs/social_caption.txt"

# Path (a): entity has pre-populated seeds
SEED_LEN=$(jq '.x_thread_seeds | length' "$ENTITY_LOCAL")
if [ "$SEED_LEN" -ge 8 ]; then
  jq '.x_thread_seeds | map({content: .})' "$ENTITY_LOCAL" > "$THREAD_OUT"
  jq -r '.social_caption_seed' "$ENTITY_LOCAL" > "$SOCIAL_OUT"
  echo "phase 05 ok (thread=$(jq 'length' "$THREAD_OUT") tweets from entity seeds, caption ready)"
  exit 0
fi

# Path (b): Anicca-generated tweet list
LLM_THREAD="$VERSION_DIR/docs/llm_thread.json"

if [ ! -s "$LLM_THREAD" ]; then
  cat >&2 <<EOF
ERR: entity has fewer than 8 x_thread_seeds AND $LLM_THREAD is missing/empty.

This phase does not call any external LLM. The 12-tweet array must be written
by the skill's own LLM at run time, BEFORE this phase runs. See SKILL.md.

Expected at $LLM_THREAD:
  ["tweet 1 (hook with AI/SAO name)", "tweet 2", ..., "tweet 12 (ends with anicca.ai and 'We are not alone.')"]
EOF
  exit 4
fi

TWEET_COUNT=$(jq 'length' "$LLM_THREAD" 2>/dev/null || echo 0)
if [ "$TWEET_COUNT" -lt 8 ]; then
  echo "ERR: $LLM_THREAD is not a JSON array of 8+ strings (got length=$TWEET_COUNT)" >&2
  head -c 800 "$LLM_THREAD" >&2
  echo >&2
  exit 4
fi

jq 'map({content: .})' "$LLM_THREAD" > "$THREAD_OUT"
jq -r '.social_caption_seed' "$ENTITY_LOCAL" > "$SOCIAL_OUT"

echo "phase 05 ok (thread=$TWEET_COUNT tweets from $LLM_THREAD, caption ready)"
