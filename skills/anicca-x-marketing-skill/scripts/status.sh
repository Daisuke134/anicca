#!/usr/bin/env bash
SKILL_DIR="$HOME/.openclaw/skills/anicca-x-marketing-skill"
echo "=== anicca-x-marketing-skill status ==="
echo "Posts history (last 10):"
jq -r '.[-10:] | .[] | "[\(.channel)] \(.posted_at) \(.url) (pillar=\(.pillar // "-") product=\(.product // "-"))"' "$SKILL_DIR/data/posts-history.json" 2>/dev/null || echo "(no history yet)"
