# ManagerBench public launch specification and execution plan

Purpose: publish a reproducible, honest research package on codex/managerbench-launch, then compare the requested current OpenRouter models on exactly its published inputs. The user explicitly requests autonomous execution and this sparse clone.

Scope: managerbench/ only, plus a team board log; private comparison report in anicca-ops main. No raw interventions, personal me-data, training, production deployment, new billing, or auto-reload changes.

Source correction: baseline-2026-11-14 contains 192 aggregated evaluation receipts, not 192 input cases. The supplied 2026-11-15 dataset has 260 receipts and 10 incomplete records. Never derive fictitious prompts or labels from scores. Reuse the ten existing synthetic restraint-v1 situations; publish all ten, not a sampled subset. Real intervention cases = 0. Behavioral prediction and comedy tracks remain historical receipts, not newly measured tracks.

Architecture: pinned Rubric/rubric-eval core metrics as primary scorer, promptfoo secondary instructions. Standard-library OpenRouter transport, one identical prompt per situation/model, max_tokens=2000, no tools, no model-specific retries. Exact action accuracy measures synthetic restraint only; observed value/cost/causal effect stay null. All ten labels are pass: disclose the always-pass ceiling and limited discrimination.

Alternatives: inventing 192 cases misrepresents provenance; redistributing restricted benchmark inputs risks their licenses; reuse the existing synthetic suite and freeze historical scores instead.

Completion: branch provider readback, public bytes pinned by commit and SHA256, all nine API models attempted on all ten published cases, Manager v0 measured only if a real published runnable checkpoint exists, exact per-generation costs/total, private report pushed to main and verified.

## Ordered execution
- [x] Publish inputs, provenance, baseline, README, Rubric harness, tests and secondary instructions.
- [x] Observe negative parser/scoring tests, implement minimum runner, pass focused tests and fresh read-only publication review.
- [x] Commit/push public branch, verify ls-remote and public source bytes.
- [x] Resolve exact model IDs from live catalog, run frozen published suite with dedicated $5 capped key; preserve failures and raw synthetic responses.
- [x] Reconcile generation receipts and dedicated-key spend; disable key; write and push report to anicca-ops main.

Cursor: assemble package. Skills read: using-superpowers, brainstorming (explicit no-questions opt-out), writing-plans, executing-plans, test-driven-development, using-git-worktrees, ponytail full. Existing root/remote verified. Life Manager-only source-boundary rules conflict with explicit anicca target and are superseded for this task.

Verification: initial import failure observed before implementation; concurrent intent race reproduced (9 unwanted calls) then fixed using exclusive create and post-acquisition destination check. All six focused tests pass. Independent read-only publication review found no HIGH, one MEDIUM race corrected. Historical source hashes and 192-in-260 lineage verified.

## Protocol correction (#301 / #302)
Use ALL 10 publishable restraint-v1 cases, in published order, for every model. No sampling; seed not applicable. Freeze case IDs and SHA256 in the private result file before any corrected-run inference. The original API bench first-four-positive/first-four-negative selection is an outcome-conditioned non-probability design; it is not used here. No restricted 12,808-person frame is loaded.
Request exactly id, action and p_intervene (probability that sending now is appropriate). Synthetic Brier = mean((p_intervene - 0)^2), over all ten only when all ten contracts pass. Otherwise report incomplete Brier as unmeasured with valid-only descriptive loss separately. No human response or population claims; always-pass with p=0 has Brier 0 by construction. Preserve earlier attempt costs separately.
Cursor: DONE — full-frame comparison, official cost reconciliation, key-disabled readback, replay-zero and independent source/numerical reviews complete. Final aggregate/report are the publication artifacts.

Measured result: full public-frame census, 90 unique generations, all contracts valid, official total $0.103723397; Manager v0 unmeasured. Source inference commit ade92be1d16e75cf3eb7704a834890bc5a970535; preregistration b37459004559e070a10b7c79ae1161810c71e409 precedes first request. No population or human-effect inference.
