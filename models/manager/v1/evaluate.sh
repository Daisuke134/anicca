#!/usr/bin/env bash
# Run from repository root after training finishes. Reuses the frozen v0 harness.
set -euo pipefail
export TMPDIR="${TMPDIR:-/home/hatch/workspace/tmp_cache/manager-v1}"
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-/home/hatch/workspace/tmp_cache/pip}"
export npm_config_cache="${npm_config_cache:-/home/hatch/workspace/tmp_cache/npm}"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" "$npm_config_cache"
manager_python="${MANAGER_PYTHON:-/home/hatch/workspace/tools/manager-v0-venv/bin/python}"
manager_source="${HILLSTROM_SOURCE:-/home/hatch/workspace/manager-v0-work/data/hillstrom.csv.gz}"
manager_dir=models/manager/v1
"$manager_python" - "$manager_source" <<'PY'
import hashlib, sys
from pathlib import Path
assert hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest() == 'bab6578f60db5d792f1c2372c502f029152a5249cf5ea84390f3b7f885d7234f'
PY
cp "$manager_dir/out/manager-v1/train_log.json" "$manager_dir/results/train_log.json"
"$manager_python" models/manager/v0/eval_uplift.py \
    --source "$manager_source" --model "$manager_dir/out/manager-v1" \
    --label manager-v1 --eval-n 1000 --out "$manager_dir/results/eval_manager-v1.json"
"$manager_python" "$manager_dir/eval_behaviorbench.py" \
    --model "$manager_dir/out/manager-v1" --out "$manager_dir/results/behaviorbench_v1.json"
"$manager_python" "$manager_dir/verify_results.py"
