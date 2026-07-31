# Blackout-resilience setup — rollback

Set up 2026-07-31. Baseline snapshot of every value below:
`~/recovery-setup/baseline-20260731-235408.txt`

## What was ALREADY true before this session (not changed by me)

These were already configured; nothing to roll back.

| Setting | Value found | Meaning |
|---|---|---|
| `autorestart` | `1` | Boots itself when power returns |
| `womp` | `1` | Wake on network |
| `sleep` / `SleepDisabled` | `0` / `1` | Never sleeps |
| `standby` | `0` | No standby |
| FileVault | `Off` | No password wall at boot |
| `autoLoginUser` | `anicca` | Logs in without a human |
| `/etc/kcpassword` | present, `root:wheel 0600` | Auto-login secret (created 2026-02-21) |
| Remote Login (SSH) | `On` | |
| `waitforstartupafterpowerfailure` | `0 seconds` | Boots immediately |
| Tailscale | `homebrew.mxcl.tailscale` in `/Library/LaunchDaemons` | System daemon — runs BEFORE login |
| User LaunchAgents | 189 plists | Load automatically at auto-login |

## What I changed

### 1. Daily auto power-on (insurance)

```bash
sudo pmset repeat wakeorpoweron MTWRFSU 06:00:00
```

Rollback:

```bash
sudo pmset repeat cancel
```

Before: no repeating power events. After: `wakepoweron at 6:00AM every day`.

### 2. Health monitor (new)

- `~/recovery-setup/health-check.sh`
- `~/Library/LaunchAgents/com.anicca.recovery-health.plist` (RunAtLoad, every 60s)
- Log: `~/recovery-setup/health.log`

Checks internet, Tailscale, both Codex remote-control daemons, Claude Remote Control.
Repairs ONLY a component that is actually down.

Rollback:

```bash
launchctl bootout gui/501/com.anicca.recovery-health
rm ~/Library/LaunchAgents/com.anicca.recovery-health.plist
rm -rf ~/recovery-setup
```

### 3. Codex keepalive fix (earlier this session)

`~/.codex-remote-keepalive.sh` had a repair condition so broad it killed healthy
daemons every 5 minutes, which is what took the phone offline. Now it kills only
on the literal string `not managed by codex app-server daemon`.

Files: `~/.codex-remote-keepalive.sh`, `~/.codex-remote-status.py`,
`~/Library/LaunchAgents/com.anicca.codex-remote-keepalive.plist`.

Rollback:

```bash
launchctl bootout gui/501/com.anicca.codex-remote-keepalive
rm ~/Library/LaunchAgents/com.anicca.codex-remote-keepalive.plist
```

Note: this job is now largely redundant with the health monitor above; the
health monitor covers the same ground once a minute instead of once every five.

### 4. Claude Remote Control auto-unlock (earlier this session)

`~/Library/LaunchAgents/com.anicca.claude-remote-control.plist` now unlocks
`~/ci-signing.keychain-db` before starting, because a locked keychain in the
search list hangs every credential read and killed the server for 5 hours.

Rollback: restore the `ProgramArguments` string to
`unset CLAUDE_CODE_OAUTH_TOKEN; exec /Users/anicca/.local/bin/claude remote-control --name "Mac mini"`.

## NOT done

- **No UPS** — a blackout is still a hard power cut.
- **No backup configured** — `tmutil destinationinfo` reports "No destinations configured".
  This is the largest remaining data risk under repeated hard power cuts.
- **Auto-login not verified by reboot** — `/etc/kcpassword` dates from 2026-02-21.
  If the account password changed since, auto-login fails silently and NOTHING
  recovers until a human logs in. Only a real reboot proves it.
