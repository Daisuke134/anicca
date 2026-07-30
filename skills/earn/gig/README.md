# Life Manager Gig loop

This directory is the canonical local OSS package for Life Manager's
marketplace revenue loop. Production cutover occurs only after the D5 parity
and controlled-plus-natural wake gates pass.

## Runtime flow

```text
launchd/systemd or Life Manager earn/gig slot
  -> gig_pass.sh
  -> Reply / Fulfill / Apply / List
  -> authoritative marketplace readback
  -> canonical event and identity ledgers
  -> Telegram human report + agent event feed
  -> evaluator -> one reversible strategy experiment -> keep/revert
  -> healer when freshness, evidence, browser, provider, or scheduler checks fail
```

## Source and state boundary

| Data | Location |
|---|---|
| Canonical source and tests | `skills/earn/gig/` |
| Shared model runner | `runtime/agent-runner/` |
| Shared browser helpers | `skills/browser/` |
| Existing local runtime state during migration | `${GIG_STATE_DIR:-$HOME/gig}` |
| Credentials, browser profile, transaction evidence | Outside Git |

Tracked `artifacts/`, retired `archive/`, credentials, cookies, runtime SQLite,
and customer evidence are not canonical source and must never be added here.

## Operator gates

1. Run the source contract and Gig characterization suites.
2. Complete repository-relative runner/browser wiring.
3. Verify an isolated-HOME install twice for idempotency.
4. Compare source and target results on the same copied state and fixtures.
5. Cut over only after one controlled live pass and one natural hourly pass
   agree on all four lane closures, marketplace readback, and Telegram ACK.

## Local install

The repository root `install.sh` prepares the Gig state boundary without
enabling marketplace schedulers. To render and enable the host scheduler after
the controlled parity gate:

```bash
# macOS or Linux auto-detection
skills/earn/gig/install-local.sh --scheduler auto

# Render-only verification
skills/earn/gig/install-local.sh --scheduler launchd --no-enable
skills/earn/gig/install-local.sh --scheduler systemd --no-enable
```

If `$HOME/gig` already exists, the installer adopts that directory in place and
does not copy, move, or rewrite its ledgers. A fresh install uses
`$LIFE_MANAGER_HOME/state/gig`. The atomic receipt is
`$LIFE_MANAGER_HOME/state/gig-install.json`.

The detailed execution order and live evidence are maintained in
`docs/loop-engineering/26-gig-loop-asis-tobe-plan.md` after D5-F migration.
