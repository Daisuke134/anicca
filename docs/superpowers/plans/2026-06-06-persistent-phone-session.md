# Persistent Phone Session Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Each Moshi tab on Dais's iPhone spawns a new persistent independent Claude (Opus 4.7) session on Mac Mini; sessions survive Wi-Fi/LTE roaming and screen sleep; N concurrent tabs coexist; `phone ls`/`phone <name>` reattach old ones.

**Architecture:** mosh (UDP transport, roams) → per-tap unique tmux session `phone-<unix_ts>` → zshrc auto-`exec`s `claude --session-id $(uuidgen) --model claude-opus-4-7 --max-budget-usd 10`. No shared state between tabs. tmux already handles detach/persist. mosh already handles roaming.

**Tech Stack:** zsh, tmux, mosh 1.4.0 (already installed), Claude Code CLI, bats-core (will install for TDD on shell scripts), launchd (for cleanup cron).

**Pre-flight verified 2026-06-06**:
- `/opt/homebrew/bin/mosh` present (1.4.0_38) — no install needed
- `/Users/anicca/bin/phone` present (702B) — rewrite target
- `~/.zshrc` has the legacy tmux interceptor — must be removed
- `bats` not installed — Task 1 installs it

**HARD RULE #0 exception**: Files touched live in `/Users/anicca/bin/`, `~/.zshrc`, `/etc/ssh/sshd_config`. These cannot live in a git worktree (they are user-level dotfiles + system config). Per CLAUDE.md HARD RULE #0 exception (runtime canonical store), edits go to main paths directly; the rest of the SDD flow (TDD + verify + review + finish + push) still applies.

---

## File Structure

| File | Role |
|---|---|
| `/Users/anicca/bin/phone` | Multi-mode CLI: `phone` (no arg) = new session; `phone ls` = list; `phone <name>` = attach; `phone kill <name>` = terminate; `phone last` = attach most-recent. Exports `MOSHI_PHONE=1` before tmux. |
| `/Users/anicca/bin/phone-cleanup` | Daily cron, kills `phone-*` tmux sessions with no attached client AND idle > 7 days. |
| `/Users/anicca/bin/phone-status` | Convenience: prints active session count + each session's age. |
| `~/.zshrc` | Block 1 (DELETE): old tmux interceptor. Block 2 (ADD): MOSHI_PHONE detection + `exec claude ...`. Idempotent via `CLAUDE_AUTOSTARTED` guard. |
| `/etc/ssh/sshd_config` | `ClientAliveInterval 60`, `ClientAliveCountMax 5`. Defense in depth even with mosh. |
| `~/Library/LaunchAgents/local.phone-cleanup.plist` | Schedules `phone-cleanup` daily at 04:00 JST. |
| `~/anicca-project/tests/phone/test_phone.bats` | bats-core test file. Asserts each phone subcommand. |
| `~/anicca-project/tests/phone/helpers.bash` | Test helpers (tmux mock, fake date). |
| `~/anicca-project/docs/superpowers/specs/2026-06-05-anicca-v32-evolution-design.md` | Source spec (no edits in this plan, but referenced from commits). |

---

## Backups before edits

| Original | Backup path |
|---|---|
| `/Users/anicca/bin/phone` | `/Users/anicca/bin/phone.bak-pre-v32-20260606` |
| `~/.zshrc` | `~/.zshrc.bak-pre-v32-20260606` |
| `/etc/ssh/sshd_config` | `/etc/ssh/sshd_config.bak-pre-v32-20260606` (sudo) |

---

## Tasks

### Task 1: Install bats-core for shell-script TDD

**Files:**
- No file edits; tool install only.

- [ ] **Step 1: Install bats-core via brew**

Run: `brew install bats-core`
Expected: brew finishes, exit 0.

- [ ] **Step 2: Verify install**

Run: `bats --version`
Expected: `Bats 1.x.x`

- [ ] **Step 3: Commit nothing (no file changes; this is environment setup, recorded in plan log only)**

No commit. Move on.

---

### Task 2: Backup current state of files we are about to touch

