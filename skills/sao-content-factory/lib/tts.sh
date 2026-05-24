#!/usr/bin/env bash
# lib/tts.sh — OpenAI TTS wrapper
set -euo pipefail

# tts_openai <text> <output_mp3> [voice] [speed]
# voice: alloy|echo|fable|onyx|nova|shimmer (default onyx for narration)
# speed: 0.25-4.0 (default 0.92 for natural pacing)
tts_openai() {
  local text="$1"
  local out="$2"
  local voice="${3:-onyx}"
  local speed="${4:-0.92}"

  [ -z "${OPENAI_API_KEY:-}" ] && { echo "ERR: OPENAI_API_KEY not set" >&2; return 3; }

  curl -sS https://api.openai.com/v1/audio/speech \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -cn --arg t "$text" --arg v "$voice" --argjson s "$speed" \
        '{model:"tts-1-hd", voice:$v, input:$t, speed:$s}')" \
    --output "$out" \
    || { echo "ERR: OpenAI TTS failed" >&2; return 4; }

  [ -s "$out" ] || { echo "ERR: TTS produced empty file" >&2; return 4; }

  # Verify it's actually audio (not an error JSON)
  if ! file "$out" | grep -qE 'MPEG|Audio'; then
    echo "ERR: TTS output is not audio:" >&2
    head -c 500 "$out" >&2
    return 4
  fi
}
