# Manager v1 execution plan

Founder assignment (2026-11-16) is the specification; no approval pauses.
Reuse v0 TRL LoRA with all 2,000 prepared rows, unchanged serialization, 25-step checkpoints and automatic resume. This isolates more-data/optimization from v0; both-arm distillation is deferred to avoid inventing counterfactual labels.

1. Run CPU bf16 SFT to completion; retain loss history and merged weights locally.
2. Reuse v0 uplift evaluator unchanged: fp32, 1,000 rows, seed 0, 500 bootstraps.
3. Inspect official BehaviorBench data and reuse its task format for a CPU subset; distinguish earlier MaMe-Re references from BehaviorBench results.
4. Document prior as current serving choice, actual integration limits, results and reproduce commands.
5. Verify artifacts and focused checks; commit current branch, no push.

Skills read: using-superpowers, brainstorming (questions explicitly waived), writing-plans, test-driven-development, verification-before-completion. Astra Advisor is not exposed in this harness; native execution. Ponytail check: reuse v0, existing venv and existing benchmark assets.

Review: fresh read-only gpt-6.1-sol reviewer (/root/review_v1), 0 findings;
3 unit tests passed. Final measured artifacts still pending training.
