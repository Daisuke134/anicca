#!/bin/bash
set -euo pipefail

LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"

echo "=== Uninstalling Passive Observer Agent ==="

launchctl unload "$LAUNCH_AGENTS_DIR/ai.anicca.observer.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/ai.anicca.shell-watcher.plist" 2>/dev/null || true
launchctl unload "$LAUNCH_AGENTS_DIR/ai.anicca.observer-sync.plist" 2>/dev/null || true

rm -f "$LAUNCH_AGENTS_DIR/ai.anicca.observer.plist"
rm -f "$LAUNCH_AGENTS_DIR/ai.anicca.shell-watcher.plist"
rm -f "$LAUNCH_AGENTS_DIR/ai.anicca.observer-sync.plist"

echo "=== Uninstall Complete ==="
echo "Data preserved at ~/.openclaw/observer/"
