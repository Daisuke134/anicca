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

The committed bootstrap manifest pins PBS CPython `3.14.7+20260814` for macOS
arm64 by immutable URL and SHA-256. The installer verifies and extracts the same
held artifact, validates the full runtime tree, and atomically activates it
without changing PATH or the system Python. The current Mac also has a receipted
CloakBrowser app. Affiliate-only Keychain readback is live-proven; an unverified
reference is never `AUTHORIZED`. Authenticated provider/mail/X session discovery,
account-handle verification, launchd, publication, and revenue remain disabled.
