# CORE 8d — fresh-review 6 blockers corrective RED

You are a fresh `gpt-5.6-sol` RED/test-contract builder. Work only in `/Users/anicca/anicca-project/.worktrees/lm-p0-order8d` on `feature/lm33d-daily-preflight`. Do not delegate. This atomic is RED only: reproduce the six fresh-review blockers with executable tests and official VCSDD traceability artifacts. Do not implement GREEN fixes.

## Sources and exact binding

- Fetch first. Require clean worktree and `HEAD == upstream == a5dc8df8b23776e1a2877a30bbcb32e7cfeae4dc`.
- Canonical product spec: `/Users/anicca/anicca-project/docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`; read §9, §9.5, §10 row 8d, §10.0, §10.2 and §10.3.
- Fresh review log: `/Users/anicca/anicca-project/.claude/sol-orders/logs/core-8d-manager-fresh-review-2.log`; terminal verdict is `RESULT=FRESH-REVIEW-FAIL blockers=6`.
- Baseline for this RED atomic is exact `a5dc8df8b...`. Preserve all earlier immutable evidence and Phase 3 provenance.

## Entry gate

Reproduce before edits:

- full intended manager suite `137/137`;
- old selection `75/75`, focused `52/52`, full app `372/372`, eval `33/33`;
- module coverage lines/functions: daily-preflight `92.68/96.00`, collectors `90.08/90.91`, gog `99.06/100`, CLI `95.40/100`;
- state/runtime/schema/trace PASS, 101 test beads GREEN, 11 prior findings RESOLVED, `currentPhase=2b`, `sprintCount=0`, active feature `fable5-config-slimdown`;
- recorded tracked-snapshot `scope`, `coverage`, and controlled-L3 gate each exit 1.

If any entry fact differs, return `RESULT=BLOCKED` without normalization.

## RED contract

Add the minimum executable contract cases needed for the following six findings. Each new case must fail for the reviewed defect, pass against a minimal correct implementation, and have an exact stable name. Runtime assertions are required; source-regex-only tests are insufficient.

1. **Tracked evidence closure / no self-hash impossibility**
   - Reproduce the recorded tracked `scope`, `coverage`, and controlled-L3 commands failing against final HEAD while `verification.md` claims PASS.
   - Define the correct non-circular contract: the tracked source snapshot binds the immutable implementation commit and exact `apps/life-call` tree; current HEAD must be a descendant, current worktree must be clean, current app tree must equal the bound tree, and every post-implementation commit/path must be restricted to declared state/history/new-evidence closure. Any production/test/root-spec/global-index/historical-evidence change after the bound implementation commit fails.
   - Controlled L3 must evaluate the current clean HEAD and exact bound app tree without requiring a tracked file to contain its own commit hash. The post-run evidence may record the observed invocation HEAD; it must not be used to pre-authorize itself.
   - Recorded commands and path counts must be replayable and truthful.

2. **Current-run replay and fresh-process arbitrary runRef**
   - Reproduce two valid independent reports in one process, then prove the first serialized report is wrongly accepted after the second.
   - In a fresh process, prove an arbitrary well-formed runRef is wrongly accepted.
   - Correct contract: serialized validation must require explicit current-run provenance from the same invocation; module-global history/empty-Set fallback is forbidden. Raw correlation remains absent from the final report and evidence.

3. **Deadline test must exercise production supported boundaries**
   - Reproduce production `withinDeadline` aborting its signal while a non-cooperative timer continues, versus the harness deleting the timer.
   - Replace only the known false test contract so it exercises real signal-aware provider/process/poll/wait boundaries. Do not demand magical cancellation of arbitrary JavaScript.
   - RED must fail because production boundary lineage or the harness contract is wrong, not because a test-only AsyncLocalStorage hook manufactures success. Test-support may not delete timers to alter production semantics.

4. **Receipt boundary integrity**
   - Reproduce `core8d-runtime-harness.js` moving `sentAtMs` back 1000 ms and accepting a receipt one millisecond before the actual send.
   - Correct contract: source `sentAtMs` is never rewritten. Determinism uses an explicit clock seam wholly inside test support, and a receipt 1 ms before actual send is rejected.

5. **Portable VCSDD schema discovery**
   - Reproduce the `/Users/anicca/.codex/plugins/cache/...` absolute import requirement.
   - Correct contract: use supported installed-plugin discovery (`CLAUDE_PLUGIN_ROOT` or an equivalent explicit injected plugin root) with fail-closed validation. A fresh checkout/machine without Dais's path must work when the plugin root is provided and fail clearly when absent.

6. **Recursive privacy scan truthfulness**
   - Run the exact architecture-approved recursive scope and reproduce exit 1, including detector self-literals and the actual production paths that fail. Do not echo matched secret/PII content.
   - Correct contract: the declared recursive scope is deterministic and executable, scans changed production plus required feature/evidence artifacts, handles its own detector fixtures/literals without false positives, still rejects injected secret/email/phone/raw-correlation/provider-ID fixtures, and records the actual path count rather than a hardcoded count.

## Test-contract correction rule

- Earlier manager tests remain immutable except the exact false deadline/receipt harness assertions proven invalid by this fresh review. Any correction to those tests must strengthen reality: remove harness semantic rewriting and replace it with supported-boundary/runtime assertions. Record before/after test names and why the prior assertion was false.
- Do not skip, delete, rename away, weaken, or regex-substitute any other test.
- Production/verifier/test-support implementation must remain byte-identical to `a5dc8df8b` in this RED atomic. Test files, VCSDD state/history, new finding artifacts, and new RED evidence are the only allowed changes.

## VCSDD state and evidence

- Stay in `currentPhase=2b`, `sprintCount=0`; do not fake a transition.
- Using official VCSDD APIs, add exactly six new adversary findings `FIND-012..FIND-017` routed to `2b`, and exactly the new RED test beads required by the executable cases. Do not reopen or rewrite FIND-001..011; retain their historical resolved status.
- Link each new finding bidirectionally to its exact RED tests. New tests are RED; existing unaffected tests remain GREEN.
- Create new immutable evidence under `.vcsdd/features/life-manager-daily-preflight/evidence/sprint-1/manager-review6-red-a5dc/`. Do not overwrite `manager-review-green-ba370` or any historical evidence.
- Record exact commands, individual exit codes, failure names/counts, production implementation diff=0, test-contract correction diff, state/runtime validation, privacy-safe reproductions, and HEAD/upstream.

## Prohibited

- No GREEN implementation, provider/network/TG/email/call, controlled L3, final report, deploy, merge, panel, marketing, root spec edit, or active-feature change.
- No fake evidence, hand-edited VCSDD state, `git add -A`, dependency churn, or unrelated refactor.

## Finish

- Freshly run the original `137/137` selection excluding/reconciling only the explicitly corrected false assertions, then the expanded suite. Existing unaffected tests must remain GREEN and all new blocker tests must be genuine RED.
- Run installed state/runtime validators and verify exact bead/finding/link counts.
- Stage exact paths only, commit, push, and prove clean `HEAD == upstream`.
- Return one marker:
  - `RESULT=REVIEW6-RED` with commit, exact total/pass/fail counts, six failing test names, new bead/finding IDs, implementation_diff=0, state=2b, sprintCount=0, upstream SHA, and `NEXT=fresh Phase-2b GREEN Sol`; or
  - `RESULT=BLOCKED` with the exact invariant and preserved-state proof.
