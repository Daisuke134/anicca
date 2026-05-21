#!/bin/bash
# PostToolUse hook (Bash): Play sound on long-running command completion
if [ "${CLAUDE_TOOL_DURATION:-0}" -gt 30000 ]; then
  afplay /System/Library/Sounds/Glass.aiff 2>/dev/null &
fi
