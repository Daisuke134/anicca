#!/bin/bash
# PreCompact hook: Log context state before compaction
LOGDIR="/Users/anicca/anicca-project/.cursor/logs"
mkdir -p "$LOGDIR"
echo "$(date '+%Y-%m-%d %H:%M:%S') Pre-compact backup" >> "$LOGDIR/compact-log.txt"
