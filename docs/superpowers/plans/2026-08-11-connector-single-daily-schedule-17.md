# Connector single daily production schedule Item 17 plan

## Goal

Replace the unloaded five-minute installed native plist with the verified single 09:00 daily minimal Connector contract and load exactly that one production owner.

## Measured precondition

- Items 10–16 are accepted in the Active SSOT.
- Branch HEAD is clean and exactly upstream at `6abe5acc0`.
- Native, native healthcheck, Healer shadow, and host bridge labels are all unloaded; Connector process and lock are absent.
- The installed native plist still contains legacy `StartInterval=300`, but it is unloaded. The canonical repository template contains `StartCalendarInterval` at 09:00 and no `StartInterval`.

## Ponytail full gate

- Reuse `skills/connector/render-launchd.sh` and the canonical native plist template.
- Add no installer, daemon, retry sidecar, healthcheck, Healer, bridge, second label, or code change.
- Render into a `mktemp -d` directory because the renderer correctly refuses the live LaunchAgents directory.
- Lint and inspect the rendered plist before a precise mode-0600 install over only `~/Library/LaunchAgents/ai.anicca.life-manager-connector-native.plist`.
- Load exactly `ai.anicca.life-manager-connector-native`. Keep the other three labels unloaded and leave their private state/profile/evidence untouched.

## Execute and verify

1. Verify clean/upstream Git, no process/lock, healthy `:9222`, and four labels unloaded.
2. Render with the current worktree as repository root and `/Users/operator/.local/state/life-manager` as log home.
3. Require one output plist, `plutil` PASS, exact ProgramArguments/WorkingDirectory, 09:00 `StartCalendarInterval`, no `StartInterval`, and no healthcheck/Healer/bridge/`:9223` token.
4. Install mode 0600 over the exact native plist, then `launchctl bootstrap gui/<uid>` that file. Do not kickstart in Item 17.
5. Verify native loaded once with the exact program/workdir and daily event trigger; healthcheck/Healer/bridge loaded zero; process/lock zero before the scheduled execution.
6. Update SSOT, commit, and push. Item 18 then triggers the loaded production owner with `launchctl kickstart` and watches the first launchd-owned wake; it does not invoke a separate executor.

## Result

Pending production cutover.
