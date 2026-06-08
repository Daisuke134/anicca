#!/usr/bin/env bash
# Runs at Stop event — warns if pending tasks exist + suggests next
TASKLIST_DIR=~/.claude/tasks
PENDING=$(find "$TASKLIST_DIR" -name "*.json" 2>/dev/null | xargs grep -l '"status":"pending"' 2>/dev/null | wc -l | tr -d ' ')
if [ "$PENDING" -gt 0 ]; then
  cat <<EOF
=== STOP BLOCK WARNING (= HARD RULE 0.33) ===
★ Pending tasks = $PENDING ★. Per HARD RULE 0.33, Dais wait = sin.
Continue working autonomously — never stop until ALL tasks done OR
Dais explicit "stop/pause/wait".
EOF
fi