**Files:**
- Modify (backup): `/Users/anicca/bin/phone` → `/Users/anicca/bin/phone.bak-pre-v32-20260606`
- Modify (backup): `~/.zshrc` → `~/.zshrc.bak-pre-v32-20260606`
- Modify (backup, sudo): `/etc/ssh/sshd_config` → `/etc/ssh/sshd_config.bak-pre-v32-20260606`

- [ ] **Step 1: Backup phone binary**

Run:
```bash
cp /Users/anicca/bin/phone /Users/anicca/bin/phone.bak-pre-v32-20260606
```
Expected: silent success, file exists.

- [ ] **Step 2: Backup zshrc**

Run:
```bash
cp ~/.zshrc ~/.zshrc.bak-pre-v32-20260606
```
Expected: silent success.

- [ ] **Step 3: Backup sshd_config**

Run:
```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak-pre-v32-20260606
```
Expected: prompts for password once, then silent success.

- [ ] **Step 4: Verify all 3 backups exist**

Run:
```bash
ls -la /Users/anicca/bin/phone.bak-pre-v32-20260606 ~/.zshrc.bak-pre-v32-20260606
sudo ls -la /etc/ssh/sshd_config.bak-pre-v32-20260606
```
Expected: 3 lines, each showing the backup file with size > 0.

- [ ] **Step 5: Stage no commit (backups are local artifacts, not tracked)**

No commit.

---

### Task 3: Configure SSH keepalive on Mac Mini (defense in depth)

**Files:**
- Modify: `/etc/ssh/sshd_config` (append 2 lines)

- [ ] **Step 1: Check current ClientAliveInterval setting**

Run:
```bash
grep -E '^[[:space:]]*ClientAlive' /etc/ssh/sshd_config || echo "ABSENT"
```
Expected: either current values OR `ABSENT`.

- [ ] **Step 2: Append (or replace if present) the keepalive directives**

Run:
```bash
sudo tee -a /etc/ssh/sshd_config <<'EOF'

# Added 2026-06-06 for Anicca v3.2 phone persistence (defense in depth alongside mosh)
ClientAliveInterval 60
ClientAliveCountMax 5
EOF
```
Expected: prompts password (or remembered), output mirrors the appended block.

- [ ] **Step 3: Validate sshd_config syntax**

Run:
```bash
sudo /usr/sbin/sshd -t && echo "sshd_config OK"
```
Expected: `sshd_config OK`. Any other output = STOP and revert backup.

- [ ] **Step 4: Reload sshd**

Run:
```bash
sudo launchctl kickstart -k system/com.openssh.sshd 2>&1 || sudo launchctl unload /System/Library/LaunchDaemons/ssh.plist && sudo launchctl load /System/Library/LaunchDaemons/ssh.plist
```
Expected: silent or single line message.

- [ ] **Step 5: Smoke test SSH still works**

Run from MacBook (or here if we have a second SSH client):
```bash
ssh -o BatchMode=yes localhost 'echo ssh-ok' 2>&1 | tail -1
```
Expected: `ssh-ok` OR a denied-but-reached message (means sshd alive). Connection refused = revert backup.

- [ ] **Step 6: Commit nothing (system file, not in repo)**

No commit.

---

### Task 4: Write bats test scaffold for phone CLI

**Files:**
- Create: `~/anicca-project/tests/phone/test_phone.bats`
- Create: `~/anicca-project/tests/phone/helpers.bash`

- [ ] **Step 1: Create test helpers**

Write `/Users/anicca/anicca-project/tests/phone/helpers.bash`:

