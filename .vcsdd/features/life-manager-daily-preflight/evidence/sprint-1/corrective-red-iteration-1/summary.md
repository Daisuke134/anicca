# Corrective Phase 2a RED — Phase 3 iteration 1

- phase: `2a`
- sprintCount: `0`
- Phase 3 iteration: `1/5`
- provider/network/L3/final report: `NOT USED`
- production/verifier-helper implementation diff from `0bb2047c04465edd047116b4f0a50eed95b7ad55`: `0`
- baseline focused: `51/51` GREEN (`baseline-focused.tap`)
- baseline full: `371/371` GREEN (`baseline-full.log`)
- eval: calendar `21/21`, late `12/12`, total `33/33` GREEN (`eval.log`)
- app-new: tests `63`, pass `55`, fail `8`, skipped `0` RED (`new-focused.tap`)
- poll/deadline: tests `12`, pass `6`, fail `6`, skipped `0` RED (`poll-deadline.tap`)
- final-schema: tests `45`, pass `44`, fail `1`, skipped `0` RED (`final-schema.tap`)
- purity contract: tests `6`, pass `5`, fail `1`, skipped `0` RED (`purity-contract.tap`)
- purity/provenance: tests `32`, pass `31`, fail `1`, skipped `0`; arithmetic remains `26 + 6 = 32` (`purity-provenance.tap`)
- verifier helpers: tests `12`, pass `7`, fail `5`, skipped `0` RED (`verifier-contracts.tap`)
- test beads: `75` total, `13` RED / `62` GREEN; finding beads: `11` OPEN

## Executable RED mapping

- TEST-007..TEST-012 -> FIND-003/FIND-004: the six `timeout:` / `deadline:` cancellation cases in `poll-deadline.tap`; the six final-attempt/no-attempt-7-or-4 cases pass against executed collector code
- TEST-013 -> FIND-001/FIND-005/FIND-011: `schema positive: actual offline CLI artifact is the closed 9/9 current-run report`
- TEST-058 -> FIND-002: `purity: exported production main rejects caller env/fetch/transport and never calls forged transport`
- TEST-065/TEST-066 -> FIND-007/FIND-010: both failing `verify-phase2-process.mjs` cases cover corrupt historical/hash/mode, trace, schema, scope/HEAD, and coverage inputs
- TEST-068 -> FIND-006/FIND-010: `verify-final-artifact.mjs: rejects closed-schema identity/order/time/binding/effects mutations and empty object`
- TEST-071 -> FIND-008/FIND-010: `verify-safe-scan.mjs: secret email phone raw-correlation and provider-ID fixtures fail without leakage`
- TEST-074 -> FIND-009/FIND-010: `verify-controlled-l3-gates.mjs: HEAD/tree/count/coverage/schema/scan/digest/output mutations all fail`
- All 12 helper definitions use synthetic phase-appropriate fixtures; the nominal fixture passes and five substantive verifier cases fail because the helper implementations accept corrupt fixtures, independently of mutable feature phase.
