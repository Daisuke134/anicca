---
name: affiliate
description: Builds, runs, and migrates the Life Manager Affiliate Agent across macOS devices.
---

# Life Manager Affiliate Skill

status: `BOOTSTRAP_IN_PROGRESS`
legacy_migration: `MIGRATION_ONLY`
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

F0 provides four deterministic, non-publishing primitives:

- `bootstrap/install.sh` verifies a reviewed pinned manifest and writes an
  atomic machine-capability receipt;
- `scripts/authority_inventory.py` binds a Keychain reference to one explicit
  intent and records human-only external challenges;
- `scripts/profile_provisioner.py` creates isolated EN/JA browser roots without
  launching or copying a browser session.
- `scripts/machine_capability_inventory.py` receipts an explicitly requested
  macOS browser app from held no-follow file descriptors without launching it;
  generic executable admission remains fail-closed.

The committed bootstrap manifest intentionally contains no artifact yet. Its
default run therefore fails closed until current-host runtime/browser admission
records a real URL and SHA-256. The current Mac has a receipted CloakBrowser app,
but pinned Python installation remains open. Keychain readback, authenticated-session
discovery, account-handle verification, launchd, publication, and revenue all
remain disabled.
