#!/usr/bin/env bash
# Stage 5: SPAWN — write skill skeleton from Stage 4 PROOF cached assets.
#
# Reads from $RUN_DIR (populated by Stage 4 PROOF):
#   avatar.png         (fal flux generated)
#   voice_id.txt       (ElevenLabs persisted voice — or preview voice)
#   bgm.mp3            (extracted from source)
#   clone_spec.json    (locked params)
#   picked.json        (source provenance)
#
# Writes to ~/.openclaw/skills/<slug>-factory/:
#   SKILL.md
#   SOURCE.json
#   .env
#   assets/avatar.png + bgm.mp3 + voice_id.txt
#   scripts/run.sh (main pipeline)
#   scripts/run-detached.sh (nohup wrapper)
#   scripts/rotate_script.sh (bank rotation)
#   scripts/generate.sh (production_stack-specific render)
#   scripts/post.sh (Postiz multi-integration, copied from yangmun)
#   bank_<slug>_<lang>.jsonl (populated by Stage 6)
#   cron.template.txt
set -euo pipefail
RUN_DIR="${1:?run_dir required}"
NICHE_SLUG="${2:?niche_slug required}"
LANG_ARG="${3:?lang required}"

CVFF_DIR="$HOME/.openclaw/skills/copy-viral-format-factory"
TARGET_DIR="$HOME/.openclaw/skills/${NICHE_SLUG}-factory"
ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a

CLONE_SPEC="$RUN_DIR/clone_spec.json"
PICKED="$RUN_DIR/picked.json"
[ -f "$CLONE_SPEC" ] || { echo "❌ no clone_spec.json"; exit 2; }
[ -f "$PICKED" ] || { echo "❌ no picked.json"; exit 2; }

echo ""
echo "─── Stage 5: SPAWN ───"

# Honor agent skip
SKIP=$(python3 -c "import json; print('1' if json.load(open('$CLONE_SPEC')).get('skip') else '0')")
if [ "$SKIP" = "1" ]; then
  REASON=$(python3 -c "import json; print(json.load(open('$CLONE_SPEC')).get('reason','no reason'))")
  echo "  ⏭ skip — $REASON"
  exit 0
fi

# Versioned target_dir (don't overwrite existing factory of same slug)
if [ -d "$TARGET_DIR" ]; then
  N=2
  while [ -d "${TARGET_DIR}-v${N}" ]; do N=$((N+1)); done
  TARGET_DIR="${TARGET_DIR}-v${N}"
fi
echo "  target: $TARGET_DIR"
mkdir -p "$TARGET_DIR/scripts" "$TARGET_DIR/assets"

NICHE_SLUG_UC=$(echo "$NICHE_SLUG" | tr 'a-z-' 'A-Z_' | tr -cd 'A-Z_0-9')
FORMAT_TYPE=$(python3 -c "import json; print(json.load(open('$CLONE_SPEC')).get('format_type','still-image'))")
PRODUCTION_STACK=$(python3 -c "import json; print(json.load(open('$CLONE_SPEC')).get('production_stack','fal-flux+ffmpeg-still'))")
SOURCE_HANDLE=$(python3 -c "import json; print(json.load(open('$PICKED')).get('author_handle',''))")
SOURCE_ID=$(python3 -c "import json; print(json.load(open('$PICKED')).get('id',''))")

echo "  format=$FORMAT_TYPE  stack=$PRODUCTION_STACK  source=@$SOURCE_HANDLE/$SOURCE_ID"

# ─── Copy cached assets from Stage 4 PROOF ──────────────────────────
[ -f "$RUN_DIR/avatar.png" ] && cp "$RUN_DIR/avatar.png" "$TARGET_DIR/assets/avatar.png"
[ -f "$RUN_DIR/bgm.mp3" ] && cp "$RUN_DIR/bgm.mp3" "$TARGET_DIR/assets/bgm.mp3"
[ -f "$RUN_DIR/voice_id.txt" ] && cp "$RUN_DIR/voice_id.txt" "$TARGET_DIR/assets/voice_id.txt"
VOICE_ID=$(cat "$TARGET_DIR/assets/voice_id.txt" 2>/dev/null || echo "__PROVISION_PENDING__")
echo "  ✅ assets cached: avatar.png / bgm.mp3 / voice_id=$VOICE_ID"

