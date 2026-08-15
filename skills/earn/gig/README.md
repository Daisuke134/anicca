# Life Manager Gig loop

This directory is the canonical local OSS package for Life Manager's
marketplace revenue loop. Production cutover occurs only after the D5 parity
and controlled-plus-natural wake gates pass.

## Runtime flow

```text
launchd/systemd
  -> Storefront / Apply / Negotiate / Paid direct owners
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
5. Verify one natural wake per direct owner, marketplace readback, and Telegram ACK.

## Local install

New users provide only three private values. The command stores references in
`$LIFE_MANAGER_HOME/state/gig-onboarding.json` with mode `0600`; it does not copy
the work profile, browser session, cookies, or credentials into Git.

```bash
skills/earn/gig/install-local.sh setup \
  --work-profile "$HOME/.config/anicca/job-search/profile.json" \
  --marketplace-profile "$HOME/.cloak/profiles/gig-daily-driver" \
  --report-chat YOUR_TELEGRAM_CHAT_ID

# Complete the returned official Coconala login URL once, then:
skills/earn/gig/install-local.sh doctor
skills/earn/gig/install-local.sh start
skills/earn/gig/install-local.sh status
skills/earn/gig/install-local.sh stop
skills/earn/gig/install-local.sh uninstall
```

`doctor` is read-only and reports `effect: 0`. `start` loads the dedicated
browser plus Storefront, Apply, Negotiate, and Paid owners, then succeeds only
after the existing natural-language daily reporter records a Telegram provider
message ID.

`uninstall` removes generated launchd/systemd units and private install receipts.
It deliberately preserves `$GIG_STATE_DIR`, browser sessions, ledgers, receipts,
and customer evidence so reinstall and audit remain possible.

## Architecture

```text
host scheduler -> dedicated browser -> Storefront / Apply / Negotiate / Paid
                                     -> official marketplace readback
                                     -> durable ledgers -> Telegram receipt
```

Source stays in this repository. User state stays under `$GIG_STATE_DIR`, secrets
stay in `$LIFE_MANAGER_HOME/.env`, and browser authentication stays under the
external Cloak profile/vault. All four revenue lanes share the canonical agent
runner, browser fencing, KPI projector, and Telegram outbox.

## Security and platform policy

- The installer never copies work-profile data, cookies, credentials, or buyer
  evidence into Git.
- Marketplace effects require official readback; model output alone is not a
  sale, reply, delivery, or payment.
- Coconala account creation, KYC, bank linking, and the first official login are
  setup facts. Daily operation uses the dedicated authenticated browser profile.
- Telegram sends are event-keyed and provider-ACKed; an unknown ACK is not retried
  blindly.

## Troubleshooting

- `doctor` returns `login_required`: open its `login_url`, finish the official
  login in the configured marketplace profile, then run `doctor` again.
- An owner is `stopped`: run `start`, then inspect `status`; state is preserved.
- Telegram has no provider receipt: verify the report chat and OpenClaw Telegram
  transport, then run `start`; the daily event key prevents duplicate delivery.
- Disk pressure: free regenerable cache/build output only. Never delete
  `$GIG_STATE_DIR`, browser vaults, ledgers, or customer evidence.

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

The canonical owner set is `config/launchd/agents/gig.json`. Installer lifecycle
commands reject every plist that is not one of those seven labels.
