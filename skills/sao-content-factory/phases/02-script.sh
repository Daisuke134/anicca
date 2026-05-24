#!/usr/bin/env bash
# 02-script.sh — merge the 10-scene JSON into the entity's local copy.
#
# Where do the scenes come from?
#   (a) entity JSON already has a populated `scenes` array → use as-is (manual seed entity)
#   (b) Anicca (the LLM running this skill, per SKILL.md) wrote the 10 scenes to
#       $VERSION_DIR/docs/llm_scenes.json before calling this phase → merge into entity.
#
# This phase is purely deterministic — it does NOT call any LLM API.
set -euo pipefail

[ -n "${ENTITY_JSON:-}" ] && [ -n "${VERSION_DIR:-}" ] || { echo "ENTITY_JSON / VERSION_DIR not set" >&2; exit 2; }

ENTITY_LOCAL="$VERSION_DIR/docs/entity.json"
cp "$ENTITY_JSON" "$ENTITY_LOCAL"

SCENES_LEN=$(jq '.scenes | length' "$ENTITY_LOCAL")
if [ "$SCENES_LEN" -gt 0 ]; then
  echo "phase 02 ok (using pre-populated scenes from entity JSON, n=$SCENES_LEN)"
  exit 0
fi

OUT_JSON="$VERSION_DIR/docs/llm_scenes.json"

if [ ! -s "$OUT_JSON" ]; then
  cat >&2 <<EOF
ERR: entity has no scenes AND $OUT_JSON is missing/empty.

This phase does not call any external LLM. The 10-scene JSON must be written
by the skill's own LLM at run time, BEFORE this phase runs. See SKILL.md.

Expected schema at $OUT_JSON:
  {
    "scenes": [
      { "id": "...", "start": 0.0, "end": 3.0,
        "text_en": "...", "text_ja": "...",
        "bgKind": "image"|"video"|"graphic",
        "bgSrc": "img/<filename>" | "graphics/meta" | "graphics/cta",
        "fit": "cover"|"contain",
        "kenBurns": {"scaleFrom": 1.0, "scaleTo": 1.1}
      },
      ... 10 total, last two id="meta" (55-70s) and id="cta" (70-75s) ...
    ]
  }
EOF
  exit 4
fi

# Validate the file is JSON with a non-empty .scenes array
SCENE_COUNT=$(jq '.scenes | length' "$OUT_JSON" 2>/dev/null || echo 0)
if [ "$SCENE_COUNT" -lt 1 ]; then
  echo "ERR: $OUT_JSON is not valid JSON or has empty .scenes" >&2
  head -c 800 "$OUT_JSON" >&2
  echo >&2
  exit 4
fi

# Merge scenes into the version-local entity
jq --slurpfile new_scenes <(jq '.scenes' "$OUT_JSON") '.scenes = $new_scenes[0]' "$ENTITY_LOCAL" > "$ENTITY_LOCAL.tmp"
mv "$ENTITY_LOCAL.tmp" "$ENTITY_LOCAL"

echo "phase 02 ok (scenes merged from $OUT_JSON, n=$SCENE_COUNT)"