```bash
#!/usr/bin/env bash
# Test helpers for phone bats suite.
# We fake tmux + date so we can assert calls without spawning real sessions.

setup_phone_test_env() {
  export PATH="$BATS_TEST_TMPDIR/fake-bin:$PATH"
  mkdir -p "$BATS_TEST_TMPDIR/fake-bin"
  export TMUX_CALLS="$BATS_TEST_TMPDIR/tmux-calls.log"
  : > "$TMUX_CALLS"

  cat > "$BATS_TEST_TMPDIR/fake-bin/tmux" <<'EOF'
#!/usr/bin/env bash
echo "$@" >> "$TMUX_CALLS"
case "$1" in
  ls)
    if [ -f "$BATS_TEST_TMPDIR/tmux-ls-output" ]; then
      cat "$BATS_TEST_TMPDIR/tmux-ls-output"
    fi
    ;;
  *)
    : # no-op for other commands
    ;;
esac
EOF
  chmod +x "$BATS_TEST_TMPDIR/fake-bin/tmux"

  cat > "$BATS_TEST_TMPDIR/fake-bin/date" <<'EOF'
#!/usr/bin/env bash
if [ "$1" = "+%s" ]; then
  echo "1780900000"
else
  /bin/date "$@"
fi
EOF
  chmod +x "$BATS_TEST_TMPDIR/fake-bin/date"
}
```

- [ ] **Step 2: Create the failing bats test file**

Write `/Users/anicca/anicca-project/tests/phone/test_phone.bats`:

```bash
#!/usr/bin/env bats

load helpers

setup() {
  setup_phone_test_env
  PHONE_BIN="/Users/anicca/bin/phone"
}

@test "phone with no arg creates a new tmux session named phone-<ts>" {
  run "$PHONE_BIN"
  [ "$status" -eq 0 ]
  grep -q "new-session -A -s phone-1780900000" "$TMUX_CALLS"
}

@test "phone ls invokes tmux ls and filters phone-*" {
  printf 'phone-1780000000: 1 window\nphone-1780900000: 1 window\nother: 1 window\n' > "$BATS_TEST_TMPDIR/tmux-ls-output"
  run "$PHONE_BIN" ls
  [ "$status" -eq 0 ]
  echo "$output" | grep -q "phone-1780000000"
  echo "$output" | grep -q "phone-1780900000"
  ! echo "$output" | grep -q "^other:"
}

@test "phone <name> attaches to that named session" {
  run "$PHONE_BIN" phone-1780000000
  [ "$status" -eq 0 ]
  grep -q "attach -t phone-1780000000" "$TMUX_CALLS"
}

@test "phone kill <name> kills that session" {
  run "$PHONE_BIN" kill phone-1780000000
  [ "$status" -eq 0 ]
  grep -q "kill-session -t phone-1780000000" "$TMUX_CALLS"
}

@test "phone kill with no arg prints usage and exits 1" {
  run "$PHONE_BIN" kill
  [ "$status" -eq 1 ]
  echo "$output" | grep -q "usage: phone kill"
}

@test "phone last attaches to the most-recent phone-* session" {
  printf 'phone-1780000000: 1 window\nphone-1780900000: 1 window\n' > "$BATS_TEST_TMPDIR/tmux-ls-output"
  run "$PHONE_BIN" last
  [ "$status" -eq 0 ]
  grep -q "attach -t phone-1780900000" "$TMUX_CALLS"
}

@test "phone exports MOSHI_PHONE=1 when creating a session" {
  run "$PHONE_BIN"
  [ "$status" -eq 0 ]
  grep -q "MOSHI_PHONE=1" "$TMUX_CALLS" || \
    grep -q "new-session.*-e MOSHI_PHONE=1" "$TMUX_CALLS" || \
    grep -q "set-environment.*MOSHI_PHONE" "$TMUX_CALLS"
}
```

