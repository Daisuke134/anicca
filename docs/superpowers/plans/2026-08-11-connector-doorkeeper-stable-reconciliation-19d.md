# Connector Doorkeeper stable reconciliation 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna restores production/tests; Sol reviews, verifies, and integrates.

**Goal:** concurrent stable integrationで削除されたreview済みDoorkeeper public-trigger fresh-observation/latchを、現在のB4c factory配線を維持したまま復元する。

**Architecture:** 新しい実装は設計しない。commit `587c03f7a`が削除した、review済み`51656fd5b`のDoorkeeper限定WeakMap latch、action直前再観測、stale-token/button-impostor regressionだけを同じ2 Harness filesへ戻す。B4c minimal-production filesとlive stateは変更しない。

**Estimated change:** 2 files。production +10/-1、test +37。すべて既review済みdiffの復元。

## Constraints

- Modify only `apps/life-manager/lib/connector-production-browser-harness.js` and matching test.
- Test-first: restore the two deleted public-trigger regressions before production. Current stable must show stale-observation test RED while button-impostor remains GREEN.
- Production must match the reviewed net behavior at `51656fd5b`: Doorkeeper public actions re-observe immediately; successful exact modal trigger is latched by page + exact candidate canonical URL; non-Doorkeeper cache path remains unchanged.
- Same exact repeated trigger causes no second DOM click; changed live control/stale token and button impostor fail before DOM action. Final submit remains distinct and possible.
- Keep current B4c `doorkeeperWorkflow` factory injection and its tests byte-untouched.
- No official wake, provider action, Calendar, evidence, Telegram, schedule, launchd, session, target, or live-state change. Four labels stay UNLOADED.

## Task 1: Restore the reviewed public-trigger safety boundary

1. Restore only the two removed tests from reviewed commit `51656fd5b`; run their focused name pattern and confirm stale-observation RED for the intended reason.
2. Restore only the Doorkeeper public-boundary WeakMap/fresh-observation/latch production diff from `51656fd5b`.
3. Run focused two tests, all Doorkeeper Harness tests, full Harness, minimal production B4c, Doorkeeper workflow, syntax, and `git diff --check`.
4. Confirm exact two-file ownership and that diff against current base is equivalent to reversing `587c03f7a` for these files. Commit without amend and push.

## Completion gate

- Harness returns to 74/74; minimal production remains 15/15.
- Fresh Sol review finds no Critical/Important regression and returns SHIP.
- SSOT records the concurrent revert and final reviewed restoration without rewriting history.
