#!/usr/bin/env bash
# Install the read-only five-minute Stripe receipt collector. The restricted
# key stays in the exact macOS Keychain item and is never written to the plist.
set -euo pipefail

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKER="$SCRIPT_DIR/writer_stripe_sync.py"
PYTHON_BIN="$(command -v python3)"
LABEL="ai.anicca.writer-stripe-sync"
DOMAIN="gui/$(id -u)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOG_DIR="$HOME/.openclaw/logs"
KEYCHAIN_SERVICE="ai.anicca.writer-stripe-read"

if [ "$DRY_RUN" = "1" ]; then
  printf 'DRY-RUN: install %s -> %s (StartInterval=300 RunAtLoad=true kickstart=immediate WRITER_STRIPE_READ_KEY=exact-keychain-read GET-only)\n' \
    "$LABEL" "$WORKER"
  exit 0
fi

security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$USER" -w >/dev/null 2>&1 || {
  printf 'missing restricted Stripe read key in Keychain service %s; refusing install\n' \
    "$KEYCHAIN_SERVICE" >&2
  exit 1
}

mkdir -p "$HOME/Library/LaunchAgents" "$LOG_DIR"
TMP_PLIST="$(mktemp "$HOME/Library/LaunchAgents/.$LABEL.XXXXXX")"
trap 'rm -f -- "$TMP_PLIST"' EXIT
cat >"$TMP_PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$PYTHON_BIN</string><string>$WORKER</string></array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>WRITER_STRIPE_KEYCHAIN_SERVICE</key><string>$KEYCHAIN_SERVICE</string>
    <key>WRITER_STRIPE_KEYCHAIN_ACCOUNT</key><string>$USER</string>
  </dict>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$LOG_DIR/writer-stripe-sync.out</string>
  <key>StandardErrorPath</key><string>$LOG_DIR/writer-stripe-sync.err</string>
</dict>
</plist>
PLIST
plutil -lint "$TMP_PLIST" >/dev/null
mv "$TMP_PLIST" "$PLIST"
trap - EXIT

launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "$DOMAIN" "$PLIST"
launchctl enable "$DOMAIN/$LABEL"
launchctl kickstart -k "$DOMAIN/$LABEL"
printf 'installed and kicked %s (%s)\n' "$LABEL" "$PLIST"
