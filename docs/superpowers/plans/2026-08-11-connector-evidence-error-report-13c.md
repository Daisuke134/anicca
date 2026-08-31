# Connector evidence-error every-wake report Item 13C plan

## Goal

Convert a thrown evidence-completion error into one safe terminal wake report so every official wake has a positive durable Telegram receipt while Item 12 checkpoints preserve partial external effects for the next wake. Do not retry evidence or provider Submit in the same wake.

## Live failure evidence

- Official wake `wake-b3f05e7a9c4a5afc322e3d2d` successfully reused the accepted Peatix bundle: candidate one navigate/readback was followed by candidate two navigate/readback with zero cache/direct/Harness Submit rows between them.
- Later Peatix event `5065833` was already `registered`, also with Submit zero. The chain durably stored provider receipt/PNG, exact Calendar event/readback, and message checkpoint with positive Telegram ID `11079`.
- Photo delivery failed. `completeEvidence` threw, `native-pass` exited 2, and the runner wrote no terminal wake report/delivery. Bundle delta remained zero.
- Process/lock/owned page cleaned up, CDP returned to one newtab, four labels stayed unloaded, Git stayed clean/upstream `0/0`.

## Ponytail full gate

- Reuse runner `finish`, Item 12 partial checkpoints, existing report operations, and next-wake recovery. Add no retry, queue, exception store, provider action, evidence change, browser action, schedule, or new state.
- Change only runner production/test. Never include the raw exception or private data in safe reason/history/report.
- Stop the current wake after the evidence exception. Recovery belongs to the next official wake; same-wake evidence retry risks duplicate ambiguous effects.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-minimal-runner.test.js`
2. `apps/mr-bot/lib/connector-minimal-runner.js`

Soft target: 2 files; production +5–12 LOC; tests +30–60 LOC.

### RED

1. `completeEvidence` throws after a parent `registered` readback. Runner does not throw; it terminates exactly once as `circuit_open / evidence_completion_failed`.
2. Failure count increments once within the existing 0–3 bound. Cache/direct/Harness remain zero for the registered candidate, and no evidence retry occurs.
3. Owned page cleanup occurs once.
4. Real `createMinimalProductionOperations` persists report row one and delivery row one, mode 0600, positive provider ID, send one, with no raw error text.
5. Existing malformed-result reporting, `created` terminal, `reused` continuation, all-reused reason, and circuit/deadline behavior remain unchanged.

### GREEN

- Catch only the `completeEvidence` call boundary.
- Increment the bounded consecutive failure count once and return the existing `finish("circuit_open", "evidence_completion_failed")` path.
- Preserve the finally cleanup and never call evidence or Submit again in the same wake.

## Verify

- Focused runner and operations; evidence, minimal production, Peatix workflow/store/Harness, native entrypoint; syntax; `git diff --check`.
- Fresh Sol review for catch scope, error sanitization, exact-once reporting, failure count, cleanup, no retry/Submit, and created/reused non-regression.
- Update SSOT, commit, push, then run one official foreground recovery wake with schedules unloaded. Item 13 completes only when saved message is reused, photo/final bundle are completed, a positive every-wake report is durable, and cleanup passes.

## Result

- RED reproduced the defect in two tests: a thrown `completeEvidence` error escaped the runner and omitted the terminal wake report.
- GREEN catches only that call boundary, increments the existing bounded failure count once, and returns the existing `circuit_open / evidence_completion_failed` terminal path. The same wake performs no evidence retry and no cache/direct/Harness Submit.
- Ponytail reduced the final scope to the two owned files, production `+13/-7` and tests `+59/-10`. No provider, evidence, Calendar, Telegram, browser, state schema, or schedule production code changed.
- Luna's serialized focused and adjacent suites passed except the unchanged date-dependent Peatix baseline. Sol independently ran the authoritative runner/operations/evidence/production/Harness/entrypoint/contract/outbox set at `63/63` PASS; syntax and `git diff --check` passed.
- Fresh Sol review returned `ship` with Critical 0 and Important 0. Live acceptance remains the next exact-one official foreground wake with all four schedules unloaded.
