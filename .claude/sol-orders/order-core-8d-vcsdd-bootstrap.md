# CORE-a 8d receipt corrective: restore missing VCSDD Phase 1 artifacts

Fresh `gpt-5.6-sol` builder in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d`, branch `feature/lm33d-daily-preflight`, exact start `58846034b4505f585bd8b4ea3fbcaa04c38e31bc`, PR #330. Do not spawn another agent.

The independent review log `.claude/sol-orders/logs/core-8d-receipt-fresh-review.log` is FAIL because `.vcsdd/features/life-manager-daily-preflight/` contains only evidence JSON and lacks VCSDD state/spec/verdict artifacts. The code behavior itself freshly passed focused 51/51, full 371/371, eval 33/33, and boundary assertions 10/10. The main orchestrator independently verified PR #330 head equals `58846034b`; do not treat the reviewer's network-prohibited PR check as a code defect.

This order repairs process truth only. Do not change production source/tests, run providers/network except git fetch/push/gh PR read, send Telegram/email, dial phone, read inbox, deploy, merge, or create production evidence. Preserve both existing evidence JSON files byte-for-byte and mode 0600. Never fabricate a gate, approval, command output, chronology, or human verdict.

Read completely before acting:

- `/Users/anicca/.codex/RTK.md`, project `AGENTS.md`.
- Installed VCSDD operational docs under `/Users/anicca/.codex/plugins/cache/vcsdd-claude-code/vcsdd/1.0.0/`: `VCSDD.md`, `commands/vcsdd-init.md`, `commands/vcsdd-spec.md`, `commands/vcsdd-spec-review.md`, `commands/vcsdd-tdd.md`, `commands/vcsdd-impl.md`, `commands/vcsdd-adversary.md`, `commands/vcsdd-harden.md`, `commands/vcsdd-converge.md`, state schema and state library/API. Follow the repo phase sequence 1a→1b→1c→2a→2b→2c→3→4→5→6.
- Canonical spec §9.5, §10 row 8d, §10.0, §10.2, §10.3.
- Exact correction diff `f6129abb5..58846034b` and relevant source/tests only.
- Original TDD logs `.claude/sol-orders/logs/core-8d-receipt-precision-fix.log` and `core-8d-receipt-precision-resume.log`; verify their hashes and locate exact RED-before-GREEN output without trusting prose.

Required work:

1. Verify clean exact start/local/upstream/origin/PR head and existing artifact hashes/modes.
2. Initialize `.vcsdd/features/life-manager-daily-preflight/` in strict mode using installed VCSDD state tooling. Never manually invent or directly mutate `state.json`; use the supported atomic state library/commands and validate against schema/runtime verifier.
3. Author Phase 1a behavioral spec for the complete CORE 8d closed production preflight and the narrow method-2 receipt precision correction. Requirements must include nine dependencies, exact nonce/provider/owned-recipient correlation, minute closed interval, exact timestamp, impossible dates, freshness, sanitized evidence, no transport/test injection, one-shot send limits, no phone, and historical artifact immutability.
4. Author Phase 1b verification architecture with explicit L1/L2/L3 proof obligations, deterministic boundary tests, production provenance/purity checks, RED/green evidence contract, sanitizer/security checks, controlled side-effect budget, and final artifact review.
5. Create a strict sprint contract draft with CRIT identifiers and traceability. Do not set `status: approved`; human/orchestrator approval and fresh contract/spec review have not happened.
6. Record only truthful Phase 1a/1b state transitions and stop at the Phase 1c review gate. Do not record Phase 1c PASS or advance to 2a. No retroactive Phase 3/4/5/6 claims.
7. Preserve original TDD log hashes and references in a provenance note, but do not yet call them accepted VCSDD RED/GREEN evidence; Phase 2 will adjudicate/replay them after 1c.
8. Update worktree canonical spec row 8d/§10.0 to record: fresh implementation review FAIL due missing VCSDD process artifacts, code verification counts, PR head independently confirmed by orchestrator, VCSDD Phase 1 artifacts restored and waiting fresh Phase 1c review. Keep row pending.
9. Run VCSDD state/runtime validation, schema checks, `git diff --check`, secret/PII scan with safe counts. Stage only `.vcsdd/features/life-manager-daily-preflight/` process artifacts and the canonical spec. Commit/push and verify remote equality. Do not merge.

Return exact safe summary:

```text
RESULT: PHASE-1C-REVIEW-READY | FAIL
STATE: <validated phase/mode>
ARTIFACTS: <paths>
PRESERVED_EVIDENCE: <safe paths/hashes/modes>
VALIDATION: <commands/exits>
SPEC: pending
COMMIT: <hash>
PUSH: <equality>
PR: #330 NOT MERGED
```
