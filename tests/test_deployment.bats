#!/usr/bin/env bats

setup() {
  REPO_ROOT="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
  TEST_HOME="$(mktemp -d)"
  TEST_BIN="$TEST_HOME/bin"
  mkdir -p "$TEST_BIN"

  export HOME="$TEST_HOME"
  export PATH="$TEST_BIN:/usr/bin:/bin:/opt/homebrew/bin:/usr/local/bin"
}

teardown() {
  rm -rf "$TEST_HOME"
}

_write_ssh_stub() {
  cat > "$TEST_BIN/ssh" <<'EOF'
#!/bin/bash
exit 0
EOF
  chmod +x "$TEST_BIN/ssh"
}

_write_rsync_success_stub() {
  cat > "$TEST_BIN/rsync" <<'EOF'
#!/bin/bash
exit 0
EOF
  chmod +x "$TEST_BIN/rsync"
}

_write_rsync_fail_stub() {
  cat > "$TEST_BIN/rsync" <<'EOF'
#!/bin/bash
exit 7
EOF
  chmod +x "$TEST_BIN/rsync"
}

_write_launchctl_stub() {
  cat > "$TEST_BIN/launchctl" <<'EOF'
#!/bin/bash
echo "$@" >> "${HOME}/launchctl.calls"
if [[ "$1" == "list" ]]; then
  exit 0
fi
exit 0
EOF
  chmod +x "$TEST_BIN/launchctl"
}

@test "deployment scripts exist in observer/" {
  [ -f "$REPO_ROOT/observer/sync-to-vps.sh" ]
  [ -f "$REPO_ROOT/observer/install.sh" ]
  [ -f "$REPO_ROOT/observer/uninstall.sh" ]
}

@test "sync-to-vps.sh uses HOME-based observer dir and strict mode" {
  run grep -F 'set -euo pipefail' "$REPO_ROOT/observer/sync-to-vps.sh"
  [ "$status" -eq 0 ]

  run grep -F 'OBSERVER_DIR="${HOME}/.openclaw/observer"' "$REPO_ROOT/observer/sync-to-vps.sh"
  [ "$status" -eq 0 ]
}

@test "sync-to-vps.sh writes success log when rsync succeeds" {
  mkdir -p "$HOME/.openclaw/observer/observations" "$HOME/.openclaw/observer/logs"
  _write_ssh_stub
  _write_rsync_success_stub

  run "$REPO_ROOT/observer/sync-to-vps.sh"
  [ "$status" -eq 0 ]

  run grep -F "Sync completed successfully" "$HOME/.openclaw/observer/logs/sync.log"
  [ "$status" -eq 0 ]
}

@test "sync-to-vps.sh fails and records rsync exit code when rsync fails" {
  mkdir -p "$HOME/.openclaw/observer/observations" "$HOME/.openclaw/observer/logs"
  _write_ssh_stub
  _write_rsync_fail_stub

  run "$REPO_ROOT/observer/sync-to-vps.sh"
  [ "$status" -eq 1 ]

  # Spec uses $(date ...) in the same echo; $? expands after command substitution and becomes 0.
  run grep -F "Sync FAILED with exit code 0" "$HOME/.openclaw/observer/logs/sync.log"
  [ "$status" -eq 0 ]
}

@test "install.sh creates observer files and launch agents under HOME" {
  _write_launchctl_stub

  run "$REPO_ROOT/observer/install.sh"
  [ "$status" -eq 0 ]

  [ -d "$HOME/.openclaw/observer/observations" ]
  [ -d "$HOME/.openclaw/observer/screenshots" ]
  [ -d "$HOME/.openclaw/observer/logs" ]
  [ -f "$HOME/.openclaw/observer/excluded_apps.txt" ]
  [ -f "$HOME/Library/LaunchAgents/ai.anicca.observer.plist" ]
  [ -f "$HOME/Library/LaunchAgents/ai.anicca.shell-watcher.plist" ]
  [ -f "$HOME/Library/LaunchAgents/ai.anicca.observer-sync.plist" ]
}

@test "install.sh writes portable HOME into generated plist files" {
  _write_launchctl_stub

  run "$REPO_ROOT/observer/install.sh"
  [ "$status" -eq 0 ]

  run grep -F "<string>${HOME}</string>" "$HOME/Library/LaunchAgents/ai.anicca.observer.plist"
  [ "$status" -eq 0 ]

  run grep -F "<string>${HOME}</string>" "$HOME/Library/LaunchAgents/ai.anicca.shell-watcher.plist"
  [ "$status" -eq 0 ]

  run grep -F "<string>${HOME}</string>" "$HOME/Library/LaunchAgents/ai.anicca.observer-sync.plist"
  [ "$status" -eq 0 ]
}

@test "uninstall.sh unloads and removes launch agent plist files only" {
  _write_launchctl_stub

  mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.openclaw/observer"
  touch "$HOME/Library/LaunchAgents/ai.anicca.observer.plist"
  touch "$HOME/Library/LaunchAgents/ai.anicca.shell-watcher.plist"
  touch "$HOME/Library/LaunchAgents/ai.anicca.observer-sync.plist"
  touch "$HOME/.openclaw/observer/preserved.txt"

  run "$REPO_ROOT/observer/uninstall.sh"
  [ "$status" -eq 0 ]

  [ ! -f "$HOME/Library/LaunchAgents/ai.anicca.observer.plist" ]
  [ ! -f "$HOME/Library/LaunchAgents/ai.anicca.shell-watcher.plist" ]
  [ ! -f "$HOME/Library/LaunchAgents/ai.anicca.observer-sync.plist" ]
  [ -f "$HOME/.openclaw/observer/preserved.txt" ]
}
