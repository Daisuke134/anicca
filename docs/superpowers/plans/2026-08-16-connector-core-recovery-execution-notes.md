# Connector core recovery — execution notes

Branch `fix/connector-core-recovery`, base `origin/main` (contains `f32eee4d2`).
SSOT: spec `0.2.1 Active remaining TODO SSOT`. One item at a time, evidence before status.

## C-CORE-01 single-owner cleanup — DONE 2026-08-16

Target resolution (read-only, before any change):

| label | ProgramArguments | verdict |
|---|---|---|
| `...-connector-native-healthcheck` | `.worktrees/connector-native-completion/skills/connector/healthcheck.sh` | worktree absent (`ls` → No such file or directory) → `EX_CONFIG` 78 |
| `...-connector-healer-shadow` | same deleted worktree, `healer-shadow.sh` | `EX_CONFIG` 78 |
| `...-connector-host-bridge` | `apps/life-manager/scripts/connector-host-bridge-boot.sh` | retired; running PID 805 on `127.0.0.1:18793` |
| `...-connector-native` | `skills/connector/run.sh` | official entrypoint, keep loaded |

Dependency check before unload: `grep -rn "18793\|host-bridge\|hostBridge"` over `skills/connector/`,
`connector-native-runtime.js`, `connector-minimal-production.js` returned 0 hits. The only remaining
`18793` consumer is `deploy/local/compose.connector.yaml` (container path, not the native local path).

Action: `launchctl bootout gui/$UID/<label>` for the three labels above. No plist deleted, no state touched,
no browser or OS service stopped.

Readback after the change:

- `launchctl list | grep -i connector` → `-  0  ai.anicca.life-manager-connector-native` only. Zero `EX_CONFIG` 78 rows.
- `18793` listener → none. PID 805 gone.
- `~/Library/LaunchAgents` still holds all 7 connector plist files (4 active-named + 3 previously retired/disabled).
- `~/.local/state/life-manager/connector-native` still holds 27 entries.
- Listening ports in the `9xxx` range: `9223`, `9324`, `9326`, `9327`. Gig-owned `9223` untouched;
  Connector `9222` still has no listener, which is exactly `C-CORE-02`.

Not done here: `9222` owner restoration, travel gate removal, any wake, any external write.
