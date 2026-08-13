# Capafy 09:30 Morning Monitor Restore Plan

**Goal:** Formally restore and prove the existing `ai.anicca.capafy-goal-monitor` 09:30 morning report without adding another reporter or changing working production code.

**Observed state:** The source and installed plist parse to the same launchd object: exact label, direct `capafy-goal-monitor.sh` invocation, `09:30`, `RunAtLoad=false`, HOME/PATH, and log paths. Their byte mismatch is XML formatting only. The loaded job is inactive at run 11 with last exit `0`; no manager-level report-kind or period override remains. The delivery ledger has no `morning:2026-08-13` key.

**Ponytail decision:** No production/test code changes. Item 5 already implemented the Japanese morning renderer and period-keyed dedupe; Item 6 proved the shared ledger and live monitor. The shortest correct restoration is exact source installation plus live E2E.

**Scope:** One plan file; expected production/source LOC change `0`.

## Execution

- [ ] Run one fresh Sol adversarial read-only review of the no-code decision, current source/installed semantics, shared delivery ledger, morning-key derivation, and two-run acceptance path. Allow one Luna/Terra correction only if a Critical/Important code defect is reproduced.
- [ ] Install the source plist byte-for-byte at mode `0644`. Do not bootout/rebootstrap because the already-loaded semantic job is identical and inactive.
- [ ] Require source-installed `cmp`, SHA-256, `plutil`, and `launchctl print` readback of `Hour=9`, `Minute=30`, direct source script, inactive state, and no inherited report override.
- [ ] Kickstart the existing label once. Require exit `0`, one new `morning:2026-08-13` delivery with a real Telegram message ID, Japanese 5 orders / 2 paid / `$19.98`, no new stderr, and unchanged 409-row revenue ledger SHA-256.
- [ ] Kickstart the same label again. Require exit `0`, no new delivery, byte-identical delivery state, no new stderr, and unchanged revenue ledger SHA-256.
- [ ] Update the authoritative Capafy spec with hashes, run numbers, message ID, body assertion, remaining stale sources, commit, and push. Then make Item 8 active.

## Rejected work

- Do not edit `capafy-goal-monitor.sh`; Item 5 already supplies the required behavior.
- Do not add tests solely to restate already-proved Item 5 dedupe contracts.
- Do not create a second 09:30 label, wrapper, state file, renderer, or scheduler.
- Do not use RED/GREEN or TDD; the owner explicitly directs straight implementation and live verification.
