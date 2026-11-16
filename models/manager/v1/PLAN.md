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

## Retry #2 execution evidence (2026-11-16)

- Assignment explicitly overrides repository-name/source-boundary restrictions and requires the current branch with no push. Root/branch/common directory/origin verified before source inspection.
- `bash scripts/verify-source-boundary.sh`: checkout-root rejection; overridden by assignment, no guard edited.
- Current harness has no installed `/home/hatch/.agents/skills/superpowers`; missing skill skipped as instructed. Earlier skill/reviewer claims above belong to the previous attempt. Astra Advisor is unavailable.
- Preserved pending artifacts reviewed; three BehaviorBench tests and shell syntax/diff checks pass; committed as `af509bae1`.
- No live training process at restart; checkpoint-50 optimizer, scheduler, RNG and trainer state present. Resume keeps all 2,000 rows and 125 total steps.
