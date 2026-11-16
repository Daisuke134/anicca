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

## Takeover completion (2026-11-16, Muse direct after 3 Codex failures)

- Uncommitted BOARD/PLAN retry evidence reviewed and committed as `77c68d3eb`.
- Training resumed from checkpoint-50 and finished: global step 125/125, n_train 2,000, final segment 2,208 s CPU, merged weights saved under `out/manager-v1/` (git-ignored). `train_log.json` records `resumed_from=checkpoint-50`.
- Frozen evaluation executed via `evaluate.sh` (exit 0): Manager v1 Qini 0.0026 (boot95 [−0.0938, 0.1008]) vs base 0.0739, random p95 0.0715, T-learner 0.1017, prior 0.0; gate vs random FAIL. BehaviorBench (100 rows, seed 42): v1 accuracy 0.00 with 100/100 invalid, identical to base; constant priors 0.25/0.31.
- `verify_results.py` PASS; 3 BehaviorBench unit tests OK.
- Outcome recorded honestly in `v1/README.md` section 3: v1 does not beat base/prior references, so the population prior remains the serving Manager and no serving switch is made.