- [ ] **Step 3: Run the test suite — confirm all fail (current phone binary doesn't support these)**

Run:
```bash
cd /Users/anicca/anicca-project && bats tests/phone/test_phone.bats
```
Expected: 7 tests run, ≥ 5 FAIL (the current phone script has no `ls`/`kill`/`last`/`MOSHI_PHONE` semantics matching this contract). 1-2 might coincidentally pass.

- [ ] **Step 4: Commit the test scaffold (RED state)**

```bash
cd /Users/anicca/anicca-project
git add tests/phone/test_phone.bats tests/phone/helpers.bash
git commit -m "test(phone): bats scaffold for v3.2 multi-session contract (RED)

Failing tests for the contract phone CLI must satisfy:
- no arg → new session phone-<unix_ts>
- ls → filter to phone-* only
- <name> → attach
- kill <name> → terminate
- kill no-arg → usage + exit 1
- last → attach most-recent phone-*
- session sees MOSHI_PHONE=1

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: Rewrite `/Users/anicca/bin/phone` to satisfy the contract (GREEN)

**Files:**
- Modify: `/Users/anicca/bin/phone` (full rewrite)

- [ ] **Step 1: Write the new phone binary**

Write `/Users/anicca/bin/phone`:

```bash
#!/usr/bin/env bash
# Anicca v3.2 phone — per-tap independent persistent Claude sessions.
#
# Behaviors:
#   phone                  spawn NEW tmux session "phone-<unix_ts>" in ~/anicca-project,
#                          set MOSHI_PHONE=1 so zshrc autostarts Claude (Opus 4.7).
#   phone ls               list running phone-* tmux sessions only.
#   phone <name>           attach to that named tmux session (resume).
#   phone kill <name>      kill that tmux session.
#   phone last             attach to the most-recently-created phone-* session.
#
# Why per-tap: Dais wants N concurrent independent Claude conversations
# (one per Moshi tab). A singleton session would broadcast input across tabs.
#
# Why no --continue inside: each session must be a fresh conversation UUID.
# Reattach to an old one via `phone <name>`.

set -euo pipefail

TMUX="${TMUX_BIN:-tmux}"
START_DIR="$HOME/anicca-project"

case "${1:-}" in
  ls)
    "$TMUX" ls 2>/dev/null | grep -E '^phone-[0-9]+:' || true
    ;;
  kill)
    if [ -z "${2:-}" ]; then
      echo "usage: phone kill <session-name>" >&2
      exit 1
    fi
    "$TMUX" kill-session -t "$2"
    ;;
  last)
    LAST=$("$TMUX" ls 2>/dev/null | grep -E '^phone-[0-9]+:' | sort -t- -k2 -n | tail -1 | cut -d: -f1)
    if [ -z "$LAST" ]; then
      echo "phone: no running phone-* session" >&2
      exit 1
    fi
    exec "$TMUX" attach -t "$LAST"
    ;;
  "")
    SESSION="phone-$(date +%s)"
    # MOSHI_PHONE flag travels into the new shell via tmux -e (modern tmux ≥ 3.2)
    exec "$TMUX" new-session -A -s "$SESSION" -c "$START_DIR" \
      -e MOSHI_PHONE=1 \
      -e OPENCLAW_CONTEXT=interactive
    ;;
  *)
    exec "$TMUX" attach -t "$1"
    ;;
esac
```

- [ ] **Step 2: Make it executable**

Run:
```bash
chmod +x /Users/anicca/bin/phone
```
Expected: silent.

- [ ] **Step 3: Run the bats suite — confirm all 7 pass (GREEN)**

Run:
```bash
cd /Users/anicca/anicca-project && bats tests/phone/test_phone.bats
```
Expected: `7 tests, 0 failures`. Any failure = STOP, fix the script, re-run.

- [ ] **Step 4: Commit the green implementation**

```bash
cd /Users/anicca/anicca-project
git add /Users/anicca/bin/phone  # NOTE: bin/phone is outside repo. Use a tracked copy:
mkdir -p anicca-bin-mirror
cp /Users/anicca/bin/phone anicca-bin-mirror/phone
cp /Users/anicca/bin/phone.bak-pre-v32-20260606 anicca-bin-mirror/phone.bak-pre-v32-20260606
git add anicca-bin-mirror/phone anicca-bin-mirror/phone.bak-pre-v32-20260606
git commit -m "feat(phone): per-tap independent persistent session CLI (GREEN)

- no arg → tmux new phone-<unix_ts> with MOSHI_PHONE=1 (autostart hook)
- ls → list phone-* only
- <name> → attach
- kill <name> → terminate
- last → attach most-recent
- bats suite 7/7 pass

The live binary lives at /Users/anicca/bin/phone (outside repo).
This anicca-bin-mirror/ tracked copy is the canonical source; manual
sync needed when editing. (Better long-term: move bin/ into a tracked
dotfiles repo.)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: Add `~/.zshrc` autostart hook + remove legacy interceptor

