#!/usr/bin/env bash
# Stop camofox server (and its child Firefox)
set -euo pipefail
pkill -f "node.*camofox-{{profile.lateness.stakeholders.channel}}" 2>&1 | head -3 || true
pkill -f "Camoufox.app" 2>&1 | head -3 || true
sleep 1
if curl -sSf http://localhost:9377/health > /dev/null 2>&1; then
  echo "WARNING: camofox still running"
  exit 1
fi
echo "camofox stopped"
