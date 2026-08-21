#!/usr/bin/env bash
# Sunday 03:00 evidence-bound language whitelist learning.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="${ARTICLE_SKILL_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
exec python3 "$SKILL_DIR/scripts/learn_whitelist.py" \
  --skill-dir "$SKILL_DIR"