**Files:**
- Modify: `~/.zshrc`

- [ ] **Step 1: Locate the legacy "Anicca tmux phone interceptor" block**

Run:
```bash
grep -n "Anicca tmux phone interceptor\|^tmux() {" ~/.zshrc
```
Expected: 1-2 matching line numbers around the legacy block.

- [ ] **Step 2: Remove the legacy block in-place using a marker-delimited delete**

Run:
```bash
# Use sed to remove from "─── Anicca tmux phone interceptor" marker through the closing brace block end
awk '
  /─── Anicca tmux phone interceptor/ { skip=1; next }
  skip && /^\}$/ { skip=0; next }
  !skip { print }
' ~/.zshrc > ~/.zshrc.new && mv ~/.zshrc.new ~/.zshrc
```
Expected: file rewritten without the legacy `tmux()` function block.

- [ ] **Step 3: Verify removal**

Run:
```bash
grep -c "Anicca tmux phone interceptor" ~/.zshrc
```
Expected: `0`.

- [ ] **Step 4: Append the v3.2 autostart hook to ~/.zshrc**

Run:
```bash
cat >> ~/.zshrc <<'EOF'

# ─── Anicca v3.2 phone autostart ──────────────────────────────────
# Runs only inside a tmux session created by `phone` (MOSHI_PHONE=1).
# Replaces the shell with a fresh Claude (Opus 4.7) conversation.
# Idempotent: CLAUDE_AUTOSTARTED guard prevents re-exec on nested shells.
if [[ "$MOSHI_PHONE" == "1" && -z "$CLAUDE_AUTOSTARTED" ]]; then
  export CLAUDE_AUTOSTARTED=1
  SESSION_NAME=$(tmux display -p '#S' 2>/dev/null || echo "phone")
  SESSION_UUID=$(uuidgen 2>/dev/null || cat /proc/sys/kernel/random/uuid 2>/dev/null)
  exec claude \
    --name "$SESSION_NAME" \
    --session-id "$SESSION_UUID" \
    --model claude-opus-4-7 \
    --max-budget-usd 10
fi
# ─────────────────────────────────────────────────────────────────
EOF
```
Expected: silent append.

- [ ] **Step 5: Lint zshrc**

Run:
```bash
zsh -n ~/.zshrc && echo "zshrc syntax OK"
```
Expected: `zshrc syntax OK`. Any other output = STOP, restore backup.

- [ ] **Step 6: Smoke test the autostart hook (without spawning real claude — use a stub)**

Run:
```bash
MOSHI_PHONE=1 CLAUDE_AUTOSTARTED= zsh -i -c 'type claude; echo guard=$CLAUDE_AUTOSTARTED' 2>&1 | head -5
```
Expected: shows that `claude` is a command (real binary), and the guard variable would have been set. Note: a fully end-to-end test happens on iPhone in Task 10.

- [ ] **Step 7: Mirror zshrc changes into the repo for tracking**

```bash
cd /Users/anicca/anicca-project
mkdir -p anicca-dotfiles-mirror
cp ~/.zshrc anicca-dotfiles-mirror/.zshrc
git add anicca-dotfiles-mirror/.zshrc
git commit -m "feat(zshrc): v3.2 phone autostart hook + remove legacy interceptor

- removed: legacy tmux() function that rewrote 'attach -t phone' to
  new 'phone-<unix_ts>' sessions (per-tap fresh shell, no claude)
- added: MOSHI_PHONE=1 guard that exec's claude --session-id <uuid>
         --model claude-opus-4-7 --max-budget-usd 10 on session start

Mirrored copy under anicca-dotfiles-mirror/ for git tracking.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: Write `phone-cleanup` script + launchd plist

**Files:**
- Create: `/Users/anicca/bin/phone-cleanup`
- Create: `~/Library/LaunchAgents/local.phone-cleanup.plist`

- [ ] **Step 1: Write phone-cleanup**

Write `/Users/anicca/bin/phone-cleanup`:

```bash
#!/usr/bin/env bash
# Anicca v3.2 phone-cleanup — kill phone-* tmux sessions older than 7 days
# AND with zero attached clients.
#
# Runs daily via ~/Library/LaunchAgents/local.phone-cleanup.plist.

