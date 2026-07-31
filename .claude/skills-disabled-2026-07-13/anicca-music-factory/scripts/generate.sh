#!/usr/bin/env bash
# Anicca Music Factory — generate one track via apiframe.ai (Suno V5)
#
# Usage:
#   APIFRAME_API_KEY=... ./generate.sh <persona-slug> "<prompt>" "<title>" "<tags>"
#
# Persona slugs: anicca-sounds | mujo | bodhi-frequencies
#
# Output: /Users/anicca/anicca-project/music-factory/<persona>/<YYYY-MM-DD>/v<N>/
#         { audio_a.mp3, audio_b.mp3, cover.jpg, metadata.json }
#
# This script NEVER overwrites. Each run creates a new v{N} directory.
# Per project rule: feedback_never_overwrite_files.md

set -euo pipefail

# ── Args ───────────────────────────────────────────────────────────────────
if [ "$#" -lt 4 ]; then
    echo "Usage: $0 <persona-slug> '<prompt>' '<title>' '<tags>'" >&2
    echo "Personas: anicca-sounds | mujo | bodhi-frequencies" >&2
    exit 2
fi

PERSONA_SLUG="$1"
PROMPT="$2"
TITLE="$3"
TAGS="$4"
MODEL="${MODEL:-V5}"

# ── Auth ───────────────────────────────────────────────────────────────────
if [ -z "${APIFRAME_API_KEY:-}" ]; then
    if [ -f "$HOME/.openclaw/.env" ]; then
        # shellcheck disable=SC1090
        source "$HOME/.openclaw/.env"
    fi
fi

if [ -z "${APIFRAME_API_KEY:-}" ]; then
    echo "ERROR: APIFRAME_API_KEY not set. Add to ~/.openclaw/.env" >&2
    exit 3
fi

# ── Persona resolution ─────────────────────────────────────────────────────
case "$PERSONA_SLUG" in
    anicca-sounds)      PERSONA_NAME="Anicca Sounds" ;;
    mujo)               PERSONA_NAME="無常 Mujō" ;;
    bodhi-frequencies)  PERSONA_NAME="Bodhi Frequencies" ;;
    *)
        echo "ERROR: Unknown persona '$PERSONA_SLUG'" >&2
        echo "Allowed: anicca-sounds | mujo | bodhi-frequencies" >&2
        exit 4
        ;;
esac

# ── Output directory (versioned, never overwrite) ──────────────────────────
DATE=$(date +%Y-%m-%d)
BASE="/Users/anicca/anicca-project/music-factory/${PERSONA_SLUG}/${DATE}"
mkdir -p "$BASE"

N=1
while [ -d "$BASE/v$N" ]; do N=$((N+1)); done
OUTDIR="$BASE/v$N"
mkdir -p "$OUTDIR"

echo "→ Output: $OUTDIR"
echo "→ Persona: $PERSONA_NAME"
echo "→ Title:   $TITLE"
echo "→ Tags:    $TAGS"
echo "→ Model:   $MODEL"

# ── Step 1: Submit generation job ──────────────────────────────────────────
echo ""
echo "[1/3] Submitting Suno generation job..."

PAYLOAD=$(cat <<JSON
{
  "prompt": $(printf '%s' "$PROMPT" | jq -Rs .),
  "model": "$MODEL",
  "make_instrumental": true,
  "title": $(printf '%s' "$TITLE" | jq -Rs .),
  "tags": $(printf '%s' "$TAGS" | jq -Rs .)
}
JSON
)

