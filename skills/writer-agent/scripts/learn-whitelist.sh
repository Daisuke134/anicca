#!/usr/bin/env bash
# Sunday 03:00 evidence-bound language whitelist learning.
set -euo pipefail

SKILL_DIR="${ARTICLE_SKILL_DIR:-$HOME/profitable-claude/skills/writer-agent}"
exec python3 "$SKILL_DIR/scripts/learn_whitelist.py" \
  --skill-dir "$SKILL_DIR"
