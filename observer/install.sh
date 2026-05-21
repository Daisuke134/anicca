#!/bin/bash
set -euo pipefail

OBSERVER_DIR="${HOME}/.openclaw/observer"
LAUNCH_AGENTS_DIR="${HOME}/Library/LaunchAgents"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"  # Assumes install.sh is in observer/

echo "=== Installing Passive Observer Agent ==="
echo "Observer Dir: $OBSERVER_DIR"
echo "Project Dir: $PROJECT_DIR"

# Verify required files exist
for file in observer.sh shell-watcher.sh; do
    if [[ ! -f "$PROJECT_DIR/observer/$file" ]]; then
        echo "ERROR: Required file not found: $PROJECT_DIR/observer/$file"
        exit 1
    fi
done

# Create directories
mkdir -p "$OBSERVER_DIR"/{observations,screenshots,logs}

# Copy scripts
cp "$PROJECT_DIR/observer/observer.sh" "$OBSERVER_DIR/"
cp "$PROJECT_DIR/observer/shell-watcher.sh" "$OBSERVER_DIR/"
cp "$PROJECT_DIR/observer/sync-to-vps.sh" "$OBSERVER_DIR/" 2>/dev/null || true
chmod +x "$OBSERVER_DIR"/*.sh

# Create excluded apps list
cat > "$OBSERVER_DIR/excluded_apps.txt" << 'EOF'
1Password
Keychain Access
LastPass
Bitwarden
Dashlane
KeePassXC
EOF

# Generate launchd plist files dynamically (uses $HOME for portability)
mkdir -p "$LAUNCH_AGENTS_DIR"

# Observer plist
cat > "$LAUNCH_AGENTS_DIR/ai.anicca.observer.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.anicca.observer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${OBSERVER_DIR}/observer.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>30</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${OBSERVER_DIR}/logs/observer.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${OBSERVER_DIR}/logs/observer.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
        <key>OBSERVER_DIR</key>
        <string>${OBSERVER_DIR}</string>
    </dict>
</dict>
</plist>
EOF

# Shell watcher plist
cat > "$LAUNCH_AGENTS_DIR/ai.anicca.shell-watcher.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.anicca.shell-watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${OBSERVER_DIR}/shell-watcher.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${OBSERVER_DIR}/logs/shell-watcher.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${OBSERVER_DIR}/logs/shell-watcher.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>${HOME}</string>
        <key>OBSERVER_DIR</key>
        <string>${OBSERVER_DIR}</string>
    </dict>
</dict>
</plist>
EOF

# Sync plist
cat > "$LAUNCH_AGENTS_DIR/ai.anicca.observer-sync.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.anicca.observer-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>${OBSERVER_DIR}/sync-to-vps.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${OBSERVER_DIR}/logs/sync.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>${OBSERVER_DIR}/logs/sync.stderr.log</string>
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

# Load agents
launchctl load "$LAUNCH_AGENTS_DIR/ai.anicca.observer.plist"
launchctl load "$LAUNCH_AGENTS_DIR/ai.anicca.shell-watcher.plist"
launchctl load "$LAUNCH_AGENTS_DIR/ai.anicca.observer-sync.plist" 2>/dev/null || true

echo "=== Installation Complete ==="
launchctl list | grep ai.anicca || echo "No agents running yet"