# ─── Validate spawn ─────────────────────────────────────────────────
SPAWN_VALID=1
[ -f "$TARGET_DIR/assets/avatar.png" ] || SPAWN_VALID=0
[ -f "$TARGET_DIR/assets/voice_id.txt" ] && [ -s "$TARGET_DIR/assets/voice_id.txt" ] || SPAWN_VALID=0
echo "  spawn_valid=$SPAWN_VALID"

# ─── .env ───────────────────────────────────────────────────────────
cat > "$TARGET_DIR/.env" <<ENVEOF
# Spawned ${NICHE_SLUG}-factory env (auto-generated $(date -u +%Y-%m-%dT%H:%M:%SZ) by copy-viral-format-factory)
# Source: @${SOURCE_HANDLE}, video ${SOURCE_ID}
# This skill uses its OWN avatar+voice. NEVER falls back to yangmun-monk-factory.

${NICHE_SLUG_UC}_VOICE_ID=${VOICE_ID}
${NICHE_SLUG_UC}_AVATAR_PATH=${TARGET_DIR}/assets/avatar.png
${NICHE_SLUG_UC}_BGM_PATH=${TARGET_DIR}/assets/bgm.mp3
${NICHE_SLUG_UC}_FORMAT_TYPE=${FORMAT_TYPE}
${NICHE_SLUG_UC}_PRODUCTION_STACK=${PRODUCTION_STACK}
${NICHE_SLUG_UC}_SPAWN_VALID=${SPAWN_VALID}
ENVEOF
echo "  ✅ .env"

# ─── SOURCE.json (canonical provenance for future Stage 1 dedup) ────
python3 - <<PY
import json, datetime
src = json.load(open("$PICKED"))
spec = json.load(open("$CLONE_SPEC"))
out = {
  "source_handle": src.get("author_handle",""),
  "source_id": src.get("id",""),
  "source_url": src.get("web_video_url",""),
  "source_play_count": src.get("play_count",0),
  "source_duration_sec": src.get("duration_sec",0),
  "format_type": spec.get("format_type",""),
  "production_stack": spec.get("production_stack",""),
  "spawned_at": datetime.datetime.utcnow().isoformat()+"Z",
  "spawned_by": "copy-viral-format-factory",
  "spawned_run_dir": "$RUN_DIR",
}
json.dump(out, open("$TARGET_DIR/SOURCE.json","w"), indent=2, ensure_ascii=False)
print("  ✅ SOURCE.json")
PY

# ─── SKILL.md ───────────────────────────────────────────────────────
cat > "$TARGET_DIR/SKILL.md" <<EOF
---
name: ${NICHE_SLUG}-factory
description: "Auto-spawned factory for niche '${NICHE_SLUG}' (lang=${LANG_ARG}, format=${FORMAT_TYPE}). Generated by copy-viral-format-factory."
metadata:
  tags: ${NICHE_SLUG}, auto-spawned, ${FORMAT_TYPE}, ${LANG_ARG}
  spawned_at: $(date -u +%Y-%m-%dT%H:%M:%SZ)
  spawned_from: $(basename $RUN_DIR)
  format_type: ${FORMAT_TYPE}
  production_stack: ${PRODUCTION_STACK}
  spawn_valid: ${SPAWN_VALID}
  source: "@${SOURCE_HANDLE}/${SOURCE_ID}"
  requires:
    bins: [ffmpeg, ffprobe, curl, python3, jq]
    env: [${NICHE_SLUG_UC}_VOICE_ID, POSTIZ_API_KEY, ELEVENLABS_API_KEY]
---

# ${NICHE_SLUG}-factory

Auto-spawned by copy-viral-format-factory based on @${SOURCE_HANDLE}'s viral video.

