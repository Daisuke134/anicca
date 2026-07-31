# CORE 8d — Phase 3 iteration-1 corrective Phase 2a RED only

Fresh `gpt-5.6-sol`. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `0bb2047c04465edd047116b4f0a50eed95b7ad55`, PR #330. No sub-agent. TDD RED only: do not modify production modules or verifier helper implementations, do not enter 2b, and do not close findings.

Read project rules, installed TDD/VCSDD Phase 2a instructions, feature state/approved contract/spec/verification architecture, Phase 3 manifest/verdict, and FIND-001..011. Read the absolute canonical root spec §9.5/§10 row 8d/§10.2/§10.3. The state is legally routed to `2a`, Phase 3 iteration 1/5, 11 finding beads open.

Strengthen/replace existing test bodies and test-only fixtures so every finding has a genuine executable RED before implementation. Preserve the approved exact arithmetic: app-new remains exactly 63 tests, helper remains exactly 12 tests, poll/deadline remains 12, final-schema remains 45, purity/provenance remains 32; do not add/delete/rename test cases merely to alter counts. Baseline focused/full/eval remains 51/371/33 GREEN. Existing test names may be clarified only if their mapped bead artifact path/count remains stable.

Required RED contracts:

1. FIND-001/005/011: an isolated, offline subprocess executes the actual production CLI entrypoint through a test-loader/provider boundary (outside production code), obtains a successful output file, and validates that exact emitted file with the real closed final-schema validator. It must fail now because production publishes the legacy report. No source-regex substitute and no hand-built final report.
2. FIND-002: executable behavior proves caller-supplied `env`/`fetchImpl`/transport objects cannot enter exported production `main`; the actual process path still works through an external test loader. A forged caller function must remain at zero calls. Keep test DI outside production modules.
3. FIND-003/004: executable time/cancellation tests run actual deadline/polling code with deterministic timers/abort observation. Prove final allowed attempt success, attempt 7/4/7 never occurs, timeout aborts underlying work, and no polling/provider effect continues after hard deadline. Constants/comments/regex alone cannot pass.
4. FIND-006: verifier tests feed a valid actual CLI artifact and mutations for unknown keys, wrong dependency identity/order/uniqueness, stale/mixed-run checkedAt, bad runRef/effects/source binding/mode. `verify-final-artifact` must reject every mutation; `{}` is invalid.
5. FIND-007: within the existing 3 cases for `verify-phase2-process`, exercise every mode. Valid fixtures pass; corrupt historical hash/mode, missing trace edge, invalid schema, stale/current-HEAD scope mismatch, omitted/sub-threshold module coverage all fail. Path existence alone cannot pass.
6. FIND-008: within existing safe-scan cases, a clean fixture passes and fixtures containing a synthetic secret, email, phone, raw correlation, and provider ID each fail without leaking matched content to stderr.
7. FIND-009: within existing controlled-L3-gate cases, a fully synthetic valid post-Phase3-PASS state/evidence snapshot passes; current HEAD/tree mismatch, missing GREEN count, coverage/schema/scan failure, contract digest mismatch, and pre-existing final output each fail. The current real Phase3-FAIL state is not a valid fixture.
8. FIND-010: helper contract tests remain 12/12 as test definitions, use phase-appropriate synthetic fixtures rather than assuming the mutable feature state is always valid, and expose the current helper implementations as RED for the substantive missing proofs rather than failing only because `currentPhase=2a/3`.

Production/source diff from `0bb2047c0` must be zero, including `apps/life-call/lib/daily-preflight.js`, collectors, mail-gog, CLI, and all four verifier helper implementations. Test-only loader/fixtures may be added under the feature tests or `apps/life-call` test-support path and must contain no real credentials/network.

Run and record fresh baseline GREEN and corrective RED. Store new iteration-specific evidence without overwriting Phase 2 RED/GREEN or Phase 3 review artifacts. Update only affected test-case bead statuses to RED with exact finding links; keep 75 total test beads and 11 finding beads open. State stays `2a`, sprintCount=0, Phase3 review/gate immutable. Global VCSDD index files remain byte-identical. No provider/network/L3/final-report/deploy/merge/root-spec changes.

Commit/push test/test-support/iteration-specific RED evidence/feature-local bead state only. Return `RESULT=CORRECTIVE-RED-READY` or `BLOCKED`; exact counts and failing test names mapped to FIND IDs; production diff=0; state/beads; commit; push; `NEXT=corrective Phase 2b GREEN`.
