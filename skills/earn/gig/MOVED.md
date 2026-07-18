# MOVED — canonical home is now profitable-claude

2026-07-18: the gig loop was cut over to `~/profitable-claude/skills/gig-work/`
(launchd labels `ai.anicca.hf-gig-*`, spec: anicca-project
`docs/superpowers/specs/2026-07-18-gig-migration-to-profitable-claude-inventory.md`).

This directory is a tombstone: nothing loads it anymore (old `ai.anicca.gig-*`
plists are unloaded and parked in `~/Library/LaunchAgents.disabled-gig-migration-20260718/`).
Do NOT edit code here. Physical deletion happens in a separate PR only after a
grep shows zero remaining references (spec §8-4).

Why it stays for now: `~/anicca/runtime/anicca-daemon.sh` still rsyncs `skills/`
into citizen HOMEs, and franklin-side launchers reference `$HOME/anicca` paths
(see PC-singularization spec §3). Removing this dir before Task #20 (franklin
launcher self-copy convergence) would break self-funded instances.
