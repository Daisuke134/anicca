#!/usr/bin/env bash
# loop-roi.sh — REQ-B1 end-of-pass roi.jsonl row writer.
# Invoked by each slot's cron-prompt at end of every pass.
#
# Usage: loop-roi.sh <slot> <pass_id> <tokens_in> <tokens_out> <model_id> <wall_seconds>
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

SLOT="${1:-}"
PASS_ID="${2:-}"
TOKENS_IN="${3:-0}"
TOKENS_OUT="${4:-0}"
MODEL_ID="${5:-sonnet}"
WALL_S="${6:-0}"
SHARED_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 - <<PYEOF
import json, os, sys, time
sys.path.insert(0, "${SHARED_DIR}")
from pathlib import Path
from lib.roi import compute_token_cost_jpy, kill_switch_tripped
from lib._common import append_jsonl

# Default rate table per REQ-B2 (frozen 2026-07-01)
RATES_INPUT = {"sonnet": 3.0, "opus": 15.0, "haiku": 1.0, "haiku-4-5": 1.0,
               "claude-opus-4-8": 15.0, "fable": 3.0}
RATES_OUTPUT = {"sonnet": 15.0, "opus": 75.0, "haiku": 5.0, "haiku-4-5": 5.0,
                "claude-opus-4-8": 75.0, "fable": 15.0}
fx_path = Path.home() / "anicca" / "skills" / "_shared" / "fx.json"
fx = 150.0
if fx_path.exists():
    try:
        fx = float(json.loads(fx_path.read_text()).get("USDJPY", 150.0))
    except Exception:
        pass

cost = compute_token_cost_jpy(
    model_breakdown=[{"model_id": "${MODEL_ID}",
                      "tokens_in": ${TOKENS_IN}, "tokens_out": ${TOKENS_OUT}}],
    rates_input=RATES_INPUT, rates_output=RATES_OUTPUT,
    fx_usdjpy=fx, token_source="measured",
)
row = {
    "ts": int(time.time()),
    "slot": "${SLOT}", "pass_id": "${PASS_ID}",
    "model_breakdown": [{"model_id": "${MODEL_ID}",
                         "tokens_in": ${TOKENS_IN}, "tokens_out": ${TOKENS_OUT}}],
    "tokens_in": ${TOKENS_IN}, "tokens_out": ${TOKENS_OUT},
    "tokens_total": ${TOKENS_IN} + ${TOKENS_OUT},
    "token_source": "measured",
    "token_cost_jpy": cost,
    "jpy_earned_this_pass": 0,   # TODO sprint-2: read from earnings.jsonl diff
    "usdc_earned_this_pass": 0.0,
    "wall_seconds": ${WALL_S},
    "roi_7day_jpy": None, "roi_30day_jpy": None,
    "actions_taken": 0,
}
append_jsonl(Path.home() / "loops" / "${SLOT}" / "roi.jsonl", row)
print(f"roi: cost_jpy={cost:.2f}")
PYEOF