SUBMIT_RESPONSE=$(curl -sS -X POST "https://api.apiframe.pro/suno-imagine" \
    -H "Authorization: $APIFRAME_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

TASK_ID=$(echo "$SUBMIT_RESPONSE" | jq -r '.task_id // empty')

if [ -z "$TASK_ID" ]; then
    echo "ERROR: No task_id in response:" >&2
    echo "$SUBMIT_RESPONSE" >&2
    exit 5
fi

echo "    task_id: $TASK_ID"

# ── Step 2: Poll until finished (max 5 min) ────────────────────────────────
echo ""
echo "[2/3] Polling for completion..."

MAX_ATTEMPTS=20    # 20 * 15s = 5 minutes
ATTEMPT=0
AUDIO_A=""
AUDIO_B=""
IMAGE=""

while [ "$ATTEMPT" -lt "$MAX_ATTEMPTS" ]; do
    sleep 15
    ATTEMPT=$((ATTEMPT+1))

    FETCH=$(curl -sS -X POST "https://api.apiframe.pro/fetch" \
        -H "Authorization: $APIFRAME_API_KEY" \
        -H "Content-Type: application/json" \
        -d "{\"task_id\": \"$TASK_ID\"}")

    STATUS=$(echo "$FETCH" | jq -r '.status // "unknown"')
    echo "    attempt $ATTEMPT/$MAX_ATTEMPTS — status: $STATUS"

    if [ "$STATUS" = "finished" ]; then
        # apiframe returns songs[] array with audio_url + image_url per song
        AUDIO_A=$(echo "$FETCH" | jq -r '.songs[0].audio_url // empty')
        AUDIO_B=$(echo "$FETCH" | jq -r '.songs[1].audio_url // empty')
        IMAGE=$(echo "$FETCH"   | jq -r '.songs[0].image_url // empty')
        DUR_A=$(echo "$FETCH"   | jq -r '.songs[0].duration // 0')
        DUR_B=$(echo "$FETCH"   | jq -r '.songs[1].duration // 0')
        SONG_ID_A=$(echo "$FETCH" | jq -r '.songs[0].song_id // empty')
        SONG_ID_B=$(echo "$FETCH" | jq -r '.songs[1].song_id // empty')
        break
    fi

    if [ "$STATUS" = "failed" ] || [ "$STATUS" = "error" ]; then
        echo "ERROR: Task failed:" >&2
        echo "$FETCH" >&2
        exit 6
    fi
done

if [ -z "$AUDIO_A" ]; then
    echo "ERROR: Timed out after 5 minutes waiting for audio" >&2
    exit 7
fi

# ── Step 3: Download files ─────────────────────────────────────────────────
echo ""
echo "[3/3] Downloading assets..."

curl -sS -L "$AUDIO_A" -o "$OUTDIR/audio_a.mp3"
echo "    saved: audio_a.mp3 ($(du -h "$OUTDIR/audio_a.mp3" | cut -f1))"

if [ -n "$AUDIO_B" ]; then
    curl -sS -L "$AUDIO_B" -o "$OUTDIR/audio_b.mp3"
    echo "    saved: audio_b.mp3 ($(du -h "$OUTDIR/audio_b.mp3" | cut -f1))"
fi

if [ -n "$IMAGE" ]; then
    curl -sS -L "$IMAGE" -o "$OUTDIR/cover.jpg"
    echo "    saved: cover.jpg ($(du -h "$OUTDIR/cover.jpg" | cut -f1))"
fi

# ── Write metadata ─────────────────────────────────────────────────────────
GENERATED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
jq -n \
    --arg persona  "$PERSONA_NAME" \
    --arg slug     "$PERSONA_SLUG" \
    --arg title    "$TITLE" \
    --arg tags     "$TAGS" \
    --arg prompt   "$PROMPT" \
    --arg model    "$MODEL" \
    --arg gen_at   "$GENERATED_AT" \
    --arg taskid   "$TASK_ID" \
    --arg songid_a "${SONG_ID_A:-}" \
    --arg songid_b "${SONG_ID_B:-}" \
    --argjson dur_a "${DUR_A:-0}" \
    --argjson dur_b "${DUR_B:-0}" \
    '{
        persona: $persona,
        persona_slug: $slug,
        title: $title,
        tags: $tags,
        prompt: $prompt,
        model: $model,
        instrumental: true,
        generated_at: $gen_at,
        task_id: $taskid,
        song_id_a: $songid_a,
        song_id_b: $songid_b,
        duration_a_seconds: $dur_a,
        duration_b_seconds: $dur_b,
        distrokid_uploaded: false,
        spotify_url: null,
        isrc: null,
        stream_count_30d: null
    }' > "$OUTDIR/metadata.json"

echo ""
echo "✓ Done. Track ready at:"
echo "  $OUTDIR"
echo ""
echo "Next step (manual): Upload to DistroKid"
echo "  1. https://distrokid.com → New Single"
echo "  2. Artist: $PERSONA_NAME"
echo "  3. Audio:  $OUTDIR/audio_a.mp3"
echo "  4. Cover:  $OUTDIR/cover.jpg"
echo "  5. Title:  $TITLE"
echo "  6. Tag AI-generated: YES"
echo ""
echo "After upload, edit metadata.json:"
echo "  distrokid_uploaded: true"
echo "  spotify_url: <url>"
echo "  isrc: <code>"