set -euo pipefail

TMUX="${TMUX_BIN:-tmux}"
NOW=$(date +%s)
CUTOFF_SECS=$((7 * 24 * 3600))

"$TMUX" ls -F '#{session_name}|#{session_created}|#{session_attached}' 2>/dev/null \
  | awk -F'|' -v now="$NOW" -v cutoff="$CUTOFF_SECS" '
      $1 ~ /^phone-[0-9]+$/ && $3 == "0" && (now - $2) > cutoff {
        print $1
      }' \
  | while read -r name; do
      echo "phone-cleanup: killing idle session $name (age >7d, 0 clients)"
      "$TMUX" kill-session -t "$name"
    done
```

- [ ] **Step 2: Make it executable**

Run:
```bash
chmod +x /Users/anicca/bin/phone-cleanup
```

- [ ] **Step 3: Smoke test it (should print nothing if no stale sessions)**

Run:
```bash
/Users/anicca/bin/phone-cleanup
echo "exit=$?"
```
Expected: empty output (or 0-N "killing" lines if old sessions exist), `exit=0`.

- [ ] **Step 4: Write the launchd plist**

Write `~/Library/LaunchAgents/local.phone-cleanup.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>local.phone-cleanup</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/anicca/bin/phone-cleanup</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>4</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/anicca/.openclaw/logs/phone-cleanup.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/anicca/.openclaw/logs/phone-cleanup.err</string>
</dict>
</plist>
```

- [ ] **Step 5: Load the launchd job**

Run:
```bash
mkdir -p ~/.openclaw/logs
launchctl unload ~/Library/LaunchAgents/local.phone-cleanup.plist 2>/dev/null || true
launchctl load -w ~/Library/LaunchAgents/local.phone-cleanup.plist
launchctl list | grep phone-cleanup
```
Expected: a single line showing `local.phone-cleanup` registered.

- [ ] **Step 6: Mirror + commit**

```bash
cd /Users/anicca/anicca-project
cp /Users/anicca/bin/phone-cleanup anicca-bin-mirror/phone-cleanup
mkdir -p anicca-dotfiles-mirror/LaunchAgents
cp ~/Library/LaunchAgents/local.phone-cleanup.plist anicca-dotfiles-mirror/LaunchAgents/
git add anicca-bin-mirror/phone-cleanup anicca-dotfiles-mirror/LaunchAgents/local.phone-cleanup.plist
git commit -m "feat(phone): phone-cleanup daily cron (kills idle >7d phone-* sessions)

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Write `phone-status` convenience script

**Files:**
- Create: `/Users/anicca/bin/phone-status`

- [ ] **Step 1: Write the script**

Write `/Users/anicca/bin/phone-status`:

```bash
#!/usr/bin/env bash
# Anicca v3.2 phone-status — humans-friendly status of phone-* tmux sessions.
# Shows: session name | age (human) | attached clients | current pane command.

set -euo pipefail

TMUX="${TMUX_BIN:-tmux}"
NOW=$(date +%s)

printf '%-30s  %-10s  %-8s  %s\n' "SESSION" "AGE" "CLIENTS" "CURRENT"

"$TMUX" ls -F '#{session_name}|#{session_created}|#{session_attached}|#{pane_current_command}' 2>/dev/null \
  | awk -F'|' '$1 ~ /^phone-[0-9]+$/' \
  | while IFS='|' read -r name created clients cmd; do
      age=$((NOW - created))
      d=$((age / 86400))
      h=$(( (age % 86400) / 3600 ))
      m=$(( (age % 3600) / 60 ))
      if [ $d -gt 0 ]; then human="${d}d${h}h"
      elif [ $h -gt 0 ]; then human="${h}h${m}m"
      else human="${m}m"
      fi
      printf '%-30s  %-10s  %-8s  %s\n' "$name" "$human" "$clients" "$cmd"
    done
```

