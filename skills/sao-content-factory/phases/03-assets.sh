#!/usr/bin/env bash
# 03-assets.sh — TTS narration + BGM generation
set -euo pipefail

SKILL_DIR="${SKILL_DIR:-$HOME/.openclaw/skills/sao-content-factory}"
source "$SKILL_DIR/lib/tts.sh"
source "$SKILL_DIR/lib/bgm.sh"

[ -n "${VERSION_DIR:-}" ] || { echo "VERSION_DIR not set" >&2; exit 2; }
ENTITY_LOCAL="$VERSION_DIR/docs/entity.json"

# Build narration text from scenes (text_en concatenated with sentence breaks)
NARRATION=$(jq -r '.scenes | map(.text_en) | join(" ")' "$ENTITY_LOCAL")

# Some scenes may use commas where natural; OpenAI handles fine

VOICE=$(jq -r '.voice.voice // "onyx"' "$ENTITY_LOCAL")
SPEED=$(jq -r '.voice.speed // 0.92' "$ENTITY_LOCAL")
VO_OUT="$VERSION_DIR/vo/vo_en.mp3"

if [ ! -f "$VO_OUT" ]; then
  tts_openai "$NARRATION" "$VO_OUT" "$VOICE" "$SPEED"
fi

# BGM
DURATION=$(jq -r '.duration_sec // 75' "$ENTITY_LOCAL")
BGM_PROMPT=$(jq -r '.bgm.prompt' "$ENTITY_LOCAL")
BGM_OUT="$VERSION_DIR/bgm/bgm.mp3"

if [ ! -f "$BGM_OUT" ]; then
  bgm_suno "$BGM_PROMPT" "$BGM_OUT" "$DURATION"
fi

echo "phase 03 ok (vo=$(basename $VO_OUT) bgm=$(basename $BGM_OUT))"
