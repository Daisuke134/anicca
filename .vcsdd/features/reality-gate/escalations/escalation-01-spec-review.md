# Escalation 01 — Phase 1c (spec review) hit max iterations

- feature: reality-gate (lean)
- phase: 1c (spec-review gate)
- iterations run: 5 (limit 5)
- verdict at limit: FAIL (2 blocking)
- decided: 2026-07-12T18:09:22.948Z
- decided by: orchestrator (claude-p), no human loop

## Why escalate rather than abandon

Adversary #5 independently confirmed that iteration 4 blocking findings (FIND-H shared enforceVerdict module reaching the runtime path, FIND-I ground truth anchored to a fixed public surface + pre-committed fingerprint, FIND-J query-preserving canonicalization, FIND-K fail-closed automatedVerification, FIND-L no duplicated enforcement) are STRUCTURALLY fixed — not restated. Review convergence is real: findings are shrinking in scope and specificity each round (5 blocking -> 2 blocking), which is the VCSDD convergence signal, not thrash.

## The 2 remaining blocking findings are bounded and mechanical

- FIND-M: enforceVerdict composition order runs the automatedVerification refusal BEFORE validateArtifactProvenance. Because automatedVerification defaults false until Phase 2a proves platform diagnosability, the gate can only ever emit FAIL for the named first customer, and REQ-010 escalates every FAIL to self-fix -> a healthy loop self-fixes forever. This is the inverse of the false-PASS bug and equally fatal.
- FIND-N: passId is a caller-suppliable CLI argument, and the caller is the loop under test. gig_reality_verify.sh:100-105 (the mirrored precedent) generates pass_id INTERNALLY and never accepts it. A loop can pre-stage a forged artifacts.jsonl row under a self-chosen passId.

## Decision

Grant ONE bounded iteration (6) limited to FIND-M and FIND-N (+ majors FIND-O/FIND-P). No new scope. Re-review with a fresh adversary. If that review still returns blocking findings, stop and re-scope the feature rather than iterating further.
