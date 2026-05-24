#!/usr/bin/env bash
# Master orchestrator — runs once per day from cron.
# 1. Pick today's theme/seed/genre from prompt-rotation.json (by day of week)
# 2. Receive TITLE from caller (SKILL.md: Anicca generates the title herself — no external LLM API)
# 3. Generate music (apiframe Suno V5)
# 4. Generate cover (FAL FLUX)
# 5. Upload to DistroKid (Playwright)
# 6. Append to state log
# 7. Emit one Slack-ready stdout line (cron delivery posts it)
#
# Exit non-zero on any failure. The last stdout line becomes the Slack message.
#
# Usage:
#   TITLE="Empty Sky" bash 00-run-daily.sh
# or:
#   bash 00-run-daily.sh "Empty Sky"

set -uo pipefail

SK="$HOME/.openclaw/skills/anicca-music-factory"
PROJ_OUT="/Users/anicca/anicca-project/music-factory/anicca-sounds"

# Source env
if [ -f "$HOME/.openclaw/.env" ]; then
  set -a; source "$HOME/.openclaw/.env"; set +a
fi

TODAY=$(date +%Y-%m-%d)
DOW=$(date +%u)   # 1=Mon ... 7=Sun
RELEASE_DATE=$(date -v +7d +%Y-%m-%d 2>/dev/null || date -d "+7 days" +%Y-%m-%d)

# Output dir, never overwrite
BASE="$PROJ_OUT/$TODAY"
mkdir -p "$BASE"
N=1
while [ -d "$BASE/v$N" ]; do N=$((N+1)); done
OUTDIR="$BASE/v$N"
mkdir -p "$OUTDIR"

LOG="$SK/state/daily-log.jsonl"
CATALOG="$SK/state/catalog.json"

emit_fail() {
  local step="$1"
  local msg="$2"
  echo "❌ FAILED at step $step: $msg"
  jq -nc --arg date "$TODAY" --arg step "$step" --arg err "$msg" \
    '{date:$date, status:"failed", step:$step, error:$err, timestamp:now|todate}' >> "$LOG"
  exit 1
}

# === Step 1: pick theme ===
ROT="$SK/config/prompt-rotation.json"
[ -f "$ROT" ] || emit_fail "config" "prompt-rotation.json not found"

THEME=$(jq -r ".day_${DOW}.theme" "$ROT")
SUNO_PROMPT=$(jq -r ".day_${DOW}.suno_prompt" "$ROT")
COVER_PROMPT=$(jq -r ".day_${DOW}.cover_prompt" "$ROT")
TITLE_SEED=$(jq -r ".day_${DOW}.title_seed" "$ROT")
GENRE_PRIMARY=$(jq -r ".day_${DOW}.genre_primary" "$ROT")
GENRE_SECONDARY=$(jq -r ".day_${DOW}.genre_secondary" "$ROT")

[ "$THEME" = "null" ] && emit_fail "config" "no theme for day_$DOW"

# === Step 2: title (provided by caller — Anicca self-generates it per SKILL.md) ===
TITLE="${TITLE:-${1:-}}"
if [ -z "$TITLE" ]; then
  emit_fail "title" "TITLE not provided. SKILL.md instructs Anicca to generate the title herself and pass it via env: TITLE='Some Title' bash 00-run-daily.sh"
fi
# Strip any wrapping quotes / leading 'Title:' just in case
TITLE=$(printf "%s" "$TITLE" | sed -E 's/^[Tt]itle:[[:space:]]*//' | tr -d '"' | tr -d "'" | xargs)
[ -z "$TITLE" ] && emit_fail "title" "TITLE empty after cleanup"

# === Step 3: music ===
bash "$SK/scripts/01-generate-music.sh" "$SUNO_PROMPT" "$TITLE" "$OUTDIR" 2>>"$OUTDIR/.music-err.log" \
  || emit_fail "01-generate-music" "$(tail -3 "$OUTDIR/.music-err.log" 2>/dev/null | tr '\n' ' ')"

# === Step 4: cover ===
bash "$SK/scripts/02-generate-cover.sh" "$COVER_PROMPT" "$OUTDIR" 2>>"$OUTDIR/.cover-err.log" \
  || emit_fail "02-generate-cover" "$(tail -3 "$OUTDIR/.cover-err.log" 2>/dev/null | tr '\n' ' ')"

# === Step 5: write FULL metadata.json (viral replication-ready) ===
DOW_NUM=$(date +%u)
WEEK=$(date +%V)
GEN_AT_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Pull the raw responses from helper scripts
SUNO_TASK_ID=$(jq -r '.task_id // ""' "$OUTDIR/.suno-task.json" 2>/dev/null)
SUNO_AUDIO_URL=$(jq -r '.songs[0].audio_url // ""' "$OUTDIR/.suno-final.json" 2>/dev/null)
SUNO_DURATION=$(jq -r '.songs[0].duration // 0' "$OUTDIR/.suno-final.json" 2>/dev/null)
COVER_URL=$(cat "$OUTDIR/.fal-cover-url.txt" 2>/dev/null || echo "")

