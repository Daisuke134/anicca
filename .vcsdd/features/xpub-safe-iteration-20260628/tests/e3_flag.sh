#!/usr/bin/env bash
# E3 — verify --no-cleanup-duplicates flag exists in publish_md_to_x.py --help
set -eu
HELP=$(python3 ~/.claude/skills/x-article-publisher/scripts/publish_md_to_x.py --help 2>&1)
echo "$HELP" | grep -F -- "--no-cleanup-duplicates" > /dev/null
echo "E3 PASS: --no-cleanup-duplicates flag listed in --help"
