#!/usr/bin/env bash
# Verify the latest exact8 run and any due both-lane experiment application.
set -euo pipefail

SKILL_DIR="${ARTICLE_SKILL_DIR:-$HOME/profitable-claude/skills/article-writer}"
exec python3 "$SKILL_DIR/scripts/self_improve_control.py" verify \
  --skill-dir "$SKILL_DIR"
