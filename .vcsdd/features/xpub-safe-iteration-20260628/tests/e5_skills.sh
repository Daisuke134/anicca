#!/usr/bin/env bash
# E5 — verify both SKILL.md files have grown past their baseline ## heading
# count AND preserved older "MORE LESSONS" headings.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"

assert_grew () {
  local md="$1" baseline_file="$2" name="$3"
  local baseline=$(cat "$baseline_file")
  local now=$(grep -c '^## ' "$md")
  if [ "$now" -le "$baseline" ]; then
    echo "E5 FAIL: $name now=$now <= baseline=$baseline"
    exit 1
  fi
  echo "E5 OK: $name headings grew $baseline -> $now"
}

assert_grew \
  ~/.claude/skills/ai-entity-article-writer/SKILL.md \
  "$HERE/baseline-ai-entity-headings.txt" \
  ai-entity-article-writer

assert_grew \
  ~/.claude/skills/x-article-publisher/SKILL.md \
  "$HERE/baseline-xpub-headings.txt" \
  x-article-publisher

# Preserve old lesson headings (proves we appended, not overwrote)
grep -F "MORE LESSONS (2026-06-22)" ~/.claude/skills/ai-entity-article-writer/SKILL.md > /dev/null
grep -F "MORE LESSONS — Corgi Cafe ground-truth pass (2026-06-27)" ~/.claude/skills/x-article-publisher/SKILL.md > /dev/null
echo "E5 PASS: prior lesson headings preserved in both files"
