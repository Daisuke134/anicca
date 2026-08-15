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

The first provider CLI slice is live:

```bash
skills/affiliate/affiliate provider inspect \
  --provider hubspot-impact --cdp-port 9223 --receipt "$RECEIPT"
```

It attaches read-only to the existing task browser, selects exactly one
origin/title/path-bound tab, maps rendered text through the versioned provider
playbook, and writes an atomic sanitized receipt. Unknown UI never becomes an
approval. The current slice observes status only; it cannot submit or publish.

Use `provider poll` with the same arguments in a loop. The first observation or
a real state change returns `changed=true` and a deterministic `transition_id`;
an unchanged retry returns `next_action=NO_STATE_CHANGE`. Downstream actions
must deduplicate on `transition_id`.

Use the versioned English program research before any application:

```bash
skills/affiliate/affiliate programs list
skills/affiliate/affiliate programs next --decision READY_NO_REVIEW
skills/affiliate/affiliate programs credential --id hubspot-impact
python3 -c 'import secrets; print("A!" + secrets.token_hex(24))' | \
  skills/affiliate/affiliate programs store-credential \
  --id elevenlabs --label ElevenLabs
```

The registry stores only official-source eligibility and the latest receipted
application decision. Execute its `next_action`, then require authenticated
rendered readback before changing application or tracking-link state. Never
bulk-apply past an audience, content, fit, or traffic gate.

Provider passwords are never committed. The mode-0600 Git-external local
`~/.config/anicca/affiliate-credentials.md` is the recovery SSOT and is written
before any signup/reset submit. Each program may also bind to a fixed
`keychain://service/account` mirror. `programs credential` checks that mirror:
only a non-empty value is `VERIFIED_NONEMPTY`; a present but empty item is
`MISSING_OR_EMPTY` and login stays disabled. Impact uses
`keychain://ai.anicca.affiliate.provider.impact/primary`. After official recovery,
write the new value there and prove a fresh-tab login before resuming Grammarly.
`store-credential` reads the secret only from stdin, writes the Git-external
mode-0600 private Markdown first, then mirrors it to the fixed program Keychain
reference, and returns status only. Run it before every signup/reset submission;
after fresh login repeat with `--verification VERIFIED_LOGIN`. Never pass a
password on the affiliate CLI command line.

The committed bootstrap manifest pins PBS CPython `3.14.7+20260814` for macOS
arm64 by immutable URL and SHA-256. The installer verifies and extracts the same
held artifact, validates the full runtime tree, and atomically activates it
without changing PATH or the system Python. The current Mac also has a receipted
CloakBrowser app. Affiliate-only Keychain readback is live-proven; an unverified
reference is never `AUTHORIZED`. Authenticated provider/mail/X session discovery,
account-handle verification, launchd, publication, and revenue remain disabled.
