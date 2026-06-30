#!/usr/bin/env python3
"""loop-roi-dispatch.py — Python side of loop-roi.sh."""
import json
import os
import sys
import time
from pathlib import Path

shared_dir = os.environ.get("ANICCA_SHARED_DIR", "")
if shared_dir:
    sys.path.insert(0, shared_dir)

from lib.roi import compute_token_cost_jpy  # noqa: E402
from lib._common import append_jsonl  # noqa: E402


# Default rate table per REQ-B2 (frozen 2026-07-01).
RATES_INPUT = {"sonnet": 3.0, "opus": 15.0, "haiku": 1.0, "haiku-4-5": 1.0,
               "claude-opus-4-8": 15.0, "fable": 3.0,
               "claude-sonnet-4-6": 3.0}
RATES_OUTPUT = {"sonnet": 15.0, "opus": 75.0, "haiku": 5.0, "haiku-4-5": 5.0,
                "claude-opus-4-8": 75.0, "fable": 15.0,
                "claude-sonnet-4-6": 15.0}


def main() -> int:
    slot = os.environ.get("ANICCA_SLOT", "")
    pass_id = os.environ.get("ANICCA_PASS_ID", "")
    tokens_in = int(os.environ.get("ANICCA_TOKENS_IN", "0") or 0)
    tokens_out = int(os.environ.get("ANICCA_TOKENS_OUT", "0") or 0)
    model_id = os.environ.get("ANICCA_MODEL_ID", "sonnet")
    wall_s = int(os.environ.get("ANICCA_WALL_S", "0") or 0)

    fx_path = Path.home() / "anicca" / "skills" / "_shared" / "fx.json"
    fx = 150.0
    if fx_path.exists():
        try:
            fx = float(json.loads(fx_path.read_text()).get("USDJPY", 150.0))
        except Exception:
            pass

    cost = compute_token_cost_jpy(
        model_breakdown=[{"model_id": model_id,
                          "tokens_in": tokens_in, "tokens_out": tokens_out}],
        rates_input=RATES_INPUT, rates_output=RATES_OUTPUT,
        fx_usdjpy=fx, token_source="measured",
    )

    row = {
        "ts": int(time.time()),
        "slot": slot, "pass_id": pass_id,
        "model_breakdown": [{"model_id": model_id,
                             "tokens_in": tokens_in, "tokens_out": tokens_out}],
        "tokens_in": tokens_in, "tokens_out": tokens_out,
        "tokens_total": tokens_in + tokens_out,
        "token_source": "measured",
        "token_cost_jpy": cost,
        "jpy_earned_this_pass": 0,
        "usdc_earned_this_pass": 0.0,
        "wall_seconds": wall_s,
        "roi_7day_jpy": None, "roi_30day_jpy": None,
        "actions_taken": 0,
    }
    append_jsonl(Path.home() / "loops" / slot / "roi.jsonl", row)
    print(f"roi: cost_jpy={cost:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
