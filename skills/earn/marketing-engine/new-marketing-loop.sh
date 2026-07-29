#!/usr/bin/env bash
# new-marketing-loop.sh <product> — stand up a marketing loop from a manifest, on the SHARED engine.
# The engine script is capafy-ig-marketing-daily.sh (generic: state paths derive from MKT_INSTANCE,
# per-loop config comes from the manifest via MKT_MANIFEST). This just registers the launchd job.
set -uo pipefail
PRODUCT="${1:?usage: new-marketing-loop.sh <product>}"
ENGINE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MANIFEST="$ENGINE_DIR/manifests/${PRODUCT}.manifest.sh"
[ -f "$MANIFEST" ] || { echo "no manifest: $MANIFEST"; exit 1; }
# shellcheck source=/dev/null
. "$ENGINE_DIR/load_manifest.sh"; me_load_manifest "$PRODUCT" || { echo "manifest invalid"; exit 1; }
HOUR="${MKT_CADENCE_HOUR:-16}"
ENGINE="$ENGINE_DIR/../capafy-marketing/capafy-ig-marketing-daily.sh"
LABEL="ai.anicca.${PRODUCT}-ig-marketing-daily"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG="$HOME/.local/state/life-manager/logs/${PRODUCT}-ig-marketing-daily.log"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>${LABEL}</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>${ENGINE}</string></array>
  <key>EnvironmentVariables</key><dict>
    <key>HOME</key><string>${HOME}</string>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>MKT_MANIFEST</key><string>${PRODUCT}</string>
  </dict>
  <key>StartCalendarInterval</key><dict><key>Hour</key><integer>${HOUR}</integer><key>Minute</key><integer>0</integer></dict>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>${LOG}</string>
  <key>StandardErrorPath</key><string>${LOG}</string>
</dict></plist>
PL
plutil -lint "$PLIST" || { echo "plist invalid"; exit 1; }
launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load "$PLIST" 2>/dev/null || true
echo "registered ${LABEL} (manifest=${PRODUCT}, hour=${HOUR})"
launchctl list | grep "${PRODUCT}-ig-marketing" || echo "WARN not in launchctl list"
