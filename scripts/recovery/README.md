# Blackout auto-recovery — live copies

Backup of the files that make the Mac mini come back on its own after a power
cut. **These run from `~`, not from here** — this directory exists so the
recovery system survives the disk it protects.

Design + TODO: [`docs/superpowers/specs/2026-08-01-blackout-autorecovery-design.md`](../../docs/superpowers/specs/2026-08-01-blackout-autorecovery-design.md)

| File here | Lives at | Role |
|---|---|---|
| `health-check.sh` | `~/recovery-setup/health-check.sh` | Every 60s: internet, Tailscale, both Codex daemons, Claude RC. Repairs only what is actually down |
| `com.anicca.recovery-health.plist` | `~/Library/LaunchAgents/` | Runs the above at login + every 60s |
| `codex-remote-keepalive.sh` | `~/.codex-remote-keepalive.sh` | Keeps both ChatGPT accounts' Codex remote-control connected |
| `codex-remote-status.py` | `~/.codex-remote-status.py` | Parses `remote-control start --json` status |
| `com.anicca.codex-remote-keepalive.plist` | `~/Library/LaunchAgents/` | Runs the keepalive every 5 min |
| `com.anicca.claude-remote-control.plist` | `~/Library/LaunchAgents/` | Claude Remote Control server, with the keychain unlock that a locked `ci-signing.keychain-db` otherwise hangs forever |
| `rollback.md` | `~/recovery-setup/rollback.md` | Every changed value, with its before-state |

## Restoring after a wipe

```bash
cp scripts/recovery/health-check.sh ~/recovery-setup/health-check.sh
cp scripts/recovery/codex-remote-keepalive.sh ~/.codex-remote-keepalive.sh
cp scripts/recovery/codex-remote-status.py ~/.codex-remote-status.py
cp scripts/recovery/com.anicca.*.plist ~/Library/LaunchAgents/
chmod +x ~/recovery-setup/health-check.sh ~/.codex-remote-keepalive.sh
for j in recovery-health codex-remote-keepalive claude-remote-control; do
  launchctl bootstrap gui/501 ~/Library/LaunchAgents/com.anicca.$j.plist
done
```

Then re-apply the power settings from `rollback.md` (`autorestart`, `sleep 0`,
`womp`, the 06:00 `wakepoweron`).

## The one rule these scripts encode

A repair that fires on a healthy component is worse than no repair. On
2026-07-31 a keepalive whose repair condition was merely "status is not
connected" killed healthy daemons every five minutes and took the phone
offline. Repair triggers here match one unambiguous broken state; anything
unparsed or transient is left alone.
