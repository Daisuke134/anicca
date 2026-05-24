#!/usr/bin/env bash
# 03b-transcribe.sh — NO-OP (deprecated).
#
# Word-level captions are now generated in phase 03 directly from ElevenLabs
# `/with-timestamps` alignment — audio + captions come from the SAME
# synthesis so they are guaranteed in sync.
#
# This phase exists only as a backwards-compatible passthrough; it verifies
# captions_en.json / captions_ja.json were already written by phase 03.

set -euo pipefail

[ -n "${VERSION_DIR:-}" ] || { echo "VERSION_DIR not set" >&2; exit 2; }

for lang in en ja; do
  f="$VERSION_DIR/docs/captions_${lang}.json"
  if [ -f "$f" ]; then
    n=$(jq 'length' "$f" 2>/dev/null || echo 0)
    echo "  → captions_${lang}.json present ($n words)"
  else
    echo "  → captions_${lang}.json missing (phase 03 was supposed to write it)" >&2
    # Don't fail — empty captions just means renderer falls back to scene text
    echo "[]" > "$f"
  fi
done

echo "phase 03b ok (no-op; captions generated in phase 03 from ElevenLabs alignment)"
exit 0

# ──────── legacy code below (kept for reference, never executes) ────────
[ -n "${OPENAI_API_KEY:-}" ] || { echo "ERR: OPENAI_API_KEY not set" >&2; exit 3; }

transcribe_lang() {
  local lang="$1"
  local mp3="$VERSION_DIR/vo/vo_${lang}.mp3"
  local out="$VERSION_DIR/docs/captions_${lang}.json"

  if [ ! -f "$mp3" ]; then
    echo "  → no vo_${lang}.mp3, skip" >&2
    return 0
  fi

  echo "  → whisper transcribe $lang ..."

  # verbose_json + word timestamps. Whisper API caps at 25MB; our VO is well under.
  local resp_path
  resp_path=$(mktemp)
  curl -sS https://api.openai.com/v1/audio/transcriptions \
    -H "Authorization: Bearer $OPENAI_API_KEY" \
    -F "file=@${mp3}" \
    -F "model=whisper-1" \
    -F "language=${lang}" \
    -F "response_format=verbose_json" \
    -F "timestamp_granularities[]=word" \
    -o "$resp_path"

  if ! jq -e '.words' "$resp_path" >/dev/null 2>&1; then
    echo "WARN: whisper response missing .words (likely OpenAI quota) — writing empty captions, slide-level text will fall back" >&2
    head -c 400 "$resp_path" >&2
    echo >&2
    rm -f "$resp_path"
    echo '[]' > "$out"
    return 0
  fi

  # Convert Whisper words → @remotion/captions Caption[]
  jq '[
    .words[]
    | {
        text: (.word + " "),
        startMs: ((.start * 1000) | floor),
        endMs: ((.end * 1000) | floor),
        timestampMs: (((.start + .end) / 2 * 1000) | floor),
        confidence: null
      }
  ]' "$resp_path" > "$out"

  rm -f "$resp_path"

  local count
  count=$(jq 'length' "$out")
  echo "  → $count words transcribed → $out"
}

transcribe_lang en
transcribe_lang ja || true   # JA is optional

echo "phase 03b ok"
