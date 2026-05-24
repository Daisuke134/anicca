#!/usr/bin/env bash
# lib/bgm.sh — Suno V5 BGM gen via apiframe
set -euo pipefail

# bgm_suno <prompt> <output_mp3> <target_duration_sec>
# Generates instrumental, picks first variant, trims to duration with fade in/out
bgm_suno() {
  local prompt="$1"
  local out="$2"
  local duration="${3:-75}"

  [ -z "${APIFRAME_API_KEY:-}" ] && { echo "ERR: APIFRAME_API_KEY not set" >&2; return 3; }

  local payload
  payload=$(jq -nc --arg p "$prompt" \
    '{prompt:$p, model:"V5", make_instrumental:true, title:"SAO BGM", tags:"lofi, ambient, cafe"}')

  local submit task_id
  submit=$(curl -sS -X POST "https://api.apiframe.pro/suno-imagine" \
    -H "Authorization: $APIFRAME_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$payload")
  task_id=$(echo "$submit" | jq -r '.task_id // empty')
  [ -z "$task_id" ] && { echo "ERR: Suno submit failed: $submit" >&2; return 4; }

  # Poll up to 8 min
  local fetch status percentage url i
  for i in $(seq 1 32); do
    sleep 15
    fetch=$(curl -sS -X POST "https://api.apiframe.pro/fetch" \
      -H "Authorization: $APIFRAME_API_KEY" \
      -H "Content-Type: application/json" \
      -d "{\"task_id\":\"$task_id\"}")
    status=$(echo "$fetch" | jq -r '.status // "unknown"')
    percentage=$(echo "$fetch" | jq -r '.percentage // 0')
    echo "  [bgm] poll $i: status=$status percentage=$percentage" >&2
    if [ "$status" = "finished" ]; then
      url=$(echo "$fetch" | jq -r '.songs[0].audio_url')
      [ -z "$url" ] || [ "$url" = "null" ] && { echo "ERR: no audio_url" >&2; return 4; }
      local raw="${out%.mp3}_raw.mp3"
      curl -fsSL -o "$raw" "$url"
      # trim + fade
      local fade_out_start=$((duration - 2))
      ffmpeg -y -loglevel error -i "$raw" -t "$duration" \
        -af "afade=t=in:st=0:d=1.0,afade=t=out:st=${fade_out_start}:d=2.0" \
        "$out"
      rm -f "$raw"
      return 0
    fi
    if [ "$status" = "failed" ]; then
      echo "ERR: Suno task failed: $fetch" >&2
      return 4
    fi
  done
  echo "ERR: Suno timed out after 8min (task_id=$task_id)" >&2
  return 4
}
