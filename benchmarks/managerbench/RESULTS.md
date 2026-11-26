# ManagerBench — measured results

Every number below comes from a run whose inputs and scoring code are in
this repository or in the cited public source. Where a denominator is
small, we say so. Where we lost, we say so.

## 1. Frozen MaMe-Re v1 — behavior prediction (strict accuracy, non-tied n = 18)

Official frozen harness, same conditions for every arm.

| Arm | Strict accuracy | Correct |
|---|---|---|
| Qwen3-4B-Instruct-2507 (backbone control) | 0.6111 | 11/18 |
| Prior (train mean) | 0.6111 | 11/18 |
| Be.FM 1.5-4B | 0.5556 | 10/18 |

Be.FM does **not** beat the prior. With n = 18, one case is worth
0.0556 — read all three numbers as "indistinguishable at this size,"
which is itself the finding that motivates the v2 expansion.

## 2. First same-conditions run, 2026-11-17 — intervention prediction (Brier, lower is better)

| Model | Brier |
|---|---|
| Grok | 0.3547 |
| GPT | 0.3555 |
| Manager v1 | 0.3827 |
| Prior | 0.3869 |
| Claude | 0.4631 |

## 3. First same-conditions run, 2026-11-17 — comedy / Ōgiri generation (0–10, higher is better)

| Model | Score |
|---|---|
| Grok | 7.58 |
| Claude | 6.58 |
| GPT | 5.17 |
| Manager v1 | 1.92 |

**Manager v1 is an honest negative result**: it does not beat the prior
or the frontier models on either surface. The bottleneck is training
data — specifically, the app does not yet log chosen interventions with
their assignment probabilities, so real intervention cases number 0
(see README "Known gaps").

## 4. MG-06 uplift protocol — Hillstrom randomized e-mail experiment

Scoring dtype pinned to fp32 (a protocol requirement; bf16 logit noise
exceeds the probability differences this metric ranks). Full protocol
and reproduction commands: [`models/manager/v0/`](../../models/manager/v0/).

Frozen test subsample, n = 1,000 (seed 0, stratified), ATE 0.0455,
random p95 = 0.0715. Gate: lower 95% CI > random p95.

| Arm | Qini AUC | 95% CI | AUUC | uplift@30% |
|---|---|---|---|---|
| Population prior | 0.0000 | — | 0.0000 | 0.0749 |
| T-learner (logistic regression) | 0.1017 | [0.0079, 0.2128] | 0.0479 | 0.0671 |
| Base model (SmolLM2-135M-Instruct) | 0.0739 | [−0.0458, 0.1853] | 0.0345 | 0.0753 |
| Manager v0 (post-trained) | 0.0041 | [−0.0839, 0.1045] | 0.0027 | 0.0746 |

No arm passes the gate on the subsample (the subsample costs statistical
power; on the full frozen test the T-learner passes the pre-registered
H1: Qini 0.0712, CI [0.0437, 0.0997] vs random p95 0.0201). Manager v0
shows **no measurable uplift skill**: its CI crosses zero and its point
estimate is below the untrained base model. Training itself was healthy
(loss 0.82 → 0.09); the model learned the outcome distribution, not the
contrast between arms. That is the v0 result, and we do not dress it up.

## 5. BehaviorBench (external, adopted as-is)

UMich Foreseer BehaviorBench (arXiv 2606.24162; code MIT; data
CC BY-NC-ND 4.0), run under its official harness. Small local runs,
2026-11-10, personality-score prediction (`pers_score_pred`, MAE, lower
is better): Be.FM 1.5-4B 6.52, Qwen3-4B backbone 6.48. Full-coverage
receipts for the frozen replay are under
[`files/eval/`](../../files/eval/) and aggregate through
`files/eval/managerbench/run.py` (260 family/task/condition rows,
10 incomplete arms, no pooled score — cross-family pooling is refused
by design).

## What is NOT measured yet

- Real intervention cases from the Anicca app: **0** (logging gap,
  README "Known gaps" #1).
- ManagerBench v2 (expanded frozen set, ~200 cases): planned, unmeasured.
- Psych-101 / Psych-201 full-frame scores for Manager v0/v1 under the
  Centaur protocol: runs in progress; no numbers are claimed here until
  their receipts land in this repository.
