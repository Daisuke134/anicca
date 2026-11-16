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

Training completed 2026-11-16: all 2,000 prepared rows, 125/125 steps,
1 epoch (resumed from checkpoint-50 after an interruption; final segment
2,208 s on CPU). Trainer-reported average train loss 0.1244; logged loss
at step 125 was 0.1326. Merged weights are under `out/manager-v1/`
(git-ignored, retained on the VM). `verify_results.py` prints PASS:
training complete, frozen uplift baselines exact, BehaviorBench aligned,
source hashes intact.

Uplift evaluation — v0 frozen protocol unchanged (frozen test subsample
n=1,000, seed 0, fp32 scoring, 500 bootstrap draws;
`results/eval_manager-v1.json`):

| arm | Qini | Qini boot95 CI | AUUC | uplift@30% |
| --- | --- | --- | --- | --- |
| population prior | 0.0000 | — | 0.0000 | 0.0749 |
| random targeting | −0.0070 (mean) | p95 = 0.0715 | — | — |
| base SmolLM2-135M-Instruct | 0.0739 | [−0.0458, 0.1853] | 0.0345 | 0.0753 |
| Manager v0 (1,000 rows, historical) | 0.0041 | [−0.0839, 0.1045] | 0.0027 | 0.0746 |
| **Manager v1 (2,000 rows)** | **0.0026** | **[−0.0938, 0.1008]** | **0.0007** | **0.0617** |
| T-learner (logreg) | 0.1017 | [0.0079, 0.2128] | 0.0479 | 0.0671 |

Verdict, recorded honestly: **v1 does not beat the base model, the
random-targeting p95, or the T-learner.** The MG-06 gate check fails
(lower 95% CI −0.0938 ≤ random p95 0.0715). Doubling the SFT sample from
1,000 to 2,000 rows did not repair v0's negative result; v1's Qini
(0.0026) is statistically indistinguishable from v0's (0.0041) and from
the constant prior (0.0). The population prior therefore **remains the
serving Manager**; no serving switch is made on this result.

BehaviorBench comparison frame — official `surv_resp_pred` file pinned
by revision, 100 rows (seed 42), identical prompts, greedy fp32,
row accuracy including invalid outputs (`results/behaviorbench_v1.json`,
`results/behaviorbench_base.json`):

| model | accuracy | invalid |
| --- | --- | --- |
| base SmolLM2-135M-Instruct | 0.00 (0/100) | 100 |
| **Manager v1** | **0.00 (0/100)** | **100** |
| prior, complement marginal | 0.25 | 0 |
| prior, constant 3 | 0.31 | 0 |

Both the base model and v1 fail the strict bracket format on every row,
so this frame shows no transfer from Hillstrom SFT to BehaviorBench
response prediction; the constant priors beat both LLMs here.
Historical references Be.FM=0.5556 and prior=0.6111 are from MaMe-Re
18 non-tied pairs, **not BehaviorBench accuracy**, and are not
comparable to the numbers above; see
../../../../docs/research/manager/2026-11-11-behaviorbench-run.md section 6.

## 4. Reproduce

Run from the repository root on this VM (existing v0 environment):

```bash
export TMPDIR=/home/hatch/workspace/tmp_cache/manager-v1
export PIP_CACHE_DIR=/home/hatch/workspace/tmp_cache/pip
export npm_config_cache=/home/hatch/workspace/tmp_cache/npm
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" "$npm_config_cache"
PY=/home/hatch/workspace/tools/manager-v0-venv/bin/python
nohup "$PY" -u models/manager/v1/train_sft.py \
  --data models/manager/v0/data/sft_train.jsonl \
  --out models/manager/v1/out/manager-v1 \
  > models/manager/v1/train.log 2>&1
"$PY" models/manager/v1/eval_behaviorbench.py \
  --model HuggingFaceTB/SmolLM2-135M-Instruct \
  --out models/manager/v1/results/behaviorbench_base.json
bash models/manager/v1/evaluate.sh
python3 -m unittest discover -s models/manager/v1 -p 'test_*.py'
```

Repeat the training command to resume the latest checkpoint. For an
independent fresh run, pass a different `--out` directory. `evaluate.sh`
accepts `MANAGER_PYTHON` and `HILLSTROM_SOURCE` environment overrides; it
checks the frozen source hash before scoring. `requirements.txt` records
the exact reused environment (CPU PyTorch wheel). On another machine,
create a venv and install those versions with the PyTorch CPU wheel index;
keep the cache variables above outside `/tmp`.

No paid compute, new API, signup, iOS edit or push. Local weights and
checkpoints are ignored by Git and retained under out/manager-v1.
