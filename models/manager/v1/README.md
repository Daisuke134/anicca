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
