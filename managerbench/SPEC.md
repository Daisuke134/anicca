# ManagerBench public launch specification and execution plan

Purpose: publish a reproducible, honest research package on codex/managerbench-launch, then compare the requested current OpenRouter models on exactly its published inputs. The user explicitly requests autonomous execution and this sparse clone.

Scope: managerbench/ only, plus a team board log; private comparison report in anicca-ops main. No raw interventions, personal me-data, training, production deployment, new billing, or auto-reload changes.

Source correction: baseline-2026-11-14 contains 192 aggregated evaluation receipts, not 192 input cases. The supplied 2026-11-15 dataset has 260 receipts and 10 incomplete records. Never derive fictitious prompts or labels from scores. Reuse the ten existing synthetic restraint-v1 situations; publish all ten, not a sampled subset. Real intervention cases = 0. Behavioral prediction and comedy tracks remain historical receipts, not newly measured tracks.

Architecture: pinned Rubric/rubric-eval core metrics as primary scorer, promptfoo secondary instructions. Standard-library OpenRouter transport, one identical prompt per situation/model, max_tokens=2000, no tools, no model-specific retries. Exact action accuracy measures synthetic restraint only; observed value/cost/causal effect stay null. All ten labels are pass: disclose the always-pass ceiling and limited discrimination.

Alternatives: inventing 192 cases misrepresents provenance; redistributing restricted benchmark inputs risks their licenses; reuse the existing synthetic suite and freeze historical scores instead.

Completion: branch provider readback, public bytes pinned by commit and SHA256, all nine API models attempted on all ten published cases, Manager v0 measured only if a real published runnable checkpoint exists, exact per-generation costs/total, private report pushed to main and verified.

## Ordered execution
- [ ] Publish inputs, provenance, baseline, README, Rubric harness, tests and secondary instructions.
- [ ] Observe negative parser/scoring tests, implement minimum runner, pass focused tests and fresh read-only publication review.
- [ ] Commit/push public branch, verify ls-remote and public source bytes.
- [ ] Resolve exact model IDs from live catalog, run frozen published suite with dedicated $5 capped key; preserve failures and raw synthetic responses.
- [ ] Reconcile generation receipts and dedicated-key spend; disable key; write and push report to anicca-ops main.

Cursor: assemble package. Skills read: using-superpowers, brainstorming (explicit no-questions opt-out), writing-plans, executing-plans, test-driven-development, using-git-worktrees, ponytail full. Existing root/remote verified. Life Manager-only source-boundary rules conflict with explicit anicca target and are superseded for this task.
