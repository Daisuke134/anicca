# CORE 8d — rescue uncommitted corrective RED; fix bead ledger and finish

Fresh `gpt-5.6-sol`. Resume only the intentionally dirty worktree `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`, whose HEAD remains exact `0bb2047c04465edd047116b4f0a50eed95b7ad55`. The prior Sol was interrupted before commit because it incorrectly marked all 75 test beads RED. Preserve and independently audit the uncommitted executable test/test-support/evidence changes; do not discard them. No sub-agent.

The already captured raw evidence is authoritative: baseline focused/full/eval=`51/371/33` GREEN; app-new=`63` with 55 pass/8 fail; poll=`12` with 6 pass/6 fail; final-schema=`45` with 44 pass/1 fail; purity=`6` with 5 pass/1 fail; helpers=`12` with 7 pass/5 fail. Production and verifier-helper implementation diff from HEAD must remain zero.

Correct only the ledger/evidence inconsistency and any genuine test-fixture defect discovered by a fresh rerun:

- Reconstruct test-case bead statuses from the clean HEAD state, then mark exactly these 13 existing beads RED and keep the other 62 GREEN:
  - `TEST-007..TEST-012` — six executed timeout/deadline cancellation failures, link FIND-003/FIND-004;
  - `TEST-013` — actual CLI emitted artifact failure, link FIND-001/FIND-005/FIND-011;
  - `TEST-058` — production-main caller injection failure, link FIND-002;
  - `TEST-065`, `TEST-066` — substantive phase2-process corruption/scope failures, link FIND-007/FIND-010;
  - `TEST-068` — final-artifact mutation failure, link FIND-006/FIND-010;
  - `TEST-071` — real safe-scan content failure, link FIND-008/FIND-010;
  - `TEST-074` — L3 gate mutation failure, link FIND-009/FIND-010.
- Do not change the 11 adversary-finding beads: all stay OPEN.
- Fix `corrective-red-iteration-1/summary.md` to say 13 RED / 62 GREEN, not 75 RED.
- Ensure the five helper failures are due to the helper implementations accepting a corrupt substantive fixture, not a broken nominal fixture or current-phase mismatch. Ensure the eight app failures are due to the exact missing production behavior. Preserve exact 63/12/12/45/32 arithmetic.

Run fresh baseline and RED commands. Confirm state=`2a`, sprintCount=0, Phase3 gate/review immutable, 75 total test beads = 13 red + 62 green, 11 finding beads open. Confirm no changes to the four production modules or four verifier-helper implementations, global VCSDD index files, Phase2/Phase3 historical artifacts, canonical spec, provider/network/L3/final report/deploy/merge.

Commit/push only the legitimate test/test-support/iteration-specific RED evidence/state changes already in the worktree. Return `RESULT=CORRECTIVE-RED-READY` or `BLOCKED`; counts; exact 13 RED bead IDs and finding mapping; production/helper implementation diff 0; validation; commit; push; `NEXT=corrective Phase 2b GREEN`.
