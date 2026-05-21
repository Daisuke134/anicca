#!/usr/bin/env bash
# OpenClaw Control UI 用 SSH トンネルを LaunchAgent で常時維持する。
# autossh で切断時に自動再接続。ログイン時・ネット復帰時に起動。
#
# 用法: ./scripts/openclaw-vps/install-tunnel-launchagent.sh
# アンインストール: launchctl unload ~/Library/LaunchAgents/ai.anicca.openclaw-tunnel.plist

set -e
VPS_HOST="${OPENCLAW_VPS_HOST:-anicca@46.225.70.241}"
LOCAL_PORT=18789
REMOTE_PORT=18789
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PLIST_LABEL="ai.anicca.openclaw-tunnel"
PLIST_PATH="${LAUNCH_AGENTS_DIR}/${PLIST_LABEL}.plist"
LOG_DIR="${HOME}/.openclaw/tunnel-logs"
AUTOSSH_BIN="$(which autossh 2>/dev/null || echo /opt/homebrew/bin/autossh)"

if [[ ! -x "$AUTOSSH_BIN" ]]; then
  echo "Installing autossh..."
  brew install autossh
  AUTOSSH_BIN="$(which autossh)"
fi

mkdir -p "$LOG_DIR"

# -M 0: no monitoring port; use ServerAliveInterval instead
# ServerAliveInterval=30 ServerAliveCountMax=3: keep connection alive, reconnect after ~90s idle failure
# ExitOnForwardFailure=yes: fail fast if port forward fails
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>${PLIST_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>${AUTOSSH_BIN}</string>
        <string>-M</string>
        <string>0</string>
        <string>-o</string>
        <string>ServerAliveInterval=30</string>
        <string>-o</string>
        <string>ServerAliveCountMax=3</string>
        <string>-o</string>
        <string>ExitOnForwardFailure=yes</string>
        <string>-N</string>
        <string>-L</string>
        <string>${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}</string>
        <string>${VPS_HOST}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <dict>
        <key>NetworkState</key>
        <true/>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/tunnel.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/tunnel.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
    </dict>
</dict>
</plist>
EOF

# Unload if already loaded
launchctl unload "$PLIST_PATH" 2>/dev/null || true
# Load and start
launchctl load "$PLIST_PATH"

echo "Installed and started. Tunnel: localhost:${LOCAL_PORT} -> ${VPS_HOST}:${REMOTE_PORT}"
echo "Control UI: http://127.0.0.1:${LOCAL_PORT}/"
echo "Logs: ${LOG_DIR}/"
echo "Stop: launchctl unload $PLIST_PATH"
