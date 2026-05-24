#!/usr/bin/env bash
# Stage 6: BANK — DETERMINISTIC SETUP ONLY.
# Writes AGENT_INSTRUCTIONS_BANK.md telling the agent (Claude / cron gpt-5.4-mini)
# to produce 30 Anicca-twisted bank entries IN-CONTEXT. NO LLM subprocess.
#
# Output:
#   $RUN_DIR/AGENT_INSTRUCTIONS_BANK.md
#
# Agent then writes:
#   $RUN_DIR/new_bank.jsonl  (30 lines, one JSON object per line)
#
# After agent writes the bank, run.sh ondemand-finalize installs it into
# $TARGET_DIR/bank_<slug>_<lang>.jsonl.
set -euo pipefail
RUN_DIR="${1:?run_dir required}"
NICHE_SLUG="${2:?niche_slug required}"
LANG_ARG="${3:?lang required}"

CLONE_SPEC="$RUN_DIR/clone_spec.json"
PICKED="$RUN_DIR/picked.json"
[ -f "$CLONE_SPEC" ] || { echo "❌ no clone_spec.json"; exit 2; }
[ -f "$PICKED" ] || { echo "❌ no picked.json"; exit 2; }

# Honor agent skip
SKIP=$(python3 -c "import json; print('1' if json.load(open('$CLONE_SPEC')).get('skip') else '0')")
[ "$SKIP" = "1" ] && { echo "  ⏭ skip per clone_spec"; exit 0; }

PICKED_ID=$(python3 -c "import json; print(json.load(open('$PICKED'))['id'])")
PICKED_HANDLE=$(python3 -c "import json; print(json.load(open('$PICKED'))['author_handle'])")
PICKED_DUR=$(python3 -c "import json; print(json.load(open('$PICKED'))['duration_sec'])")
PICKED_VIEWS=$(python3 -c "import json; print(json.load(open('$PICKED'))['play_count'])")
TRANSCRIPT_PATH="$RUN_DIR/source_${PICKED_ID}.transcript.json"

FORMAT_TYPE=$(python3 -c "import json; print(json.load(open('$CLONE_SPEC')).get('format_type','still-image'))")
HOOK_PATTERN=$(python3 -c "import json; print(json.load(open('$CLONE_SPEC')).get('hook_pattern',''))")
STRUCTURE=$(python3 -c "import json; print(json.load(open('$CLONE_SPEC')).get('structure',''))")
WORD_TARGET=$(python3 -c "print(int(${PICKED_DUR}*2.4))")

echo ""
echo "─── Stage 6: BANK setup (deterministic, agent reasons in-context) ───"
echo "  source: @${PICKED_HANDLE} (${PICKED_VIEWS} views, ${PICKED_DUR}s)"
echo "  format: ${FORMAT_TYPE}"

cat > "$RUN_DIR/AGENT_INSTRUCTIONS_BANK.md" <<EOF
# Agent task — Stage 6 BANK generation (in-context, NO LLM subprocess)

## Source recap
- author: @${PICKED_HANDLE}
- views:  ${PICKED_VIEWS}
- duration: ${PICKED_DUR}s (target ~${WORD_TARGET} words for English)
- mp4: ${RUN_DIR}/source_${PICKED_ID}.mp4
- transcript: ${TRANSCRIPT_PATH}
- frames: ${RUN_DIR}/frames_${PICKED_ID}/

## Spec recap
- format_type: **${FORMAT_TYPE}**
- hook_pattern: ${HOOK_PATTERN}
- structure: ${STRUCTURE}

## Task — write \`${RUN_DIR}/new_bank.jsonl\`

30 lines, ONE JSON object per line. Each line schema:

\`\`\`json
{"id":"clone-NN","formula":"REFRAME|WRONG_WAY|VALIDATION","duration":${PICKED_DUR},"emphasis_words":["..."],"full_text":"...","title":"≤140 chars","captions":["3 1-line CTA candidates + 4 hashtags"],"hook_motion":"2-3s opening prompt (only if production_stack uses i2v hook)","opening_template":"first 1-2 sentences must follow chosen formula"}
\`\`\`

## Hard constraints (enforce per entry)

1. **Anicca twist content**: every entry teaches impermanence / dukkha / breath / mindfulness / aging / letting go in the SAME structural shape as @${PICKED_HANDLE}'s source. Topic = Anicca; delivery = source.

2. **Match source duration**: target ${PICKED_DUR}s (~${WORD_TARGET} words for English).

3. **Open with one of 3 Shalev formulas** (record in \`formula\`, mirror in \`opening_template\`):
   - **REFRAME** — "If you're going to X, X with awareness." (24M views)
   - **WRONG_WAY** — "You X the wrong way, my friend." (23M views)
   - **VALIDATION** — "Keep your X private until it is permanent." (22.4M views)

4. **Use "my friend" 2-4 times** per entry (warm direct address).

5. **End tender, NO CTA in voiceover**. Forbidden: ebook / link / profile / comment / signup / メルマガ / プレゼント. Bio link does conversion silently.

6. **Soft impermanence imagery only**: water / breath / cloud / snow / silence / leaf / petal / river / morning light / mist / wave passing.
   ❌ Forbidden (HeyGen content moderation rejects): anger / fire / thunder / violence / body-violence / locked-jaw / hands-speaking.

7. **\`captions[]\` array**: 3 candidates per entry. Each candidate = 1 single-line CTA (e.g. "Read my book on impermanence in bio 🙏") + 4 hashtags. Match \`lang=${LANG_ARG}\`.

8. **\`hook_motion\`**: only fill if production_stack uses image-to-video (Kling i2v). Otherwise leave empty string.

9. **Variety across 30 entries**:
   - 10 REFRAME, 10 WRONG_WAY, 10 VALIDATION
   - rotate themes: breath, grief, aging, letting go, anger fading, illusion of permanence, the body changing, lost relationships, Anicca itself
   - rotate "you" subjects: you who can't sleep, you who lost someone, you who feel behind, you who are tired, etc.

## Skip option

If after reading the transcript and frames you decide the source is junk
(not actually viral / copyrighted person / not replicable), DO NOT write the
bank. Instead, edit clone_spec.json to set \`{"skip": true, "reason": "..."}\`
and exit.

## After new_bank.jsonl exists

Re-run \`bash run.sh ondemand-finalize "${NICHE_SLUG}" "${LANG_ARG}"\` —
run.sh installs the bank into the spawned skill at
\`~/.openclaw/skills/${NICHE_SLUG}-factory/bank_${NICHE_SLUG}_${LANG_ARG}.jsonl\`
and proceeds to Stage 7 (cron registration, DISABLED).
EOF

echo "  ✅ AGENT_INSTRUCTIONS_BANK.md written"
echo "  📝 Agent must write 30-line $RUN_DIR/new_bank.jsonl"
echo ""
