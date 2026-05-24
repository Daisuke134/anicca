#!/usr/bin/env bash
# Generate one Suno V5 instrumental track via apiframe.ai
#
# Usage: 01-generate-music.sh <prompt> <title> <output_dir>
# Outputs: $output_dir/audio.mp3 (single track, A variation)
#          $output_dir/.suno-task.json (task_id + raw response)

set -euo pipefail

PROMPT="$1"
TITLE="$2"
OUTDIR="$3"

[ -z "${APIFRAME_API_KEY:-}" ] && { echo "ERR: APIFRAME_API_KEY not set" >&2; exit 3; }

mkdir -p "$OUTDIR"

PAYLOAD=$(jq -nc \
  --arg p "$PROMPT" \
  --arg t "$TITLE" \
  '{prompt:$p, model:"V5", make_instrumental:true, title:$t, tags:"meditation, ambient"}')

# apiframe/Suno は時々サーバ側で "Internal Error, Please try again later"
# を返す（一過性）。submit+poll を1試行とし、failed/error/timeout/no-task_id
# は新タスクを再投入して最大 ATTEMPTS 回リトライ（指数的 backoff）。
# 生成段のみ・DistroKid 前なので重複リリース等のリスクは無い。
ATTEMPTS=3

for attempt in $(seq 1 "$ATTEMPTS"); do
  # Submit (fresh task each attempt)
  SUBMIT=$(curl -sS -X POST "https://api.apiframe.pro/suno-imagine" \
    -H "Authorization: $APIFRAME_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" || true)

  TASK_ID=$(echo "$SUBMIT" | jq -r '.task_id // empty' 2>/dev/null || true)
  if [ -z "$TASK_ID" ]; then
    echo "WARN: attempt ${attempt}/${ATTEMPTS}: no task_id from submit" >&2
    echo "$SUBMIT" >&2
  else
    echo "$SUBMIT" > "$OUTDIR/.suno-task.json"

    # Poll up to 5 min for this task
    RESULT="timeout"
    for i in $(seq 1 20); do
      sleep 15
      FETCH=$(curl -sS -X POST "https://api.apiframe.pro/fetch" \
        -H "Authorization: $APIFRAME_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"task_id\":\"$TASK_ID\"}" || true)

      STATUS=$(echo "$FETCH" | jq -r '.status // "unknown"' 2>/dev/null || echo unknown)
      if [ "$STATUS" = "finished" ]; then
        AUDIO=$(echo "$FETCH" | jq -r '.songs[0].audio_url // empty')
        if [ -z "$AUDIO" ]; then
          echo "ERR: no audio_url in finished response" >&2; echo "$FETCH" >&2; exit 5
        fi
        curl -sS -L "$AUDIO" -o "$OUTDIR/audio.mp3"
        DURATION=$(echo "$FETCH" | jq -r '.songs[0].duration // 0')
        echo "$FETCH" > "$OUTDIR/.suno-final.json"
        echo "OK audio.mp3 duration=${DURATION}s (attempt ${attempt}/${ATTEMPTS})"
        exit 0
      fi
      if [ "$STATUS" = "failed" ] || [ "$STATUS" = "error" ]; then
        echo "WARN: attempt ${attempt}/${ATTEMPTS}: Suno task ${TASK_ID} failed" >&2
        echo "$FETCH" >&2
        RESULT="failed"
        break
      fi
    done
    [ "$RESULT" = "timeout" ] && echo "WARN: attempt ${attempt}/${ATTEMPTS}: timed out after 5 min" >&2
  fi

  if [ "$attempt" -lt "$ATTEMPTS" ]; then
    BACKOFF=$((attempt * 30))
    echo "Retrying Suno in ${BACKOFF}s ..." >&2
    sleep "$BACKOFF"
  fi
done

echo "ERR: Suno task failed after ${ATTEMPTS} attempts (apiframe/Suno upstream error)" >&2
exit 6
