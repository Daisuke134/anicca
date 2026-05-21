#!/bin/bash
# SessionStart hook: Display session context
echo "=== Anicca Session Started ==="
echo "Branch: $(git -C /Users/anicca/anicca-project branch --show-current 2>/dev/null || echo 'unknown')"
echo "Date: $(date '+%Y-%m-%d %H:%M JST')"
echo "Rules: $(ls /Users/anicca/anicca-project/.claude/rules/*.md 2>/dev/null | wc -l | tr -d ' ') files"
