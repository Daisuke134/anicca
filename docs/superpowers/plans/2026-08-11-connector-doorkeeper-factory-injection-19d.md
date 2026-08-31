# Connector Doorkeeper factory injection 19D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and verifies.

**Goal:** Official production factoryが生成したDoorkeeper workflowをdefault Browser Harnessへ渡し、Doorkeeper fallbackのparent readbackへ本線から到達できるようにする。

**Architecture:** 既存`createDoorkeeperScriptFirstWorkflow`、provider router、Browser Harnessをそのまま再利用する。factoryのHarness constructionへ既存workflow参照を一つ渡すだけで、新しいprovider abstractionやbrowser railは作らない。

**Estimated change:** 2 files。production 1 LOC、test 20〜35 LOC。

## Constraints

- Modify only `apps/mr-bot/lib/connector-minimal-production.js` and matching test.
- RED must prove the default factory-created Harness—not an injected Harness—uses the factory Doorkeeper workflow for fallback readback.
- No browser rail/session/target creation in the test; inject page/control transport boundaries only.
- Existing Luma/Connpass/Peatix/Meetup injection and provider order stay unchanged.
- No native runner, operations, discovery audit, profile, evidence, schedule, or live state change.
- Official wake 0; all four Connector labels remain UNLOADED.

## Task 1: Pass the existing Doorkeeper workflow into the default Harness

1. Add a focused factory test that constructs default Browser Harness dependencies with an injected Doorkeeper workflow and safe control boundaries, then runs Doorkeeper fallback far enough to prove that workflow's `readProviderState` is called. Run RED and confirm the missing workflow causes the intended failure.
2. Pass `doorkeeperWorkflow` to `createProductionBrowserHarness` beside the other provider workflows.
3. Run `connector-minimal-production.test.js`, Browser Harness and Doorkeeper workflow adjacent tests, syntax checks, and `git diff --check`.
4. Confirm exact two-file ownership, commit without amend, and push the slice branch.

## Completion gate

- Factory-created default Harness reaches Doorkeeper parent readback.
- No browser rail call or external effect occurs.
- Focused and adjacent tests pass; fresh Sol review returns SHIP.

## Result

Luna added one production line passing the factory-created `doorkeeperWorkflow` into the default `createProductionBrowserHarness`, plus one production-equivalent regression test that leaves `browserHarness` uninjected. RED observed `failed` with Doorkeeper readback/click 0; GREEN observes completed, workflow parent readback 1, safe click 1, and browser rail 0.

Fresh Sol review returned SHIP with Critical/Important 0. Sol independently verified factory `15/15`, Harness + Doorkeeper workflow `87/87`, syntax, diff, two-file scope, and unloaded live boundary. Because the implementation branch inherited an unrelated rejected merge, Sol integrated only the reviewed implementation commit by cherry-pick as `4f77b43fd`; the rejected merge and its documentation were separately reverted on stable before integration.
