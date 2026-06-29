#!/usr/bin/env bash
# run-daily.sh [en] — ONE faceless money short, end-to-end, FRESH every run. $0.
# gen fresh script (DeepSeek, dedup) → free TTS → free b-roll → beat-aligned assemble + captions
# → DRAFT email for approval (until YT/TikTok/IG accounts are wired; then post).
# Cron-able: a brand-new video every single day, forever, from rules (no rotation, no slop).
set -uo pipefail
LANG_CODE="${1:-en}"
DRAFT_ONLY="${DRAFT_ONLY:-1}"   # 1 = email DRAFT only (never post). set 0 once accounts are wired.
export PATH="$HOME/.local/bin:$PATH"
set -a; . "$HOME/.openclaw/.env" 2>/dev/null || true; set +a
export GOG_KEYRING_PASSWORD="${GOG_KEYRING_PASSWORD:-shizen1234}"
SK="$HOME/.claude/skills/faceless-money-factory"; S="$SK/scripts"
OUT="$SK/state/renders"; mkdir -p "$OUT"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

echo "=== [1] fresh script (DeepSeek, dedup, template) ==="
J="$(bash "$S/gen-script.sh" "$LANG_CODE")" || { echo "gen-script failed" >&2; exit 1; }
ID="$(printf '%s' "$J" | python3 -c 'import json,sys;print(json.load(sys.stdin)["id"])')"
TOPIC="$(printf '%s' "$J" | python3 -c 'import json,sys;print(json.load(sys.stdin)["topic"])')"
QUERY="$(printf '%s' "$J" | python3 -c 'import json,sys;print(json.load(sys.stdin)["query"])')"
SCRIPT="$(printf '%s' "$J" | python3 -c 'import json,sys;print(json.load(sys.stdin)["script"])')"
echo "id=$ID topic=$TOPIC query=$QUERY"
printf '%s\n' "$SCRIPT" > "$OUT/$ID.script.txt"

echo "=== [2] TTS (edge-tts, free, consistent voice) ==="
edge-tts --voice "${MONEY_EN_VOICE:-en-US-AndrewNeural}" --rate=+8% --text "$SCRIPT" --write-media "$WORK/voice.mp3" 2>/dev/null
[ -s "$WORK/voice.mp3" ] || { echo "TTS_FAILED" >&2; exit 3; }

echo "=== [3] b-roll (Mixkit free + library fallback) ==="
bash "$S/fetch-broll.sh" "$QUERY" "$WORK/broll" 8

echo "=== [4] assemble (beat-aligned + captions) ==="
bash "$S/assemble.sh" "$WORK/voice.mp3" "$WORK/broll" "$OUT/$ID.mp4" "$LANG_CODE"

# sanity
VDUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT/$ID.mp4" 2>/dev/null || echo 0)
HASA=$(ffprobe -v error -select_streams a -show_entries stream=codec_type -of csv=p=0 "$OUT/$ID.mp4" 2>/dev/null | head -1)
echo "render: dur=${VDUR}s audio=${HASA:-NONE}"
[ "${HASA:-}" = "audio" ] || { echo "RENDER_BAD" >&2; exit 6; }

if [ "$DRAFT_ONLY" = "1" ]; then
  echo "=== [5] DRAFT email (approval gate) ==="
  BODY="$(printf 'Daily faceless money short (AI-generated, $0, DRAFT — not posted).\n\nTopic: %s\nID: %s\nDuration: %ss\n\nScript:\n%s\n' "$TOPIC" "$ID" "$VDUR" "$SCRIPT")"
  gog gmail send --account keiodaisuke@gmail.com --to keiodaisuke@gmail.com \
    --subject "💸 Daily money short DRAFT — $TOPIC ($ID)" \
    --body "$BODY" --attach "$OUT/$ID.mp4" 2>&1 | tail -2
else
  echo "=== [5] POST (accounts wired) — handled by poster step (TODO: yt/tiktok/ig posters) ==="
fi
echo "RUN_DONE id=$ID file=$OUT/$ID.mp4 draft_only=$DRAFT_ONLY"
