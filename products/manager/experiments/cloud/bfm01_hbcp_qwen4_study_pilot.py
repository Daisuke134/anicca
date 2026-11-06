"""BFM-01: real HBCP intervention-arm forecasting with an actual open Qwen3-4B.

NOT Be.FM (gated), NOT a causal treatment-effect estimate, NOT a validated BFM.
Source: published HBCP study-arm annotations, no individual patient records.
The untrusted/public dataset is never committed, and prompts/labels never
leave the ephemeral free GitHub runner. Only aggregate errors are uploaded.

Pre-existing source with 971 study arms:
https://github.com/HumanBehaviourChangeProject/semantic-prediction
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import io
import json
import math
import re
import time
import urllib.request
from pathlib import Path

DATA_URL = ("https://raw.githubusercontent.com/"
            "HumanBehaviourChangeProject/semantic-prediction/main/data/hbcp_gen.csv")
DATA_SHA256 = "eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b"
LABEL = "('Outcome', 'Outcome')"
SEED = "manager-bfm01-study-heldout-2026-11-05"
N_EVAL_ARMS = 12
N_SELECTED_STUDIES = 16
MODEL = "bartowski/Qwen_Qwen3-4B-Instruct-2507-GGUF"
MODEL_SHA256 = "2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e"


def _check_rate(value: str) -> float | None:
    try:
        n = float(value)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(n) or n < 0 or n > 100:
        return None
    return n


def load_real_arms() -> list[dict[str, str]]:
    req = urllib.request.Request(DATA_URL, headers={"User-Agent": "Manager-BFM01-Eval/0.1"})
    with urllib.request.urlopen(req, timeout=30) as res:
        body = res.read(900_000)
    if hashlib.sha256(body).hexdigest() != DATA_SHA256:
        raise ValueError("Original real intervention corpus changed; no silent retesting")
    rows = list(csv.DictReader(io.StringIO(body.decode("utf-8-sig"))))
    if len(rows) != 971 or not all("doc" in r and LABEL in r for r in rows):
        raise ValueError("Original HBCP study/target contract drift")
    return rows


def study_split(records: list[dict], n_studies: int = N_SELECTED_STUDIES,
                n_eval: int = N_EVAL_ARMS) -> tuple[list[dict], list[dict], set[str]]:
    """Choose heldout WHOLE studies before inspecting labels or results."""
    studies = sorted(
        {str(r.get("doc", "")).strip() for r in records if str(r.get("doc", "")).strip()},
        key=lambda s: hashlib.sha256((SEED + ":" + s).encode()).hexdigest(),
    )
    if len(studies) < n_studies + 5:
        raise ValueError("Too few independent studies")
    chosen = set(studies[:n_studies])
    train = [r for r in records if r.get("doc") not in chosen
             and _check_rate(r.get(LABEL, "")) is not None]
    candidates = [r for r in records if r.get("doc") in chosen
                  and _check_rate(r.get(LABEL, "")) is not None]
    candidates.sort(key=lambda r: hashlib.sha256(
        (SEED + ":" + str(r.get("doc_id", "")) + ":" +
         str(r.get("arm_id", ""))).encode()).hexdigest())
    eval_rows = candidates[:n_eval]
    if len(eval_rows) != n_eval or not train:
        raise ValueError("Too few rows for fixed study-heldout pilot")
    if {r["doc"] for r in train} & {r["doc"] for r in eval_rows}:
        raise ValueError("Study split leakage")
    return train, eval_rows, chosen


def present_features(row: dict, max_features: int = 16) -> list[str]:
    """Use only pre-intervention intervention arm/context flags; never IDs/targets."""
    features = []
    for key, value in row.items():
        if value != "1" or key in {"doc", "doc_id", "arm", "arm_id", LABEL}:
            continue
        try:
            parsed = ast.literal_eval(key)
        except (ValueError, SyntaxError, TypeError):
            continue
        if not isinstance(parsed, tuple) or len(parsed) != 2:
            continue
        name = parsed[1]
        if not isinstance(name, str):
            continue
        if "Outcome" in name or "outcome" in name.lower():
            continue
        # Features are aggregated annotations; 'Outcome' is the forbidden target.
        if ("Abstinence" in name or "follow up" in name or "Mean age" in name
                or "Individual-level" in name or "Face to face" in name
                or "Group-based" in name or "Support" in name
                or name[:1].isdigit() or "Patch" in name or "Pill" in name):
            features.append(name.strip())
    features.sort()
    return features[:max_features]


def create_prompt(row: dict) -> str:
    flags = present_features(row)
    if not flags:
        flags = ["No selected intervention/context annotations available"]
    content = (
        "An anonymized aggregate arm from a published smoking-cessation randomized "
        "intervention study has the following coded context and techniques:\n"
        + "; ".join(flags) +
        "\nPredict the percentage (0 to 100) of participants in this arm "
        "who were abstinent at the study-defined follow-up. "
        "Answer with only one numeric percentage and no explanation."
    )
    if LABEL in content or str(row.get("doc", "")) in content:
        raise ValueError("Forbidden source/label text in prompt")
    return (
        "<|im_start|>system\n"
        "You are a statistical baseline for published research outcomes. "
        "Only give one predicted percentage, no advice.\n"
        "<|im_end|>\n<|im_start|>user\n" + content +
        "\n<|im_end|>\n<|im_start|>assistant\n"
    )


def parse_percentage(raw: str) -> float | None:
    # Be robust to short terminal results; don't cherry-pick malformed outputs.
    if not isinstance(raw, str) or len(raw) > 5000:
        return None
    t = raw.strip()
    match = re.match(r"^\s*(\d{1,3}(?:\.\d+)?)\s*%?\s*(?:[.!]|$)", t)
    if match is None:
        return None
    v = float(match.group(1))
    return v if 0 <= v <= 100 else None


def infer_http(prompt: str, endpoint: str = "http://127.0.0.1:8087") -> tuple[str, float]:
    payload = json.dumps({
        "prompt": prompt, "n_predict": 18, "temperature": 0,
        "cache_prompt": False, "stream": False,
    }).encode("utf8")
    req = urllib.request.Request(endpoint + "/completion", data=payload, method="POST",
                                 headers={"Content-Type": "application/json"})
    start = time.monotonic()
    with urllib.request.urlopen(req, timeout=90) as res:
        data = json.load(res)
    dt = round(time.monotonic() - start, 3)
    return str(data.get("content", "")), dt


def run(endpoint: str) -> dict:
    rows = load_real_arms()
    train, evaluation, heldout = study_split(rows)
    observed = [float(r[LABEL]) for r in evaluation]
    trainmean = sum(float(r[LABEL]) for r in train) / len(train)
    preds, times, malformed = [], [], 0
    for row in evaluation:
        output, elapsed = infer_http(create_prompt(row), endpoint=endpoint)
        p = parse_percentage(output)
        if p is None:
            malformed += 1
            p = trainmean  # predeclared fallback, not excluded from score
        preds.append(p)
        times.append(elapsed)
    mae = lambda pp: sum(abs(y - p) for y, p in zip(observed, pp)) / len(observed)
    rmse = lambda pp: math.sqrt(sum((y-p)**2 for y, p in zip(observed, pp)) / len(observed))
    return {
        "source_kind": "real_published_aggregate_intervention_arms",
        "experiment": "Qwen3-4B-Instruct-2507_Q4_study_heldout_small_pilot",
        "base_model": MODEL,
        "model_sha256": MODEL_SHA256,
        "not_befm": True,
        "not_full_behaviorbench": True,
        "not_original_hbcp_rule_nn": True,
        "data_sha256": DATA_SHA256,
        "n_original_arms": len(rows),
        "n_train_arms": len(train),
        "n_selected_heldout_studies": len(heldout),
        "n_eval_arms": len(evaluation),
        "n_eval_unique_studies": len({r["doc"] for r in evaluation}),
        "split": "deterministic study-disjoint from local HBCP data, not proven pretraining-unseen",
        "train_mean_reference_pct": trainmean,
        "mae_train_mean_pct_points": mae([trainmean] * len(observed)),
        "mae_qwen4_pct_points_including_fallback": mae(preds),
        "rmse_train_mean_pct_points": rmse([trainmean] * len(observed)),
        "rmse_qwen4_pct_points_including_fallback": rmse(preds),
        "invalid_generations": malformed,
        "elapsed_inference_seconds_total": sum(times),
        "causal_effect_estimated": False,
        "generalization_established": False,
        "manager_benefit_established": False,
        "model_training_completed": False,
        "individual_data_exported": False,
        "limitation": ("Small unadapted Qwen pilot on trial-arm outcome rates; labels used only "
                       "in scoring. Public-paper pretraining contamination cannot be excluded. "
                       "No individual participant response or causal treatment effect."),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:8087")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    report = run(args.endpoint)
    dst = Path(args.output)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k.startswith(("n_", "mae_", "invalid_", "elapsed_"))},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
