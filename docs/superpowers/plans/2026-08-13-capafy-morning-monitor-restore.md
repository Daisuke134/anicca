# Capafy 09:30 Morning Monitor Restore Plan

**Goal:** Formally restore and prove the existing `ai.anicca.capafy-goal-monitor` 09:30 morning report without adding another reporter or changing working production code.

**Observed state:** The source and installed plist parse to the same launchd object: exact label, direct `capafy-goal-monitor.sh` invocation, `09:30`, `RunAtLoad=false`, HOME/PATH, and log paths. Their byte mismatch is XML formatting only. The loaded job is inactive at run 11 with last exit `0`; no manager-level report-kind or period override remains. The delivery ledger has no `morning:2026-08-13` key.

**Ponytail decision:** No production/test code changes. Item 5 already implemented the Japanese morning renderer and period-keyed dedupe; Item 6 proved the shared ledger and live monitor. The shortest correct restoration is exact source installation plus live E2E.

**Scope:** One plan file; expected production/source LOC change `0`.

## Execution

- [x] Run one fresh Sol adversarial read-only review of the no-code decision, current source/installed semantics, shared delivery ledger, morning-key derivation, and two-run acceptance path. Allow one Luna/Terra correction only if a Critical/Important code defect is reproduced.
- [x] Install the source plist byte-for-byte at mode `0644`. Do not bootout/rebootstrap because the already-loaded semantic job is identical and inactive.
- [x] Require source-installed `cmp`, SHA-256, `plutil`, and `launchctl print` readback of `Hour=9`, `Minute=30`, direct source script, inactive state, and no inherited report override.
- [x] Kickstart the existing label once. Require exit `0`, one new `morning:2026-08-13` delivery with a real Telegram message ID, Japanese 5 orders / 2 paid / `$19.98`, no new stderr, and unchanged 409-row revenue ledger SHA-256.
- [x] Kickstart the same label again. Require exit `0`, no new delivery, byte-identical delivery state, no new stderr, and unchanged revenue ledger SHA-256.
- [x] Update the authoritative Capafy spec with hashes, run numbers, message ID, body assertion, remaining stale sources, commit, and push. Then make Item 8 active.

## Rejected work

- Do not edit `capafy-goal-monitor.sh`; Item 5 already supplies the required behavior.
- Do not add tests solely to restate already-proved Item 5 dedupe contracts.
- Do not create a second 09:30 label, wrapper, state file, renderer, or scheduler.
- Do not use RED/GREEN or TDD; the owner explicitly directs straight implementation and live verification.

## Closure evidence

- The only fresh Sol adversarial review returned `ship` with zero findings and high confidence. It independently verified normalized source/installed semantics, the unique Capafy 09:30 label, unset overrides, morning key derivation, Japanese 5 / 2 / `$19.98` content, shared lock/state, and the no-code decision.
- Source and installed plist bytes now share SHA-256 `63d96bc4029817e4daa8b23b7583417a6b31f01d2ec3fa357fd14117f8e205ec`, mode `0644`; `plutil` passes and `launchctl` reads `Hour=9`, `Minute=30`.
- Existing job run 12 exited `0` and delivered `morning:2026-08-13` to real Telegram message `15934`. The rendered Japanese body contains 5 lifetime orders, 2 paid orders, `$19.98`, freshness, Builder, Marketer, repair/next action, listing, Reel/content, and dashboard URLs with no forbidden token.
- Run 13 exited `0` with delivery count still 5 and delivery SHA-256 unchanged at `0dfbfe83e66472cf36d9b43150f0db6cef27875d82cb7ddc7a5aa22ab27203d1`; no duplicate was sent.
- Across both runs the historical stderr SHA-256 stayed `288a462c276a71121542afa10efc0da982f8dc5bd46f4e50736f8db702ab6caf`; the revenue ledger stayed at 409 rows and SHA-256 `2729ed05e5504f9c6c26f684dca27fd35cdd2bc02d670a4971c0ffd5c6dc023e`.
- No production/test code was changed. Inventory, Instagram account, Marketing, and cost remain visibly stale.
