#!/usr/bin/env bash
# Stage 3: ANALYZE — DETERMINISTIC SETUP ONLY.
# The agent (Claude / cron gpt-5.4) does the actual reasoning IN-CONTEXT after this script
# exits. NO subprocess LLM calls. The agent IS the LLM.
#
# This script:
#   1. Picks TOP candidate by play_count → writes picked.json
#   2. Extracts frames at 2fps (already done in Stage 2 at 1fps; we keep that)
#   3. Writes AGENT_INSTRUCTIONS.md telling the agent what to write next
#   4. Exits with success
#
# The agent then reads picked.json + transcript + frames, and writes:
#   - clone_spec.json  (the reverse-engineered format spec)
#   - new_bank.jsonl   (30 Anicca-twisted scripts in the same structure)
#
# After agent writes those two files, Stage 4 spawn proceeds normally.
set -euo pipefail
RUN_DIR="${1:?run_dir required}"
NICHE_KW="${2:?niche required}"
LANG_ARG="${3:?lang required}"

ROOT="$HOME/anicca-monk-factory"

echo ""
echo "─── Stage 3: ANALYZE (deterministic setup, agent does reasoning) ───"

CANDIDATES="$RUN_DIR/candidates.json"
[ -f "$CANDIDATES" ] || { echo "  ❌ candidates.json missing"; exit 2; }

# Pick TOP candidate by play_count
python3 - <<PY "$RUN_DIR"
import json, os, sys
run_dir = sys.argv[1]
data = json.load(open(f'{run_dir}/candidates.json'))
candidates = [c for c in data['candidates']
              if os.path.exists(f'{run_dir}/source_{c["id"]}.mp4')]
if not candidates:
    print('  ❌ no downloaded candidates'); sys.exit(2)
picked = sorted(candidates, key=lambda x: x.get('play_count',0), reverse=True)[0]
print(f'  picked: @{picked["author_handle"]} {picked["play_count"]:,} views {picked["duration_sec"]}s — {picked["caption"][:80]}')
json.dump(picked, open(f'{run_dir}/picked.json','w'), ensure_ascii=False, indent=2)
PY

# Write AGENT_INSTRUCTIONS.md (the LLM thinking work the agent must do next)
PICKED_ID=$(python3 -c "import json; print(json.load(open('$RUN_DIR/picked.json'))['id'])")
PICKED_HANDLE=$(python3 -c "import json; print(json.load(open('$RUN_DIR/picked.json'))['author_handle'])")
PICKED_VIEWS=$(python3 -c "import json; print(json.load(open('$RUN_DIR/picked.json'))['play_count'])")
PICKED_DUR=$(python3 -c "import json; print(json.load(open('$RUN_DIR/picked.json'))['duration_sec'])")

cat > "$RUN_DIR/AGENT_INSTRUCTIONS.md" <<EOF
# Agent task — Stage 3 reasoning

Picked viral video:
- author: @${PICKED_HANDLE}
- views: ${PICKED_VIEWS}
- duration: ${PICKED_DUR}s
- mp4: ${RUN_DIR}/source_${PICKED_ID}.mp4
- transcript: ${RUN_DIR}/source_${PICKED_ID}.transcript.json
- frames dir: ${RUN_DIR}/frames_${PICKED_ID}/  (1 fps sample)
- base avatar frame: ${RUN_DIR}/${PICKED_ID}_base.jpg

## Task — Write \`${RUN_DIR}/clone_spec.json\` (clone_spec ONLY, no bank yet)

Read 5 evenly-spaced frames + transcript yourself. Reverse-engineer the format
into JSON with this shape:

\`\`\`json
{
  "format_type": "talking-head | image-to-video | slideshow | still-image | animated-short | podcast-clip | ugc",
  "production_stack": "heygen-avatar-iv | fal-flux+kling-i2v | fal-flux+ffmpeg-still | fal-flux+ffmpeg-slideshow | fal-veo3 | sora",
  "avatar": {
    "description": "...",
    "ethnicity": "...",
    "age_range": "...",
    "clothing": "...",
    "setting": "...",
    "fal_flux_prompt": "ready-to-paste fal flux prompt to recreate this character (different person, same archetype)"
  },
  "voice": {
    "tone": "...",
    "pace": "slow|normal|fast",
    "elevenlabs_voice_description": "voice design prompt for ElevenLabs text-to-voice (>= 100 chars)"
  },
  "visual_style": {
    "color_palette": ["#RRGGBB", "..."],
    "text_overlay_style": "...",
    "motion_pattern": "static|slow-zoom|pan|cuts|...",
    "scene_count": N,
    "scene_avg_duration_sec": X,
    "bgm_type": "none | piano | ambient | original | extracted-from-source"
  },
  "hook_pattern": "first 1-2 sentences",
  "structure": "problem -> insight -> close OR other shape",
  "why_it_worked": "one-line theory",
  "_meta": {
    "source_id": "${PICKED_ID}",
    "source_handle": "${PICKED_HANDLE}",
    "source_play_count": ${PICKED_VIEWS},
    "source_url": "https://www.tiktok.com/@${PICKED_HANDLE}/video/${PICKED_ID}"
  }
}
\`\`\`

If the source video is NOT actually viral or NOT AI-replicable (real celebrity,
copyright-protected, brand-only, etc.), write \`{"skip": true, "reason": "..."}\`
instead. Stage 4+ will detect this and abort.

## After clone_spec.json exists

Run \`bash run.sh ondemand-proof "<niche>" "<lang>"\` → Stage 4 PROOF generates
ONE clone video for Dais visual review. NO bank yet — bank is Stage 6 after 👍.
EOF

echo "  ✅ picked.json written"
echo "  ✅ AGENT_INSTRUCTIONS.md written"
echo "  📝 Agent must write clone_spec.json (NO bank yet — that's Stage 6)"
echo ""
