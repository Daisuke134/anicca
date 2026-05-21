# Passive Observer Agent Spec

> Single source of truth for Passive Observer implementation

## Overview

A "top-down learning agent" that passively observes user behavior on Mac, extracts patterns, and proposes automations. Unlike bottom-up skill building, this agent **learns from watching you work** and generates skills automatically.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PASSIVE OBSERVER SYSTEM                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  MAC (Observer)              SYNC                VPS (Processor)            │
│  ┌──────────────┐           ┌────┐              ┌──────────────┐            │
│  │ launchd      │           │    │              │ OpenClaw     │            │
│  │ ├─observer.sh│──30sec───▶│    │              │ cron         │            │
│  │ └─shell-     │           │    │──1hour──────▶│ └─pattern_   │            │
│  │   watcher.sh │           │rsync              │   extractor  │            │
│  └──────────────┘           │    │              └──────────────┘            │
│         │                   │    │                     │                     │
│         ▼                   └────┘                     ▼                     │
│  ~/.openclaw/observer/             ~/.openclaw/workspace/observer/          │
│  └─observations/                   ├─observations/                          │
│    └─2026-02-12.jsonl              ├─observations.db (SQLite)               │
│                                    └─patterns/                              │
│                                      └─2026-02-12.json                      │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Status

| Phase | Component | Status | Tests |
|-------|-----------|--------|-------|
| 1 | URL Sanitizer | ✅ Done | 11 passed |
| 2 | Pattern Extractor | ✅ Done | 15 passed |
| 3 | Shell Scripts | ✅ Done | 6 passed |
| 4 | Deployment | 📋 Ready | - |

**Total Tests: 32 passed** ✅

---

## Phase 1: URL Sanitizer

### Implementation

```python
# observer/url_sanitizer.py
from urllib.parse import urlparse

def sanitize_url(url: str) -> str:
    """
    Sanitize URL to scheme://host only.
    Removes path, query, fragment, and credentials.
    """
    if not url or not isinstance(url, str):
        return ""
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return ""
        if parsed.scheme not in ("http", "https"):
            return ""
        host = parsed.hostname
        if not host:
            return ""
        return f"{parsed.scheme}://{host}"
    except Exception:
        return ""
```

### Tests (11)

- test_removes_path
- test_removes_query_string
- test_removes_fragment
- test_removes_credentials
- test_removes_port
- test_preserves_scheme_http
- test_preserves_scheme_https
- test_rejects_non_http_schemes
- test_rejects_invalid_urls
- test_handles_subdomains
- test_oauth_code_stripped

---

## Phase 2: Pattern Extractor

### Implementation

```python
# observer/pattern_extractor.py

def extract_time_patterns(observations):
    """Find apps used at same time daily. Requires day_coverage >= 4, std_dev <= 20min."""
    
def extract_sequence_patterns(observations):
    """Find A→B→C sequences. Requires len(set(seq)) == 3, frequency >= 3."""
    
def extract_shell_patterns(observations):
    """Find frequent commands. Requires frequency >= 5, ignores [REDACTED]."""
```

### Tests (15)

**Time Patterns:**
- test_requires_4_day_coverage
- test_detects_pattern_with_4_days
- test_rejects_high_time_variance
- test_accepts_low_time_variance

**Sequence Patterns:**
- test_requires_3_unique_apps
- test_detects_unique_3_app_sequence
- test_ignores_non_app_events

**Shell Patterns:**
- test_counts_command_frequency
- test_ignores_redacted_commands
- test_below_threshold_not_detected

**JSON Safety:**
- test_jq_handles_quotes_in_app_name
- test_jq_handles_backslashes
- test_jq_handles_newlines

**End-to-End:**
- test_full_pipeline_with_sample_data
- test_corrupted_json_handled_gracefully

---

## Phase 3: Shell Scripts

### observer.sh

```bash
#!/bin/bash
# Runs every 30s via launchd
# Logs: app_name, timestamp, optional URL (host only)
```

### shell-watcher.sh

```bash
#!/bin/bash
# Runs every 60s via launchd
# Logs: command name only (no args), ignores sensitive patterns
```

### Tests (6)

- test_jq_generates_valid_json_with_special_characters
- test_excluded_apps_are_skipped
- test_url_sanitization_removes_path_and_query
- test_screenshot_state_prevents_duplicates
- test_observer_sh_exists_and_is_executable
- test_shell_watcher_sh_exists_and_is_executable

---

## Phase 4: Deployment

### 4.1 launchd Configuration (Mac)

#### Observer Daemon (30秒ごと)

**File:** `~/Library/LaunchAgents/ai.anicca.observer.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.anicca.observer</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/cbns03/.openclaw/observer/observer.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>30</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/cbns03/.openclaw/observer/logs/observer.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/cbns03/.openclaw/observer/logs/observer.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>/Users/cbns03</string>
        <key>OBSERVER_DIR</key>
        <string>/Users/cbns03/.openclaw/observer</string>
    </dict>
</dict>
</plist>
```

#### Shell Watcher Daemon (60秒ごと)

**File:** `~/Library/LaunchAgents/ai.anicca.shell-watcher.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.anicca.shell-watcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/cbns03/.openclaw/observer/shell-watcher.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>60</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/cbns03/.openclaw/observer/logs/shell-watcher.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/cbns03/.openclaw/observer/logs/shell-watcher.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>/Users/cbns03</string>
        <key>OBSERVER_DIR</key>
        <string>/Users/cbns03/.openclaw/observer</string>
    </dict>
</dict>
</plist>
```

#### Sync Daemon (1時間ごと)