- [ ] **Step 2: Make executable**

Run:
```bash
chmod +x /Users/anicca/bin/phone-status
```

- [ ] **Step 3: Smoke test**

Run:
```bash
/Users/anicca/bin/phone-status
```
Expected: header row + 0-N data rows.

- [ ] **Step 4: Mirror + commit**

```bash
cd /Users/anicca/anicca-project
cp /Users/anicca/bin/phone-status anicca-bin-mirror/phone-status
git add anicca-bin-mirror/phone-status
git commit -m "feat(phone): phone-status convenience listing

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Local end-to-end smoke (without iPhone, on Mac Mini)

**Files:**
- None.

- [ ] **Step 1: Open a fresh terminal on Mac Mini (or here in a new Bash run)**

Run:
```bash
# Simulate "phone" entry from a clean env (no MOSHI_PHONE leaking from current session)
env -i HOME="$HOME" PATH="/Users/anicca/bin:/opt/homebrew/bin:/usr/bin:/bin" /Users/anicca/bin/phone --help-noop 2>&1 | head -1 || true
```
Expected: returns (the `--help-noop` falls into the `*` case = tries attach to a non-existent session, prints tmux's error). This proves the binary executes.

- [ ] **Step 2: Verify `phone ls` returns 0 (even with no sessions)**

Run:
```bash
/Users/anicca/bin/phone ls
echo "exit=$?"
```
Expected: empty (no phone sessions yet) + `exit=0`.

- [ ] **Step 3: From this same shell, spawn a real test session — but DO NOT attach**

We cannot use `exec` inside this shell (it'd kill us). Instead:
```bash
tmux new-session -d -s phone-test-$$ -c "$HOME/anicca-project" -e MOSHI_PHONE=1 -e OPENCLAW_CONTEXT=interactive 'sleep 5; exit'
sleep 1
/Users/anicca/bin/phone ls
tmux kill-session -t phone-test-$$
```
Expected: `phone ls` lists the test session for ~1s window. Manual `phone` real-use is verified on iPhone in Task 10.

- [ ] **Step 4: Commit nothing (no file changes)**

No commit.

---

### Task 10: iPhone-side validation — Dais physical action required

**Files:**
- None on Mac Mini. iPhone app config only.

This is the one task where Dais must physically touch his phone (per HARD RULE #-2 exception: "physical movement" = installing an iOS app, OR tapping the Moshi/Blink button to verify behavior). Anicca posts the instructions, Dais executes them.

- [ ] **Step 1: Determine if current Moshi iOS app supports mosh**

Anicca: read Moshi's documentation or check the Anicca-known iOS terminal app inventory. If Moshi supports mosh client, no app switch needed.

```bash
firecrawl scrape "https://moshi.macroenter.com/features" markdown 2>/dev/null | grep -i mosh | head -5 || echo "no doc hit"
```

Branch:
- If Moshi has mosh → Step 2a
- If Moshi has no mosh → Step 2b (switch to Blink Shell)

- [ ] **Step 2a (Moshi supports mosh): Update Moshi's SSH command**

Open Moshi → host config for Mac Mini → change command from `tmux attach -t phone` to `mosh keiodaisuke@100.99.82.95 -- /Users/anicca/bin/phone`. Save.

- [ ] **Step 2b (Moshi lacks mosh): Recommend Blink Shell**

Anicca posts to Slack `#dev` (via slack-send) a card:
> "Phone v3.2 needs mosh client. Moshi may not have it. Install **Blink Shell** ($19.99 one-time, App Store) on iPhone, configure with key auth to Mac Mini (100.99.82.95), and set command to `mosh-bootstrap` (a 1-line wrapper at `/Users/anicca/bin/mosh-bootstrap` that invokes `mosh ... -- /Users/anicca/bin/phone`). Acknowledge in this thread."
> Then waits for Dais reply.

If Blink path taken, also create `/Users/anicca/bin/mosh-bootstrap`:
```bash
#!/usr/bin/env bash
exec mosh keiodaisuke@100.99.82.95 -- /Users/anicca/bin/phone
```
`chmod +x` it.

