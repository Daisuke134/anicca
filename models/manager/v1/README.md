# Manager v1 — all prepared rows (2026-11-16)

## 1. Question

Does training on all 2,000 prepared Hillstrom SFT rows improve v0's
intervention ranking? Founder withdrew the pre-training MG-06 prerequisite;
training starts regardless of a prior-beating candidate. Current Manager
remains the prior pending explicit v1 serving integration.

## 2. Method

Reuse v0 serialization, frozen split, base model and TRL/PEFT recipe.
Change only the training sample from 1,000 to 2,000 rows (one epoch, 125
steps). CPU bf16, LoRA r=16/alpha=32 all-linear, lr=0.001 cosine, batch=16.
Checkpoint every 25 steps with latest-checkpoint resume.
This tests more data/optimization; it does not implement both-arm or
pseudo-outcome supervision, so v0's contrast hypothesis remains open.

Uplift uses v0/eval_uplift.py unchanged: seed 0, same frozen-test
1,000-row stratified subsample, fp32 scoring, 500 bootstrap draws.
BehaviorBench uses the pinned official surv_resp_pred file, 100 rows
(seed 42), identical prompts for base and v1, greedy generation in fp32.
Row accuracy includes invalid outputs; this is a partial diagnostic,
not the official grouped multi-task leaderboard.

## 3. Results and status

Training is running. No v1 metric is claimed until results JSON exists.
The completed write-up will replace this status with measured values.
Historical references Be.FM=0.5556 and prior=0.6111 are from MaMe-Re
18 non-tied pairs, **not BehaviorBench accuracy**; see
../../../docs/research/manager/2026-11-11-behaviorbench-run.md section 6.

## 4. Reproduce

Commands and final measured results are being assembled during training.
No paid compute, new API, signup, iOS edit or push. Local weights and
checkpoints are ignored by Git and retained under out/manager-v1.
