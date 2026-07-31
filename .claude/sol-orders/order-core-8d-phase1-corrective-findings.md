# CORE-a 8d — correct Phase 1c iteration-1 findings only

Fresh `gpt-5.6-sol` spec/verification builder in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`, exact clean start `9bf5e1cf55c54688c92af2622535dddf7a49a331`, PR #330. Work on this one atomic only. Do not spawn another agent.

No production source/test changes, provider/network calls except git/gh, Telegram/email/phone, evidence JSON changes, deploy, merge, or Phase 2 start. Preserve historical evidence byte-for-byte/mode 0600. Read the iteration-1 verdict and FIND-001..004 before editing. Use installed VCSDD atomic state APIs; never hand-author a PASS or human approval.

## Main-orchestrator adjudication

- FIND-001 is accepted and routes to Phase 1a.
- FIND-003 and FIND-004 are accepted and route to Phase 1b.
- FIND-002's security concern is accepted, but its literal “booleans and hashes only” remedy is modified because a current 9/9 artifact must prove dependency identity/status, counts, and freshness. Define a **closed typed final schema** that permits only fixed schema/version enums, fixed dependency/status enums, booleans, bounded numeric counts, UTC freshness timestamps, and one-way `sha256:` references. Forbid arbitrary strings, raw classifications, paths/hosts/URLs, provider responses/errors/IDs, nonce, address, phone, location, subject/body, tokens, or secrets. Failure diagnostics must be a separate non-final channel with a closed safe failure enum and cannot be copied into a success artifact.

## Required corrections

1. Route the failed Phase 1c state back to the earliest affected phase through supported VCSDD transition tooling. Correct Phase 1a, then Phase 1b, and stop at `currentPhase=1b` awaiting fresh iteration-2 review. Keep sprintCount=0, contract draft/unapproved, humanApproved=false. Do not record a new adversary verdict yourself.
2. Correct REQ-018, PROP-010, and final checklist: Phase 1c legally means `currentPhase=1c` with adversary verdict recorded and humanApproved=false until explicit orchestrator approval; no 2a transition before both gates PASS. Do not require state to remain 1b after review begins.
3. Replace REQ-013 and related proof/CRIT language with the closed typed final schema adjudicated above. Add schema-negative cases for every forbidden field/class and nested unknown key.
4. Specify exact production polling boundaries, matching or deliberately tightening the real production contract after inspecting current source:
   - Telegram reply attempts/delay and first disallowed attempt;
   - Telegram webhook-drain attempts/delay and first disallowed attempt;
   - email inbox attempts/delay and first disallowed attempt;
   - exact per-call timeout and/or hard overall deadline so a provider call cannot make “bounded” unbounded in wall time;
   - boundary tests for final allowed attempt, first disallowed attempt, timeout after an authorized send, and zero duplicate sends.
   Any tighter timeout that requires Phase 2 code work must be explicitly listed as future RED, not falsely claimed implemented.
5. Replace verification command classes with exact executable commands from `apps/life-call`, exact expected exit/count contracts, concrete evidence paths, and source-snapshot binding. Include focused L1, full regression, eval 33/33, boundary assertions, security/sanitizer, purity/provenance, state/runtime/schema/diff validation.
6. Set numeric coverage acceptance to at least **90% lines and 90% functions for every changed production module**, with an exact executable coverage command and machine-readable output path. A combined average cannot hide a module below threshold.
7. Amend draft CRIT-001..005 only as needed so each corrected requirement has a binary criterion. Keep `status: draft`; no approval or contract-review PASS.
8. Update traceability beads/proof obligations via supported state tooling so every REQ→PROP→CRIT path remains valid. Do not create Phase 2 test beads or claim RED/GREEN evidence yet.
9. Write an iteration-1 finding-resolution record that preserves each original finding and records accepted/modified adjudication plus exact corrected artifact locations. Do not rewrite or delete the fresh verdict/findings.
10. Run state/runtime/artifact/contract schema validation, Phase-1 traceability validation, `git diff --check`, safe secret/PII counts, and historical evidence hash/mode checks. Stage only Phase 1 specs/contract/state/history/resolution artifacts. Commit/push and verify local=upstream=origin=PR head. Do not merge.

Return exactly:

```text
RESULT: ITERATION-2-REVIEW-READY | FAIL
FINDINGS_ADDRESSED: FIND-001..004 with corrected locations
STATE: phase=1b adversaryIteration1=FAIL humanApproved=false sprintCount=0
SCHEMA: closed final fields + forbidden classes
POLL_BOUNDS: exact attempts/delays/timeouts/deadlines
COMMAND_MATRIX: exact commands/counts/paths/coverage threshold
VALIDATION: commands/exits
COMMIT: <hash or none>
PUSH: <remote/PR equality>
NEXT: fresh Phase 1c iteration-2 only
```