**File:** `~/Library/LaunchAgents/ai.anicca.observer-sync.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>ai.anicca.observer-sync</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>/Users/cbns03/.openclaw/observer/sync-to-vps.sh</string>
    </array>
    <key>StartInterval</key>
    <integer>3600</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/cbns03/.openclaw/observer/logs/sync.stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/cbns03/.openclaw/observer/logs/sync.stderr.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>/Users/cbns03</string>
    </dict>
</dict>
</plist>
```

### 4.2 Sync Script

**File:** `/Users/cbns03/.openclaw/observer/sync-to-vps.sh`

```bash
#!/bin/bash
set -euo pipefail

OBSERVER_DIR="${HOME}/.openclaw/observer"
VPS_USER="anicca"
VPS_HOST="ubuntu-4gb-nbg1-7"  # Tailscale hostname
VPS_PATH="/home/anicca/.openclaw/workspace/observer/observations/"

# Ensure remote directory exists
ssh "${VPS_USER}@${VPS_HOST}" "mkdir -p ${VPS_PATH}" 2>/dev/null || true

# Sync observations to VPS
if rsync -avz --progress \
    "${OBSERVER_DIR}/observations/" \
    "${VPS_USER}@${VPS_HOST}:${VPS_PATH}"; then
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Sync completed successfully" >> "${OBSERVER_DIR}/logs/sync.log"
else
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) Sync FAILED with exit code $?" >> "${OBSERVER_DIR}/logs/sync.log"
    exit 1
fi
```

### 4.3 VPS Cron Job

```json
{
  "name": "passive-observer-pattern-extract",
  "schedule": { "kind": "cron", "expr": "0 9 * * *", "tz": "Asia/Tokyo" },
  "payload": {
    "kind": "agentTurn",
    "message": "Run pattern extraction: cd ~/.openclaw/workspace && python3 observer/pattern_extractor.py",
    "timeoutSeconds": 300
  },
  "sessionTarget": "isolated",
  "delivery": { "mode": "announce", "channel": "slack", "to": "#metrics" }
}
```

### 4.4 Install Script

**File:** `/Users/cbns03/.openclaw/observer/install.sh`

```bash
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
```

### 4.5 Uninstall Script

**File:** `/Users/cbns03/.openclaw/observer/uninstall.sh`

```bash
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
```

### 4.6 Management Commands

```bash
# Start (individual load to avoid zsh glob issues)
launchctl load ~/Library/LaunchAgents/ai.anicca.observer.plist
launchctl load ~/Library/LaunchAgents/ai.anicca.shell-watcher.plist
launchctl load ~/Library/LaunchAgents/ai.anicca.observer-sync.plist

# Stop (individual unload)
launchctl unload ~/Library/LaunchAgents/ai.anicca.observer.plist
launchctl unload ~/Library/LaunchAgents/ai.anicca.shell-watcher.plist
launchctl unload ~/Library/LaunchAgents/ai.anicca.observer-sync.plist

# Status
launchctl list | grep ai.anicca

# Logs
tail -f ~/.openclaw/observer/logs/*.log

# Manual sync
~/.openclaw/observer/sync-to-vps.sh

# Manual pattern extraction (VPS)
cd ~/.openclaw/workspace && python3 observer/pattern_extractor.py
```

---

## Directory Structure

```
Mac (/Users/cbns03/.openclaw/observer/):
├── observer.sh
├── shell-watcher.sh
├── sync-to-vps.sh
├── install.sh
├── uninstall.sh
├── excluded_apps.txt
├── .state.json
├── .shell_state.json
├── observations/
│   └── 2026-02-12.jsonl
└── logs/
    ├── observer.stdout.log
    ├── observer.stderr.log
    ├── shell-watcher.stdout.log
    ├── shell-watcher.stderr.log
    └── sync.log

VPS (~/.openclaw/workspace/observer/):
├── __init__.py
├── url_sanitizer.py
├── pattern_extractor.py
├── observations/
│   └── 2026-02-12.jsonl
├── observations.db
└── patterns/
    └── 2026-02-12.json

Project (/Users/cbns03/Downloads/anicca-project/):
├── observer/
│   ├── __init__.py
│   ├── url_sanitizer.py
│   ├── pattern_extractor.py
│   ├── observer.sh
│   ├── shell-watcher.sh
│   ├── sync-to-vps.sh
│   ├── install.sh         # Generates plist dynamically
│   └── uninstall.sh
├── tests/
│   ├── test_url_sanitizer.py
│   ├── test_pattern_extractor.py
│   └── test_observer.bats
└── specs/
    └── passive-observer-agent.md  ← This file

Note: launchd plist files are generated dynamically by install.sh
      using $HOME for portability across different users.
```

---

## Privacy Design

```
DEFAULT:
  ✅ app_name only
  ✅ timestamp
  ❌ NO url
  ❌ NO shell args
  ❌ NO window title

OPT-IN:
  ⚠️ url_host (sanitized)
  ⚠️ screenshots

NEVER:
  ❌ Full URL
  ❌ Full command
  ❌ Passwords/tokens

EXCLUDED APPS:
  1Password, Keychain Access, LastPass, Bitwarden, etc.
```

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-12 | Initial spec |
| 2.0 | 2026-02-12 | Fixed Critical/High issues from Codex review |
| 3.0 | 2026-02-12 | TDD tests complete, all 32 tests passing |
| 4.0 | 2026-02-12 | Added Deployment phase (launchd, sync, cron) |
| 4.1 | 2026-02-12 | Fixed review issues: dynamic plist generation, zsh glob, sync mkdir -p |

---

**Author:** Anicca  
**Last Updated:** 2026-02-12  
**Status:** Phase 4 ready for implementation