- [ ] **Step 3: Dais validates on iPhone (3 tabs)**

Dais's checklist:
1. Tap Moshi/Blink → tab 1 → claude prompt appears in ≤ 2s. Type "hello tab 1".
2. New tab → tap → tab 2 → independent claude prompt. Type "hello tab 2".
3. New tab → tab 3 → tab 3 prompt. Type "hello tab 3".
4. Switch back to tab 1 → confirm tab 1's transcript shows only "hello tab 1" (no leak from tab 2/3).
5. Lock phone 5 min. Unlock → all 3 tabs still alive, cursors live.
6. Switch from Wi-Fi to LTE (toggle Wi-Fi off). Type → continues without hiccup.
7. From Mac Mini terminal: `/Users/anicca/bin/phone-status` shows 3 phone-* sessions, 3 attached clients.

If any check fails → Dais reports back to Anicca → Anicca debugs.

- [ ] **Step 4: Commit nothing (no file changes from validation pass)**

No commit. Validation evidence is screenshot/text from Dais.

---

### Task 11: Final commit + push (close branch)

**Files:**
- Already committed individual changes per task. Final tidy commit if any loose ends.

- [ ] **Step 1: Ensure all task commits are pushed**

```bash
cd /Users/anicca/anicca-project
git status
git push 2>&1 | tail -3
```
Expected: `git status` clean, `git push` reports either "Everything up-to-date" or success line.

- [ ] **Step 2: Update TODO list — Task #8 complete, Task #2 complete**

(Task tool calls done by the agent, not in shell.)

- [ ] **Step 3: Update spec to reference live implementation**

Add a one-line `## 11. Implementation log` section to the spec pointing to the plan file path and the iPhone-validation evidence link (Slack thread).

```bash
cd /Users/anicca/anicca-project
# Insert section reference (manual edit OK)
git add docs/superpowers/specs/2026-06-05-anicca-v32-evolution-design.md
git commit -m "docs(spec): link v3.2 phone implementation log" && git push 2>&1 | tail -3
```

---

## Self-Review

**Spec coverage** (against `docs/superpowers/specs/2026-06-05-anicca-v32-evolution-design.md` §3):
- §3.2 multi-session goal → Task 5 (phone binary) + Task 6 (zshrc autostart with `--session-id $(uuidgen)`)
- §3.2 disconnect tolerance → Task 3 (sshd keepalive) + pre-installed mosh
- §3.3 design diagram → Task 5/6 implement directly
- §3.4 files touched → all enumerated tasks 5/6/7/8 + Task 3 (sshd) + Task 1 (mosh already present)
- §3.5 success criteria → Task 9 (Mac Mini smoke) + Task 10 (Dais iPhone E2E)
- §3.6 risks: Moshi-vs-Blink → Task 10 Step 2b
- §3.7 open question: `claude --bg` vs foreground → resolved as foreground `exec claude` (cleaner; Dais wants it to look like he's typing directly)

**Placeholder scan**: no TBDs, no "TODO", no "similar to". All code blocks are runnable as-is.

**Type / name consistency**: `phone-<unix_ts>` naming used identically across phone, phone-cleanup, phone-status, bats tests. `MOSHI_PHONE=1` used identically across phone (export via `tmux -e`) and zshrc (detection). `OPENCLAW_CONTEXT=interactive` set in phone, ready for subsystem ③ to consume.

**Coverage gap noted**: subsystem ③ (Plan #4/Execute #6) sets `defaults.model.primary = openai/gpt-5.4-mini`, but this plan hardcodes `--model claude-opus-4-7` for phone — that is correct because phone is the chat surface (frontier), not a cron. Cross-plan consistency preserved.

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-06-06-persistent-phone-session.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task with two-stage review between tasks; faster iteration; matches "go one by one" semantics.
2. **Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, batched with checkpoints.

For this plan: **recommend Subagent-Driven** — each task is small and self-contained (≤ 5 commands), and the file blast radius is wide (system files + user dotfiles + repo + LaunchAgents), so per-task review reduces blast.
