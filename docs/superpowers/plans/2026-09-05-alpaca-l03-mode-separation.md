# Alpaca L03 Structural Mode Separation Plan

## Goal

Make the existing finite Alpaca pass select exactly one `paper|shadow|live` mode before broker access, with mode-specific credential references, broker endpoints, receipt namespaces, and effect permissions. Preserve the currently running paper loop and its state.

## Non-goals

- No live-account signup, KYC, funding, or order.
- No live risk policy, Telegram command surface, cloud scheduler, migration, coordinator, or failover.
- No dashboard edit, removal, or new publisher path.
- No strategy, allocator, campaign, cadence, or deployment-profile redesign.

## Minimal design

- Require exact `LIFE_MANAGER_INVESTMENT_MODE=paper|shadow|live` before broker access.
- Resolve a mode-specific credential-file environment variable and state directory. Keep paper pointed at the current paths so production history is not abandoned.
- Broker context accepts the selected mode: paper requires the paper endpoint/key fields and forces the CLI live flag off; shadow/live require the live endpoint/key fields and turn the CLI live context on. A paper credential record therefore cannot authenticate a live context.
- Shadow is structurally read-only: both campaign-exit and allocator submission paths are denied before `submit_order`.
- Put `mode` on every decision/effect/outcome receipt, every successful stdout summary, and every Telegram success/failure report.
- Generated local Alpaca plist explicitly installs `mode=paper` plus the paper-specific credential and state references.

## Tasks

1. [x] Add focused failing tests for exact mode selection, separated paths/endpoints, shadow submit denial, receipt mode, Telegram mode, and paper plist values.
2. [x] Implement the smallest production wiring in the existing Alpaca runner, CLI boundary, receipt store, reporter, and targeted plist renderer.
3. [x] Run focused tests, registry tests, doctor, and the existing relevant runtime suite; obtain a fresh read-only adversarial review.
4. [x] Merge the implementation, cut one immutable main release, apply only `alpaca-investment` after `launchctl-safe` preflight, and verify a natural paper wake reports `mode=paper` in stdout, receipts, and Telegram.
5. [x] Record production evidence, merge it, report the milestone to Telegram, then advance only to L04.

## Acceptance criteria

- Missing, empty, padded, uppercase, comma-combined, or unknown mode fails before any broker call.
- Paper and live contexts cannot reuse each other's endpoint/key fields; shadow uses the live read context but cannot submit.
- Paper preserves the current state directory; shadow and live require distinct configured state directories.
- Every newly written receipt and every Telegram report exposes the selected mode.
- The installed local job remains paper-only and its next natural wake succeeds without a dashboard call.
- No live broker mutation occurs in L03.

## Expected size

Five existing production files plus focused existing tests and this plan, approximately 120 production LOC or less. The five boundaries are irreducible for the named acceptance gate; no new framework or dependency is introduced.
