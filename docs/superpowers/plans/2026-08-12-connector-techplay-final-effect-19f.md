# TECH PLAY Final Action and Registered Readback Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/integration verification/commit; Luna owns the exact two Harness files.

**Goal:** From a validated same-event TECH PLAY confirmation page, click the unique final application CTA at most once and report success only after the parent-owned TECH PLAY workflow proves the same event and ticket are registered.

**Architecture:** Reuse the existing Harness final-effect latch and the shipped `techplayWorkflow.readProviderState`. Add TECH PLAY as an optional Harness workflow, bind only `techplay_final_<eventId>` on exact `/event/join/<eventId>/confirm`, arm registered-only readback before one exact click, and never retry an attempted final effect. Keep the custom deterministic TECH PLAY loop: `maxSteps=14` still stops at `final_blocked`; `maxSteps>=15` may perform the final action and return success only with `{status:"registered"}`.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connector-production-browser-harness.js` — about 35–65 LOC.
- Modify `apps/mr-bot/lib/connector-production-browser-harness.test.js` — about 75–130 LOC.

## Grounding

- TECH PLAY official event page: <https://techplay.jp/event/999190> — public page states `イベントに参加する`, the event is in-person, and the ticket is `無料` with current capacity.
- Existing Harness final-effect reference: `startFinalEffectWait` already arms before click, polls for 30 seconds, and returns `effect_unknown` when the effect cannot be proven.
- Existing TECH PLAY workflow reference: `readProviderState` returns `registered` only when the canonical event payload has the same event ID, the same sole ticket ID, and `is_joined === true`; `pending` is not a TECH PLAY success state.
- Two independent GitHub code searches for TECH PLAY join/final implementations returned no reusable public implementation. The local final-effect latch is the first reusable rung.

## Contract

- [x] RED: exact confirm currently stops at `final_blocked`; no final operation or TECH PLAY readback runs.
- [x] `createProductionBrowserHarness` accepts optional `techplayWorkflow` only when it exposes `readProviderState`.
- [x] Select only one exact final control: same event token, `button`, label `申し込みを確定する`, `required:false`, `completed:false`, `submittable:true`, exact same-event confirm URL, and exact event/canonical/ticket binding before and immediately before click.
- [x] Arm the existing 30-second final-effect latch before one exact final click. Accept only parent readback `{status:"registered"}`; `pending`, `absent`, `unavailable`, malformed, rejection, or timeout never count as success.
- [x] A click throw may succeed only when registered readback proves the effect. Any attempted-but-unproven final effect returns `effect_unknown`, records the final action once, and never retries. Pre-click rejection records no final action.
- [x] Full deterministic path is 13 inputs + review + final = 15 private-free actions, external proposer 0, final click 1, and a successful provider state `registered`. `maxSteps=14` retains the previously accepted `final_blocked` boundary.
- [x] Add negative tests for wrong/missing workflow, method/purpose/token/label/state, duplicate/missing locator, page/event/ticket drift, readback pending/absent/unavailable/malformed/reject/timeout, and click throw with registered versus unknown effect.
- [x] Run Harness + TECH PLAY workflow, syntax, diff check, final one-shot mutation proof, and fresh Sol review.
- [x] Do not perform a real final application in this slice. The real side effect is reserved for the existing launchd owner after TECH PLAY Calendar/evidence/native/report wiring is complete, so registration cannot be orphaned from its operational bundle.
