# TECH PLAY Exact Input Operation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development and test-driven-development task-by-task. Sol owns plan/review/verification/commit; Luna owns the two implementation files.

**Goal:** Execute only the already-inspected TECH PLAY required answers and seven default-on opt-outs through exact DOM bindings, with parent-owned deterministic selection and postcondition verification.

**Architecture:** Reuse the Browser Harness. The validated input inspector attaches ephemeral `data-lm-connector-control` tokens only after the whole same-event/same-ticket DOM contract passes. TECH PLAY input actions are selected in the parent: scalar answers and the unique exact radio option come from `createPrivateValueResolver`; opt-outs use `ax_uncheck`. The model never receives private values and is not asked to guess a radio answer. Every operation re-inspects the exact join page before mutation and again after mutation. Review/final submission remains blocked for the next slice.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connector-production-browser-harness.js` — about 45–75 production LOC.
- Modify `apps/mr-bot/lib/connector-production-browser-harness.test.js` — about 90–150 regression LOC.
- No new runtime module, service, state, selector registry, or dependency.

## Required contracts

- [x] Add RED tests proving the valid inspector binds one unique token to every scalar answer, each radio option, each opt-out, and the review CTA only after full validation; invalid/page-drift DOM leaves no actionable binding.
- [x] Add exact TECH PLAY candidate binding to Harness observation/action without enabling native provider order or schedule.
- [x] Map only `techplay_answer_*` scalar to `ax_fill`, exact approved radio option to `ax_check`, and `techplay_optout_*` to `ax_uncheck`. Reject ticket, review, final, wrong method/purpose, completed/non-required controls, token/URL/event/ticket drift, duplicate/missing locator, mutation error, and missing/false postcondition.
- [x] Select TECH PLAY input actions deterministically in the parent. Do not call the bounded model proposer for TECH PLAY input answers or opt-outs; for a radio group, only the unique control whose resolver result is `true` is selectable. Reject zero or multiple approved options.
- [x] Re-inspect immediately before operation and after operation. Success requires the exact selected control to change from `completed:false` to `completed:true` on the same join URL and same candidate binding.
- [x] Keep `同意して内容を確認する` and `申し込みを確定する` unclickable in this slice. No final-effect polling, provider readback success, evidence, Calendar, Telegram, factory/router/native order, schedule, or live application.
- [x] Run the full Browser Harness and TECH PLAY workflow tests, syntax checks, and `git diff --check`.
- [x] Mutation proof: remove either the unique approved-radio guard or postcondition requirement, prove its named negative fails, restore, rerun GREEN.
- [x] Fresh Sol correctness/privacy review; all Critical/Important findings return to the same Luna before ship.

## Live verification after ship

- [x] On the authenticated canonical candidate, use the shipped Harness path to fill the six exact answers and disable all seven opt-outs, but do not activate the review or final CTA.
- [x] Verify read-only inspection reports all answer/opt-out controls completed, review CTA submittable, final click count 0, private projection leak 0, and owned page cleanup back to baseline.
