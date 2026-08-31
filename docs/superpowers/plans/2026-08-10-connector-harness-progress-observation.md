# Connector Browser Harness Progress Observation Plan

> **For Luna:** Use Superpowers test-driven-development. Own only the two Harness files below. Do not edit the SSOT/plan, commit, push, browser, state, private profile, or external systems.

**Goal:** Make the bounded same-page Harness advance after a parent-owned value is filled, without observing or exposing that value, and preserve candidate-separated agent evidence on the shared target.

**Measured live failure:** In official wake `wake-db550678c5bda2cf1f3890bb`, Peatix candidate 2 ran all 10 steps and selected the same `fill/ax_fill/control_4` every time. The DOM action succeeded but observations were indistinguishable because controls expose no completion state. Candidate 3 reused the same target/step evidence path, overwriting earlier step evidence.

**Ponytail scope:** Reuse the current observer, safeControl, proposer, Harness registry, and evidence writer. Two files only; production <= 35 added/changed LOC, tests <= 55. No new module, schema, store, model, provider, retry, session, target, page, prompt value, or external action.

**Files:**

- Modify: `apps/mr-bot/lib/connector-production-browser-harness.js`
- Modify: `apps/mr-bot/lib/connector-production-browser-harness.test.js`

## Contracts

1. RED first: after a successful text fill, the next observation currently exposes the same control as actionable and the proposer can select it again.
2. `safeControl` carries only a boolean `completed`; it never carries input value, selected value, checked option text beyond the already-public sanitized label/question, or private profile data.
3. Default observation computes:
   - text/textarea completed only when the current value is non-empty;
   - select completed only when it has a non-empty selected value;
   - checkbox completed only when checked;
   - every radio in one exact `name` group completed when one option in that group is checked;
   - button/link completed false.
4. The proposer receives all sanitized controls with `completed`, but its structured `control` enum excludes completed input/textarea/select/checkbox/radio controls. The prompt explicitly requires choosing only incomplete parent-owned fields before submit.
5. If no actionable control remains, fail closed before the agent call. Unknown provider/control and current max-10/same-page constraints remain unchanged.
6. `performAction` rejects a fill/check/click answer action against a completed control before DOM action. Cached replay may fail safely and continue through existing direct/fallback routing.
7. `createBoundedActionProposer` keeps an in-process per-target fallback sequence. Every `step===1` starts the next sequence; subsequent steps reuse it. Evidence path becomes `target-<id>/fallback-<positive sequence>/step-<step>`, contains no candidate identity, and never reuses one candidate's path for the next candidate on the same target.
8. No private value or dynamic page state is persisted or sent to the model.

## TDD and verification

1. Add focused RED tests for completion booleans, completed-control enum exclusion, no-value leakage, completed DOM-action rejection, radio-group completion, no-action fail-close, and two candidate fallback evidence paths on one target.
2. Run the focused test and record RED failures before production edits.
3. Implement the smallest GREEN.
4. Run focused Harness, minimal-production/runner adjacent, native contracts, syntax, and diff checks.
5. Return RED evidence, GREEN counts, exact LOC, and residual live limitation to Sol. Sol owns fresh review, SSOT, commit/push, and one official live wake.

## Implementation status

- [x] RED reproduced five measured completion/evidence failures before production edits.
- [x] Primary Sol regressions close unnamed-radio grouping, repeated same-page activation, and legitimate path-transition reuse.
- [x] Fresh Sol review regressions close raw-name exactness and activation-method bypass.
- [x] Focused 28/28, adjacent 23/23, native 7/7, syntax, and diff checks pass; fresh re-review ships.
- [ ] Official schedule-disabled live wake remains Sol-owned acceptance.