jq -nc \
  --arg id          "${TODAY}_v${N}" \
  --arg persona     "Anicca Sounds" \
  --arg title       "$TITLE" \
  --arg theme       "$THEME" \
  --argjson dow     "$DOW_NUM" \
  --argjson week    "$WEEK" \
  --arg suno_prompt "$SUNO_PROMPT" \
  --arg cover_prompt "$COVER_PROMPT" \
  --arg title_seed  "$TITLE_SEED" \
  --arg gp          "$GENRE_PRIMARY" \
  --arg gs          "$GENRE_SECONDARY" \
  --arg suno_task   "$SUNO_TASK_ID" \
  --arg suno_url    "$SUNO_AUDIO_URL" \
  --argjson dur     "${SUNO_DURATION:-0}" \
  --arg cover_url   "$COVER_URL" \
  --arg release     "$RELEASE_DATE" \
  --arg gen_utc     "$GEN_AT_UTC" \
  '{
    id: $id,
    persona: $persona,
    title: $title,
    theme: $theme,
    day_of_week: $dow,
    week_number: $week,
    suno: {
      prompt: $suno_prompt,
      model: "V5",
      tags: "meditation, ambient",
      instrumental: true,
      task_id: $suno_task,
      audio_url_original: $suno_url,
      duration_seconds: $dur
    },
    cover: {
      prompt: $cover_prompt,
      model: "flux-pro-1.1",
      size: "1024x1024",
      image_url_original: $cover_url
    },
    title_gen: {
      seed_words: $title_seed
    },
    distrokid: {
      genre_primary: $gp,
      genre_secondary: $gs,
      release_date: $release,
      stores_excluded: ["Apple Music", "iTunes"],
      ai_disclosure: {composed: true, all_audio: true, lyrics: false},
      uploaded: false,
      albumuuid: null,
      hyperfollow_url: null
    },
    generated_at_utc: $gen_utc,
    performance: {
      stream_count_7d: null,
      stream_count_30d: null,
      viral_score: null,
      double_down_priority: null
    }
  }' > "$OUTDIR/metadata.json"

# === Step 6: upload to DistroKid (positional args: audio cover title genre_jp release_date output_dir) ===
bash "$SK/scripts/04-upload-distrokid-cf.sh" \
  "$OUTDIR/audio.mp3" \
  "$OUTDIR/cover.jpg" \
  "$TITLE" \
  "$GENRE_PRIMARY" \
  "$RELEASE_DATE" \
  "$OUTDIR" \
  2>>"$OUTDIR/.upload-err.log" \
  || emit_fail "04-upload-distrokid" "$(tail -5 "$OUTDIR/.upload-err.log" 2>/dev/null | tr '\n' ' ')"

# === Step 7: update catalog + log ===
ALBUM_UUID=$(jq -r '.albumuuid // ""' "$OUTDIR/upload-receipt.json" 2>/dev/null)
HF_URL=$(jq -r '.hyperfollow_url // ""' "$OUTDIR/upload-receipt.json" 2>/dev/null)

# Atomic catalog append
if [ ! -f "$CATALOG" ]; then
  echo '{"tracks":[]}' > "$CATALOG"
fi
TMP=$(mktemp)
jq --arg title "$TITLE" --arg date "$TODAY" --arg release "$RELEASE_DATE" \
   --arg theme "$THEME" --arg uuid "$ALBUM_UUID" --arg hf "$HF_URL" \
   --arg outdir "$OUTDIR" \
  '.tracks += [{title:$title, generated:$date, release_date:$release, theme:$theme, albumuuid:$uuid, hyperfollow_url:$hf, metadata_path:($outdir+"/metadata.json")}]' \
  "$CATALOG" > "$TMP" && mv "$TMP" "$CATALOG"

CATALOG_COUNT=$(jq '.tracks | length' "$CATALOG")

# Update metadata.json (nested distrokid object)
TMP=$(mktemp)
jq --arg uuid "$ALBUM_UUID" --arg hf "$HF_URL" \
  '.distrokid.uploaded = true | .distrokid.albumuuid = $uuid | .distrokid.hyperfollow_url = $hf' \
  "$OUTDIR/metadata.json" > "$TMP" && mv "$TMP" "$OUTDIR/metadata.json"

jq -nc --arg date "$TODAY" --arg title "$TITLE" --arg release "$RELEASE_DATE" \
       --arg theme "$THEME" --arg uuid "$ALBUM_UUID" --argjson n "$CATALOG_COUNT" \
  '{date:$date, status:"ok", title:$title, theme:$theme, release_date:$release, albumuuid:$uuid, catalog_count:$n, timestamp:now|todate}' \
  >> "$LOG"

# === Final stdout: Slack message ===
echo "📀 Day ${CATALOG_COUNT}: \"${TITLE}\" (${THEME}) → DistroKid (release ${RELEASE_DATE}) | catalog: ${CATALOG_COUNT} tracks | HF: ${HF_URL}"
