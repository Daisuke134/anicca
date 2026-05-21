#!/bin/bash
# PreToolUse hook (Edit|Write): Check file size before edit
FILE_PATH="${CLAUDE_FILE_PATH:-}"
if [ -n "$FILE_PATH" ] && [ -f "$FILE_PATH" ]; then
  LINES=$(wc -l < "$FILE_PATH")
  if [ "$LINES" -gt 800 ]; then
    echo "WARNING: $FILE_PATH has $LINES lines (>800). Consider splitting."
  fi
fi