## Run
\`\`\`
bash ~/.openclaw/skills/${NICHE_SLUG}-factory/scripts/run-detached.sh ${LANG_ARG} <slot>
\`\`\`

## Locked assets
- Avatar: \`assets/avatar.png\` (generated once by fal flux from clone_spec.avatar.fal_flux_prompt)
- Voice: ElevenLabs voice_id \`${VOICE_ID}\` (designed once from clone_spec.voice.elevenlabs_voice_description)
- BGM: \`assets/bgm.mp3\` (extracted from @${SOURCE_HANDLE}'s source)

## Pipeline (4 {{profile.lateness.stakeholders.senderType}}s)
1. preflight — env / asset / balance check
2. rotate_script — pull next entry from \`bank_${NICHE_SLUG}_${LANG_ARG}.jsonl\`
3. generate — production_stack-specific render (${PRODUCTION_STACK})
4. post — Postiz multi-integration (TT+IG+YT+FB)

## Source provenance
See \`SOURCE.json\` for the original viral source this factory clones.
DO NOT spawn duplicate factories from @${SOURCE_HANDLE} — the meta-factory
auto-excludes this handle in 01_discover.sh via SOURCE.json glob.
EOF
echo "  ✅ SKILL.md"

# ─── scripts/rotate_script.sh ───────────────────────────────────────
cat > "$TARGET_DIR/scripts/rotate_script.sh" <<'ROTATEEOF'
#!/usr/bin/env bash
# Pull next bank entry, write to state/current_<lang>.json (cyclic round-robin).
set -euo pipefail
LANG_ARG="${1:?lang required}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SLUG=$(basename "$SKILL_DIR" | sed 's/-factory$//')
BANK="$SKILL_DIR/bank_${SLUG}_${LANG_ARG}.jsonl"
STATE_DIR="$HOME/anicca-monk-factory/state"
PTR="$STATE_DIR/${SLUG}_${LANG_ARG}_ptr.txt"
mkdir -p "$STATE_DIR"
[ -f "$BANK" ] || { echo "❌ bank missing: $BANK" >&2; exit 1; }
TOTAL=$(wc -l < "$BANK" | tr -d ' ')
[ "$TOTAL" -eq 0 ] && { echo "❌ bank empty: $BANK" >&2; exit 1; }
IDX=$(cat "$PTR" 2>/dev/null || echo 0)
LINE=$(sed -n "$((IDX % TOTAL + 1))p" "$BANK")
NEXT=$(( (IDX + 1) % TOTAL ))
echo "$NEXT" > "$PTR"
echo "$LINE" > "$STATE_DIR/current_${SLUG}_${LANG_ARG}.json"
echo "  rotated: idx=$((IDX % TOTAL))/$TOTAL → $STATE_DIR/current_${SLUG}_${LANG_ARG}.json" >&2
ROTATEEOF
chmod +x "$TARGET_DIR/scripts/rotate_script.sh"

# ─── scripts/generate.sh — branches by production_stack ─────────────
case "$PRODUCTION_STACK" in
  *still*|*ffmpeg-still*|*flux*ffmpeg-still*)
    # STILL-IMAGE archetype: avatar.png static + ElevenLabs TTS + bgm.mp3 + subtitles
    cat > "$TARGET_DIR/scripts/generate.sh" <<'GENEOF'
#!/usr/bin/env bash
# Still-image generator — avatar.png static + ElevenLabs TTS + BGM + subtitles
set -euo pipefail
LANG_ARG="${1:?lang required}"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SLUG=$(basename "$SKILL_DIR" | sed 's/-factory$//')
SLUG_UC=$(echo "$SLUG" | tr 'a-z-' 'A-Z_' | tr -cd 'A-Z_0-9')

ROOT="$HOME/anicca-monk-factory"
set -a; . "$ROOT/.env"; set +a
[ -f "$SKILL_DIR/.env" ] && { set -a; . "$SKILL_DIR/.env"; set +a; }

VOICE_ID=$(eval echo "\$${SLUG_UC}_VOICE_ID")
AVATAR_PATH=$(eval echo "\$${SLUG_UC}_AVATAR_PATH")
BGM_PATH=$(eval echo "\$${SLUG_UC}_BGM_PATH")

[ -f "$AVATAR_PATH" ] || { echo "❌ avatar.png missing: $AVATAR_PATH"; exit 2; }
[ -n "$VOICE_ID" ] && [ "$VOICE_ID" != "__PROVISION_PENDING__" ] || { echo "❌ voice_id missing"; exit 3; }

CURRENT="$ROOT/state/current_${SLUG}_${LANG_ARG}.json"
[ -f "$CURRENT" ] || { echo "❌ no current_*.json — run rotate_script.sh first"; exit 4; }

TEXT=$(python3 -c "import json; print(json.load(open('$CURRENT')).get('full_text',''))")
[ -n "$TEXT" ] || { echo "❌ bank entry has no full_text"; exit 5; }

TS=$(date -u +%Y%m%d_%H%M%S)
WORK="$ROOT/renders/${SLUG}_${LANG_ARG}_${TS}"
mkdir -p "$WORK"

# 1) ElevenLabs TTS
echo "  🎙 TTS (voice $VOICE_ID)" >&2
TTS_PAYLOAD=$(python3 -c "import json,sys; print(json.dumps({'text': sys.argv[1], 'model_id': 'eleven_multilingual_v2', 'voice_settings': {'stability': 0.5, 'similarity_boost': 0.85, 'style': 0.15, 'speed': 0.95}}))" "$TEXT")
HTTP=$(curl -sS -X POST "https://api.elevenlabs.io/v1/text-to-speech/$VOICE_ID" \
  -H "Content-Type: application/json" -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Accept: audio/mpeg" -d "$TTS_PAYLOAD" -w "%{http_code}" -o "$WORK/audio.mp3")
[ "$HTTP" = "200" ] || { echo "❌ TTS HTTP $HTTP"; exit 6; }

DUR=$(ffprobe -v 0 -of csv=p=0 -show_entries format=duration "$WORK/audio.mp3" | python3 -c "import sys; print(int(float(sys.stdin.read())))")
echo "  ⏱ duration: ${DUR}s" >&2

# 2) Naive SRT (6-word chunks evenly spread)
python3 - "$WORK/subs.srt" "$DUR" "$TEXT" <<'PY'
import sys
out, dur, text = sys.argv[1:4]
dur = int(dur); words = text.split()
chunks = [' '.join(words[i:i+6]) for i in range(0, len(words), 6)] or ['(no narration)']
per = dur / len(chunks)
def ts(s):
    h = int(s // 3600); m = int((s % 3600) // 60); sec = s % 60
    return f'{h:02d}:{m:02d}:{sec:06.3f}'.replace('.', ',')
open(out,'w').write('\n'.join(f'{i+1}\n{ts(i*per)} --> {ts(min((i+1)*per,dur))}\n{c}\n' for i,c in enumerate(chunks)))
PY

# 3) Detect avatar aspect → match in compose
AVA_W=$(ffprobe -v 0 -of csv=p=0 -show_entries stream=width -select_streams v:0 "$AVATAR_PATH")
AVA_H=$(ffprobe -v 0 -of csv=p=0 -show_entries stream=height -select_streams v:0 "$AVATAR_PATH")
OUT_W=${AVA_W:-1280}
OUT_H=${AVA_H:-720}

# 4) ffmpeg compose: avatar still + narration + bgm 5% + subtitles
FINAL="$ROOT/renders/${SLUG}_${LANG_ARG}_${TS}_final.mp4"
BGM_OPT=""
BGM_FILTER=""
if [ -f "$BGM_PATH" ]; then
  BGM_OPT="-stream_loop -1 -t $DUR -i $BGM_PATH"
  BGM_FILTER="[1:a]volume=1.0[narr];[2:a]volume=0.05[bgm];[narr][bgm]amix=inputs=2:duration=longest[a];"
  BGM_MAP='-map [a]'
else
  BGM_FILTER="[1:a]volume=1.0[a];"
  BGM_MAP='-map [a]'
fi
ffmpeg -y \
  -loop 1 -t "$DUR" -i "$AVATAR_PATH" \
  -i "$WORK/audio.mp3" $BGM_OPT \
  -filter_complex "${BGM_FILTER}[0:v]scale=${OUT_W}:${OUT_H}:force_original_aspect_ratio=increase,crop=${OUT_W}:${OUT_H},subtitles='$WORK/subs.srt':force_style='Fontname=Helvetica,Fontsize=46,PrimaryColour=&Hffffff,Outline=3,OutlineColour=&H000000,Alignment=2,MarginV=140'[v]" \
  -map "[v]" $BGM_MAP -c:v libx264 -preset veryfast -crf 22 -c:a aac -b:a 128k -shortest \
  "$FINAL" 2>&1 | tail -3

[ -f "$FINAL" ] || { echo "❌ ffmpeg failed"; exit 7; }
echo "  ✅ render: $FINAL" >&2
echo "$FINAL" > "$ROOT/state/last_render_${SLUG}_${LANG_ARG}.txt"
GENEOF
    chmod +x "$TARGET_DIR/scripts/generate.sh"
    echo "  ✅ scripts/generate.sh (still-image)"
    ;;
  *heygen*|*talking-head*|*avatar-iv*)
    # Talking-head — defer to budget OK (HeyGen credit required)
    cat > "$TARGET_DIR/scripts/generate.sh" <<'GENEOF'
#!/usr/bin/env bash
# HeyGen Avatar IV (talking-head) — DEFERRED until Dais funds HeyGen Premium Credits
echo "🚫 talking-head generator NEEDS_PROVISION: HeyGen Photo Avatar API + ElevenLabs voice"
echo "   See ~/.openclaw/skills/yangmun-monk-factory/scripts/generate_en.sh as reference"
echo "   Required: HeyGen Premium Credits ≥ 2k, valid avatar_look_id"
exit 99
GENEOF
    chmod +x "$TARGET_DIR/scripts/generate.sh"
    echo "  ⏸ scripts/generate.sh (talking-head, NEEDS_PROVISION stub)"
    ;;
  *kling*|*i2v*|*image-to-video*)
    # Image-to-video — defer to budget OK
    cat > "$TARGET_DIR/scripts/generate.sh" <<'GENEOF'
#!/usr/bin/env bash
# fal Kling i2v (image-to-video) — DEFERRED until Dais funds fal credits
echo "🚫 image-to-video generator NEEDS_PROVISION: fal Kling 2.5-turbo i2v"
echo "   See ~/.openclaw/skills/watercolor-monk-factory/scripts/generate.sh as reference"
exit 99
GENEOF
    chmod +x "$TARGET_DIR/scripts/generate.sh"
    echo "  ⏸ scripts/generate.sh (image-to-video, NEEDS_PROVISION stub)"
    ;;
  *)
    cat > "$TARGET_DIR/scripts/generate.sh" <<'GENEOF'
#!/usr/bin/env bash
echo "🚫 unknown production_stack — see clone_spec.json + reimplement"
exit 99
GENEOF
    chmod +x "$TARGET_DIR/scripts/generate.sh"
    echo "  ⏸ scripts/generate.sh (unknown stack, NEEDS_PROVISION stub)"
    ;;
esac

# ─── scripts/post.sh — copy from yangmun, patch slug ────────────────
if [ -f "$HOME/.openclaw/skills/yangmun-monk-factory/scripts/post.sh" ]; then
  cp "$HOME/.openclaw/skills/yangmun-monk-factory/scripts/post.sh" "$TARGET_DIR/scripts/post.sh"
  # Patch state file references to the spawned slug
  sed -i '' \
    -e "s|state/current_\${LANG_ARG}.json|state/current_${NICHE_SLUG}_\${LANG_ARG}.json|g" \
    -e "s|state/current_\$LANG_ARG.json|state/current_${NICHE_SLUG}_\$LANG_ARG.json|g" \
    -e "s|f\"~/anicca-monk-factory/state/current_{os.environ\\['LANG_ARG'\\]}.json\"|f\"~/anicca-monk-factory/state/current_${NICHE_SLUG}_{os.environ['LANG_ARG']}.json\"|g" \
    -e "s|state/current_{os.environ\\['LANG_ARG'\\]}.json|state/current_${NICHE_SLUG}_{os.environ['LANG_ARG']}.json|g" \
    -e "s|state/current_{lang}.json|state/current_${NICHE_SLUG}_{lang}.json|g" \
    "$TARGET_DIR/scripts/post.sh"
  chmod +x "$TARGET_DIR/scripts/post.sh"
  echo "  ✅ scripts/post.sh (Postiz, patched for ${NICHE_SLUG})"
else
  echo "  ⚠ yangmun post.sh not found, skipping post.sh copy"
fi

# ─── scripts/run.sh — main pipeline ─────────────────────────────────
cat > "$TARGET_DIR/scripts/run.sh" <<RUNEOF
#!/usr/bin/env bash
# ${NICHE_SLUG}-factory — main pipeline
set -euo pipefail
LANG_ARG="\${1:?lang required (en|jp)}"
SLOT="\${2:-noon}"
SKILL_DIR="\$(cd "\$(dirname "\$0")/.." && pwd)"
ROOT="\$HOME/anicca-monk-factory"
set -a; . "\$ROOT/.env"; set +a
[ -f "\$SKILL_DIR/.env" ] && { set -a; . "\$SKILL_DIR/.env"; set +a; }

# Spawn validity check
SPAWN_VALID=\$(eval echo \"\\\$${NICHE_SLUG_UC}_SPAWN_VALID\")
if [ "\$SPAWN_VALID" != "1" ]; then
  echo "❌ spawn invalid (avatar/voice missing). Re-run copy-viral-format-factory PROOF {{profile.lateness.stakeholders.senderType}}."
  exit 1
fi

echo "═══ ${NICHE_SLUG}-factory \$LANG_ARG/\$SLOT \$(date -u +%FT%TZ) ═══"

# 1. preflight
[ -n "\${ELEVENLABS_API_KEY:-}" ] || { echo "❌ ELEVENLABS_API_KEY missing"; exit 2; }
[ -n "\${POSTIZ_API_KEY:-}" ] || { echo "❌ POSTIZ_API_KEY missing"; exit 2; }

# 2. rotate
bash "\$SKILL_DIR/scripts/rotate_script.sh" "\$LANG_ARG"

# 3. generate (production_stack-specific)
bash "\$SKILL_DIR/scripts/generate.sh" "\$LANG_ARG"

# 4. post (Postiz multi-integration TT+IG+YT+FB)
LATEST_RENDER=\$(cat "\$ROOT/state/last_render_${NICHE_SLUG}_\$LANG_ARG.txt" 2>/dev/null)
[ -f "\$LATEST_RENDER" ] || { echo "❌ no render produced"; exit 3; }
WARMUP_MODE=\${WARMUP_MODE:-false} bash "\$SKILL_DIR/scripts/post.sh" "\$LANG_ARG" "\$LATEST_RENDER"

echo "═══ ✅ done ${NICHE_SLUG} \$LANG_ARG/\$SLOT ═══"
RUNEOF
chmod +x "$TARGET_DIR/scripts/run.sh"
echo "  ✅ scripts/run.sh"

# ─── scripts/run-detached.sh — nohup wrapper ────────────────────────
cat > "$TARGET_DIR/scripts/run-detached.sh" <<DETEOF
#!/usr/bin/env bash
# Detached wrapper — outlives the cron agent session
LANG_ARG="\${1:?lang required}"
SLOT="\${2:-noon}"
SKILL_DIR="\$(cd "\$(dirname "\$0")/.." && pwd)"
LOG="\$HOME/anicca-monk-factory/state/run_${NICHE_SLUG}_\${LANG_ARG}_\${SLOT}_\$(date -u +%Y%m%d_%H%M%S).log"
mkdir -p "\$(dirname "\$LOG")"
nohup bash "\$SKILL_DIR/scripts/run.sh" "\$LANG_ARG" "\$SLOT" > "\$LOG" 2>&1 &
echo "  detached pid=\$! log=\$LOG"
DETEOF
chmod +x "$TARGET_DIR/scripts/run-detached.sh"
echo "  ✅ scripts/run-detached.sh"

# ─── cron.template.txt — 3 slots/day, DISABLED until Dais enables ───
cat > "$TARGET_DIR/cron.template.txt" <<CRONEOF
# ${NICHE_SLUG}-factory cron template — 3 slots/day, DISABLED
# Dais runs \`openclaw cron enable <id>\` after manual one-shot test passes.

# Morning slot (09:13 JST)
openclaw cron add \\
  --name ${NICHE_SLUG}-${LANG_ARG}-morning \\
  --cron "13 9 * * *" \\
  --tz "Asia/Tokyo" \\
  --session isolated \\
  --agent anicca \\
  --model "openai-codex/gpt-5.4-mini" \\
  --timeout-seconds 600 \\
  --no-deliver \\
  --message "Read ~/.openclaw/skills/${NICHE_SLUG}-factory/SKILL.md, then run: bash ~/.openclaw/skills/${NICHE_SLUG}-factory/scripts/run-detached.sh ${LANG_ARG} morning. Returns immediately."

# Noon slot (12:13 JST)
openclaw cron add \\
  --name ${NICHE_SLUG}-${LANG_ARG}-noon \\
  --cron "13 12 * * *" \\
  --tz "Asia/Tokyo" \\
  --session isolated \\
  --agent anicca \\
  --model "openai-codex/gpt-5.4-mini" \\
  --timeout-seconds 600 \\
  --no-deliver \\
  --message "Read ~/.openclaw/skills/${NICHE_SLUG}-factory/SKILL.md, then run: bash ~/.openclaw/skills/${NICHE_SLUG}-factory/scripts/run-detached.sh ${LANG_ARG} noon. Returns immediately."

# Evening slot (19:27 JST)
openclaw cron add \\
  --name ${NICHE_SLUG}-${LANG_ARG}-evening \\
  --cron "27 19 * * *" \\
  --tz "Asia/Tokyo" \\
  --session isolated \\
  --agent anicca \\
  --model "openai-codex/gpt-5.4-mini" \\
  --timeout-seconds 600 \\
  --no-deliver \\
  --message "Read ~/.openclaw/skills/${NICHE_SLUG}-factory/SKILL.md, then run: bash ~/.openclaw/skills/${NICHE_SLUG}-factory/scripts/run-detached.sh ${LANG_ARG} evening. Returns immediately."
CRONEOF
echo "  ✅ cron.template.txt"

# ─── Bank placeholder (Stage 6 fills this) ──────────────────────────
BANK_PATH="$TARGET_DIR/bank_${NICHE_SLUG}_${LANG_ARG}.jsonl"
touch "$BANK_PATH"
echo "  ✅ bank file (empty until Stage 6): $BANK_PATH"

# ─── Desktop side-by-side ───────────────────────────────────────────
DESKTOP_DIR="$HOME/Desktop/anicca-monk-demo/cvff_spawned/${NICHE_SLUG}"
mkdir -p "$DESKTOP_DIR/originals" "$DESKTOP_DIR/clones"
for mp4 in "$RUN_DIR"/source_*.mp4; do
  [ -f "$mp4" ] || continue
  cp "$mp4" "$DESKTOP_DIR/originals/$(basename "$mp4")" 2>/dev/null || true
done
for mp4 in "$RUN_DIR"/clone_iter*.mp4; do
  [ -f "$mp4" ] || continue
  cp "$mp4" "$DESKTOP_DIR/clones/$(basename "$mp4")" 2>/dev/null || true
done
cp "$CLONE_SPEC" "$DESKTOP_DIR/_clone_spec.json" 2>/dev/null || true
cp "$PICKED" "$DESKTOP_DIR/_picked_source.json" 2>/dev/null || true

echo ""
echo "  ✅ spawn complete: $TARGET_DIR"
echo "  📂 Desktop: $DESKTOP_DIR"
