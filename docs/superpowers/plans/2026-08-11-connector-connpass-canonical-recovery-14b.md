# Connector Connpass canonical evidence recovery Item 14B plan

## Goal

Recover a parent-verified Connpass registration after the provider leaves the owned page on a join or completion URL. Before evidence, return the same owned page to the exact candidate canonical URL and repeat parent readback. Create evidence only when that canonical page independently reports `registered` or `pending`; never repeat Submit during recovery.

## Live evidence

- Official wake `wake-546099b19a3ad84aef0742e3` exhausted Luma candidates, found Connpass event `400028`, observed pre-submit `absent`, ran cache then direct action, and observed post-action registered/pending.
- `completeEvidence` then failed closed as `circuit_open/evidence_completion_failed`; every-wake Telegram delivery ID was `11138`.
- Connpass bundle, receipt, artifact marker, immutable object, and checkpoint counts all remained zero. The failure therefore occurred before store record and all Calendar/evidence Telegram/bundle effects.
- The production direct action clicks the event application link and does not restore the candidate canonical URL. The minimal evidence chain requires exact current page URL before any Connpass evidence action. This is the only new boundary introduced immediately before the live failure and is the strongest supported cause; raw exceptions are intentionally not persisted.

## Ponytail full gate

- Reuse the existing runner action wrapper, browser rail, provider readback, evidence chain, owned page, and failure reporting.
- Add no provider method, checkpoint schema, retry, session, target, page, queue, or schedule.
- Do not weaken the exact URL gate and do not let evidence trust the state observed on a join/completion page.
- Recovery is exactly one same-page canonical navigation plus one canonical parent readback. If either fails or the state is not `registered|pending`, stop safely with no cache/direct/Harness/Submit retry.

## Luna implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-minimal-runner.test.js`
2. `apps/mr-bot/lib/connector-minimal-runner.js`

Soft target: 2 files; production `+10–20 LOC`; tests `+30–55 LOC`.

### RED

Build one Connpass fixture: pre-submit absent, cache miss, direct completed, post-submit registered on a noncanonical join/completion URL, and evidence accepts only the canonical URL. The current runner must fail because it calls evidence before canonical recovery.

### GREEN

- For Connpass only, after a registered/pending result and before `completeEvidence`, navigate the existing owned page to `selected.canonical_url` through the existing browser rail.
- Repeat provider readback on that canonical page through the existing action wrapper. Replace the earlier state only if the new state is `registered|pending`; otherwise return the existing safe evidence failure without any Submit path.
- Assert one session/target/page, one final cleanup, one cache/direct sequence, Browser Harness zero in this fixture, canonical navigation exactly one, canonical readback exactly one, evidence exactly one, and duplicate Submit zero.

## Verify and live close

- Focused RED/GREEN, runner/evidence/production regression, syntax, and diff check.
- Fresh Sol review for action ordering, exact canonical identity, no repeat Submit, and cleanup.
- Update SSOT, commit, and push before another official wake.
- The next official wake is a recovery wake. Acceptance requires canonical pre-readback or canonical recovery readback `registered|pending`, provider Submit zero, exact Connpass bundle one, Calendar exact one, positive Telegram message/photo/every-wake IDs, and normal cleanup.

## Result

- RED reproduced the live boundary: Connpass direct action left the page on a join URL and the current runner returned `circuit_open/evidence_completion_failed` before evidence.
- GREEN adds one Connpass-only canonical navigation and action-wrapped parent readback after a completed operation. Navigation, readback, or nonregistered-state failures stop before evidence and never re-enter cache/direct/Harness/Submit.
- Fresh review found the first condition also recovered an already-registered canonical pre-readback. A second RED showed the extra navigation/readback; GREEN limits recovery to a completed operation. Already-registered now uses initial navigate one, Submit zero, recovery zero, evidence one.
- Final diff is the two owned files, production +13 LOC and tests +50 LOC. Sol independent adjacent regression passes 82/82; syntax and diff check pass. Fresh Sol re-review: `ship`.
