# Connector reused-bundle continuation Item 13B plan

## Goal

Teach the minimal runner to treat a validated `reused` bundle as an already-complete candidate, skip every Submit path for that candidate, and continue on the same owned session/target/page to the next candidate. A `created` bundle still ends the wake as `applied_bundle`. Every terminal wake must persist one positive Telegram report receipt through the existing production operations.

## Current evidence

- Item 13A is pushed at `40bf22de7`. The real evidence chain now returns runtime `completion_disposition: created|reused` only after exact bundle/provider/artifact/current-Calendar validation.
- The runner currently ends immediately after every `applied_bundle`, so a validated reused candidate prevents later candidates from being evaluated.
- The runner already performs parent pre-submit readback before cache/direct/Harness and reuses one owned session/target/page across candidates.
- `createMinimalProductionOperations.reportWake` already persists one exact wake report and one positive Telegram delivery receipt with idempotency by wake ID.

## Ponytail full gate

- Reuse the existing runner loop, parent readback, evidence result, finish/reportWake, action history, and production operations. Add no queue, coverage set, database, new state file, provider code, evidence code, browser action, schedule, or retry.
- Change no evidence/provider/operations production file. Item 13B owns only runner production/test.
- Require the explicit 13A disposition. Do not infer reuse from pre-submit registration alone; a registered event without complete exact evidence must still complete evidence and stop when a new bundle is created.
- Continue only on `reused`. `created` remains the one terminal new-effect outcome.
- Preserve same owned session/target/page and current candidate ordering. Do not rediscover or rank.

## Implementation slice

Luna owns only:

1. `apps/mr-bot/lib/connector-minimal-runner.test.js`
2. `apps/mr-bot/lib/connector-minimal-runner.js`

Soft target: 2 files; production +15–35 LOC; tests +70–120 LOC.

Final size: production +16/-2 LOC and tests +116/-3 LOC, both inside the soft target after fixture compression.

### RED

1. Candidate one parent pre-readback is `registered`; real or contract-faithful evidence returns `reused`. Cache/direct/Harness calls for that candidate are zero, no wake report is emitted yet, and candidate two is navigated on the same session/target/page.
2. Candidate two creates a new verified bundle. The wake ends once with `applied_bundle`, its bundle ID, and a positive every-wake Telegram provider ID.
3. If all candidates return `reused`, the runner ends once with `completed_no_effect / existing_bundles_reused`, failure count zero, positive Telegram ID, and owned page cleanup.
4. A registered candidate whose evidence returns `created` still stops immediately; no next candidate navigation.
5. Missing, unknown, non-string, or contradictory disposition fails closed. `reused` still requires valid `applied_bundle` status and non-empty bundle ID.
6. A real runner plus `createMinimalProductionOperations` fixture persists one wake-report row and one mode-0600 delivery row with the positive provider ID; duplicate report delivery is zero.
7. Existing cache/direct/Harness created-bundle, circuit, deadline, provider continuation, cleanup, and report tests remain unchanged except for the now-required explicit disposition in their evidence doubles.

### GREEN

- Exact-validate `completion_disposition` as `created` or `reused` after every complete evidence result.
- A malformed evidence result or disposition terminates once as `circuit_open / evidence_result_invalid` or `evidence_disposition_invalid` through the existing `finish` path, preserving one positive every-wake report receipt and owned-page cleanup. It never throws past reporting merely because the result contract is malformed.
- For `created`, call the existing terminal `finish(applied_bundle)` path.
- For `reused`, set one wake-local observation flag and continue the current candidate loop without changing failure count, session, target, page, provider order, or action cache.
- At normal exhaustion, report provider discovery failure when present; otherwise report `existing_bundles_reused` when at least one exact bundle was reused, else `providers_exhausted`.
- Keep `finish` as the sole every-wake Telegram delivery point. Use the existing production operations in test to verify durable positive delivery rather than adding runner state.

## Verify

- Focused runner and operations suites; evidence, minimal production, Peatix workflow/store/Harness, native entrypoint; changed-file syntax; `git diff --check`.
- Fresh Sol review for strict disposition validation, new-vs-existing semantics, per-candidate Submit zero, same page/session continuation, failure-count behavior, report priority, durable positive every-wake receipt, cleanup, and no loop/duplicate report.
- Update SSOT, commit, and push. Item 13 remains open until 13C official schedule-unloaded foreground wake proves the live reused Peatix bundle, Submit zero continuation, later candidate handling, positive Telegram report ID, and cleanup. Keep schedule unloaded.

## Result

- Luna reproduced four runner failures, then exact-validated `created|reused`. `reused` continues the current candidate loop on the same owned session/target/page without changing failure count; `created` remains terminal `applied_bundle`.
- All-reused exhaustion reports `completed_no_effect / existing_bundles_reused`; provider discovery failure retains priority. Real production operations persist one positive mode-0600 wake delivery/report and dedupe a duplicate report.
- Fresh review found malformed evidence results escaped without every-wake reporting. Luna changed only this contract boundary: malformed result/disposition terminates once as a safe circuit-open reason through `finish`, with report one, cleanup one, and cache/direct/Harness Submit zero.
- Luna focused runner 20/20, operations 8/8, and all named adjacent suites passed apart from three unchanged baselines. Sol independently reran the frozen expanded suite at 110/110 plus syntax and `git diff --check`; final re-review returned `ship`.
- Item 13B is complete. Item 13 remains open for the 13C official foreground wake. Schedule remains unloaded.
