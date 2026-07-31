# CORE-a 8d — resolve Phase 1c iteration-2 FIND-005/FIND-006

You are the fresh `gpt-5.6-sol` Phase 1 spec builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` at exact clean commit `de283ebdd63df592a4c1b92ae550b616744f2463`, branch `feature/lm33d-daily-preflight`, PR #330. Do not spawn another agent.

Scope is Phase 1a/1b process artifacts only. Do not edit application source/tests, historical evidence JSON, iteration-1/2 verdict or finding JSON, root canonical product spec, production config, providers, Telegram/email/phone, Railway, deployment, PR merge state, or contract approval. Do not create Phase 2 RED/GREEN evidence, do not enter Phase 2, and do not perform any network/provider side effect beyond git/GitHub fetch/push/head verification.

Read project `AGENTS.md`, `/Users/anicca/.codex/RTK.md`, installed VCSDD workflow/state/schema docs, feature state, both iteration verdicts, named FIND-005/FIND-006, behavioral spec, verification architecture, draft sprint contract, and root canonical spec §9.5/§10 row 8d/§10.0/§10.2/§10.3.

Required state procedure:

1. Prove clean HEAD/local/upstream/origin/PR equality at `de283ebdd...` and preserve all historical/review artifact hashes and modes.
2. Use installed atomic VCSDD state tooling to route the iteration-2 `1c/FAIL` to earliest Phase `1a`. Preserve the iteration-2 FAIL gate, `humanApproved=false`, `sprintCount=0`, and draft contract.
3. Correct FIND-005 in Phase 1a artifacts; legally transition `1a→1b`; correct FIND-006 in Phase 1b artifacts; stop at `currentPhase=1b` awaiting a fresh iteration-3 review. Never fabricate an iteration-3 verdict or human approval.

FIND-005 accepted correction:

- A final dependency entry is serializable only from an internally aggregated observation whose non-serialized run-correlation value equals the current report run correlation; final `runRef` is the one-way hash reference to that current run.
- Every `checkedAt` must be a finite strict UTC millisecond timestamp and satisfy `generatedAt - 900000ms <= checkedAt <= generatedAt`; it must also be no earlier than the current run start. `fresh: true` alone is never proof.
- Mixed-run observations, malformed/non-finite time, one millisecond future, and one millisecond stale must fail closed. The exact 15-minute lower boundary must pass. Define binary tests and reflect them in PROP/CRIT traceability and final schema counts.
- Keep the final artifact closed and PII-free; do not serialize raw correlation IDs.

FIND-006 accepted correction:

- Replace every mutable or baseline-only success count with an exact final Phase 2 RED/GREEN contract. Separate immutable baseline commands/counts from new-feature commands/counts if that is clearer; no “update later” language.
- Derive the final counts arithmetically from named exact test files/cases and make the total internally consistent. Include FIND-005 exact-limit/stale/future/mixed-run cases. Do not guess counts without enumerating cases.
- Add exact executable commands, expected exits/counts/thresholds, source-snapshot binding, and exact future evidence paths for every obligation: baseline and new focused L1, full final regression, eval, temporal, poll/deadline, final schema/security, purity/provenance, per-changed-module coverage, immutable historical SHA-256+0600 verification, VCSDD state/runtime plus adversary/human/contract gate assertions, REQ→PROP→CRIT traceability, review/artifact schema validation, safe secret/PII scan that does not false-positive ISO timestamps, git/diff/staged-scope checks, and the single separately authorized controlled L3 command/readback.
- The controlled L3 command must be copied/tweaked from the actual existing CLI/package surface after read-only inspection. It must bind the source snapshot, invoke exactly once only after all gates, write one closed report atomically, and make TG=1/email=1/phone=0, 9/9, same-run correlation, and no-artifact-on-failure binary. Do not invoke it now and do not expose credentials in the spec/log.
- Commands must be executable from a declared working directory. Any helper verifier proposed for Phase 2 must have an exact future path, input/output contract, and RED-first test obligation; absent helpers cannot be claimed to pass now.
- Refresh CRIT thresholds and the Phase 1 final checklist so they describe the iteration-2 FAIL correction and future iteration-3 review, without changing contract status from draft.

Create `reviews/spec/iteration-2/RESOLUTION.md` recording the original findings, exact accepted adjudication, corrected anchors, route, and the fact that the reviewer must independently decide iteration 3. Do not modify the original iteration-2 output.

Verification before commit:

- installed VCSDD state/runtime verifiers exit 0;
- selected state/index/contract/iteration-1/2 review schemas pass;
- every REQ reaches a PROP and draft CRIT; all new constraints are linked;
- all planned commands/count arithmetic/evidence paths are internally consistent and existing command surfaces referenced by the plan are confirmed read-only;
- `git diff --check`, allowed Phase 1 staged scope, safe secret/PII counts, source snapshot check, historical JSON SHA-256/mode, and iteration-1/2 review immutability pass;
- no app source/test, evidence JSON, review output, provider, deployment, or root spec file is staged.

Commit/push only corrected Phase 1 specs/draft contract/state/history and iteration-2 resolution record. Verify local/upstream/origin/PR #330 head equality.

Return exactly:

```text
RESULT: ITERATION-3-REVIEW-READY|BLOCKED
FINDINGS_ADDRESSED: FIND-005 ...; FIND-006 ...
STATE: <phase/adversary iteration-2 FAIL/humanApproved=false/sprintCount=0>
FRESHNESS: <same-run and checkedAt exact boundaries>
COMMAND_MATRIX: <exact count summary and omitted classes now covered>
VALIDATION: <fresh commands/exits>
COMMIT: <hash or none>
PUSH: <local/upstream/origin/PR equality>
NEXT: fresh Phase 1c iteration-3 only
```
