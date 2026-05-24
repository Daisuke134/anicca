#!/usr/bin/env bash
# gather.sh — deterministic: dump top-5 winning posts per platform (content+metrics)
# to a raw file the model then distills into hot-hooks.json. No LLM here.
set -uo pipefail
source ~/.openclaw/skills/_shared/lib/postiz-analytics.sh
OUT="${1:-/tmp/hot-hooks-raw.json}"
TMP=$(mktemp)
echo '{}' > "$TMP"
for plat in x tt ig yt; do
  data=$(pa_top_content "$plat" 5 2>/dev/null || echo '[]')
  jq --arg p "$plat" --argjson d "${data:-[]}" '.[$p] = $d' "$TMP" > "$TMP.2" && mv "$TMP.2" "$TMP"
done
jq --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" '{generated_at:$ts, by_platform:.}' "$TMP" > "$OUT"
rm -f "$TMP"
echo "gathered → $OUT"
jq -r '.by_platform | to_entries[] | "\(.key): \(.value|length) winners, top score \(.value[0].score // 0)"' "$OUT"
