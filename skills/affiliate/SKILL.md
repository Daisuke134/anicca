---
name: affiliate
description: Builds, runs, and migrates the Life Manager Affiliate Agent across macOS devices.
---

# Life Manager Affiliate Skill

status: `MIGRATION_ONLY`
execution: `DISABLED`

The canonical source is this `skills/affiliate` directory in the Life Manager
repository. `legacy/` contains byte-preserved evidence only; archived files are
never executed by this skill.

Mutable state lives at
`${LIFE_MANAGER_STATE_HOME:-$HOME/.local/state/life-manager}/affiliate`.
Installed data lives at
`${LIFE_MANAGER_DATA_HOME:-$HOME/.local/share/life-manager}/affiliate`.

Live affiliate execution is blocked until the later E0/provider/browser/
publisher receipt gates are satisfied. This migration shell may verify and
install an immutable disabled release, but it does not register launchd jobs,
publish content, or claim revenue.
