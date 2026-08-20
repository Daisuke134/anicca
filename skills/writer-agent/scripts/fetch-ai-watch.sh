#!/usr/bin/env bash
set -uo pipefail
SKILL="$HOME/profitable-claude/skills/article-writer"
OUT_DIR="$SKILL/state/ai-watch-$(TZ=Asia/Tokyo date +%Y-%m-%d)"
mkdir -p "$OUT_DIR"
jq -c '.watched_agents[]' "$SKILL/data/ai-entity-watch.json" | while read -r A; do
  BLOG=$(echo "$A" | jq -r .blog); [ -z "$BLOG" ] && continue
  SLUG=$(echo "$A" | jq -r .name | tr ' [:upper:]' '-[:lower:]')
  OUT="$OUT_DIR/$SLUG.md"; [ -f "$OUT" ] && continue
  timeout 30 /opt/homebrew/bin/firecrawl scrape "$BLOG" markdown > "$OUT" 2>/dev/null || true
done
DIGEST="$OUT_DIR/digest.md"; echo "# AI Watch $(date +%Y-%m-%d)" > "$DIGEST"
for f in "$OUT_DIR"/*.md; do
  [ "$f" = "$DIGEST" ] && continue
  echo "## $(basename "$f" .md)" >> "$DIGEST"; grep -E '^# |^## ' "$f" 2>/dev/null | head -3 >> "$DIGEST"
done
echo "$DIGEST"
