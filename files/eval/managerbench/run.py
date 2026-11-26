#!/usr/bin/env python3
"""Offline ManagerBench receipt aggregation. No model inference or training."""
import argparse
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(root, name, sources):
    path = root / name
    raw = path.read_bytes()
    sources[name] = hashlib.sha256(raw).hexdigest()
    return json.loads(raw)


def family(task):
    if task in {"pers_score_pred", "acrossdim_pers_score", "surv_resp_pred",
                "missing_surv_resp", "seq_surv_resp"}:
        return "big_five"
    if task == "demo_pred_age":
        return "demographic"
    if task == "ieo_economics":
        return "economics"
    if task.startswith(("game_behavior_", "multiround_behavior_", "acrossgame_behavior_", "strategic_gameplay_")):
        return "moblab"
    raise ValueError(f"Unknown task family: {task}")


def finite(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite(v) for v in value]
    return value


def require(condition, message):
    """Integrity guards must execute even when Python is optimized (-O)."""
    if not condition:
        raise ValueError(message)


def aggregate(root):
    sources, rows = {}, []
    def add(fam, condition, task, arm, n, metrics, source, invalid=None, abstention=None):
        if type(n) is not int or n <= 0:
            raise ValueError(f"Missing denominator: {condition}/{task}/{arm}")
        if invalid is not None and (type(invalid) is not int or not 0 <= invalid <= n):
            raise ValueError("Invalid parse count")
        rows.append(dict(family=fam, condition=condition, task=task, arm=arm, n=n,
                         metrics=metrics, source=source,
                         invalid_count=invalid,
                         invalid_rate=None if invalid is None else invalid/n,
                         abstention_rate=abstention,
                         abstention_note="未計測: 明示的棄権を区別する記録なし" if abstention is None else "全選択が A/B。棄権0件"))
    conditions = {}
    for version, suffix in [("v2.0", ""), ("v2.1", "_v21"), ("v2.2", "_v22")]:
        src = f"files/eval/mamere_mg04/mamere_mg04_compare{suffix}_results_2026-11-12.json"
        d = read(root, src, sources)
        conditions[version] = dict(d["conditions"], case_manifest_test_sha256=d["case_manifest_test_sha256"])
        for arm, r in d["test"].items():
            require(r["n_correct"]/r["n_human_non_tied"] == r["strict_accuracy"], "MaMe-Re strict accuracy mismatch")
            choices = r["choices"]
            require(len(choices) == r["n_total"] and set(choices.values()) <= {"A", "B"}, "MaMe-Re choice count or value mismatch")
            add("humor", version, "pair_choice", arm, r["n_total"],
                {k:r[k] for k in ("strict_accuracy","n_correct","n_human_non_tied","mean_regret")},
                src, 0, 0.0)
    src = "files/eval/managerbench/receipts/befm-actions-42773122099.json"
    d = read(root, src, sources)
    conditions["v1-actions-24"] = d
    r = d["scores"]
    for arm, acc, regret in [
        ("befm15-4b", r["model_strict_win_accuracy_including_invalid"], r["mean_model_regret_invalid_counted"]),
        ("prior", r["baseline_strict_win_accuracy"], r["mean_baseline_regret"])]:
        add("humor", "v1-actions-24", "pair_choice", arm, r["n_total"],
            dict(strict_accuracy=acc, n_human_non_tied=r["n_human_non_tied"], mean_regret=regret),
            src, r["n_model_invalid"] if arm=="befm15-4b" else 0)
    src = "files/eval/behaviorbench_prior_results_2026-11-12.json"
    d = read(root, src, sources)
    conditions["behaviorbench-prior"] = {k:d[k] for k in ("dataset_revision","evaluator_revision","definition","num_samples_per_game")}
    for r in d["results"]:
        for arm, a in r["arms"].items():
            if "metrics" not in a:
                continue  # human split-half is a reference distribution, not a predictive arm
            n = a.get("metadata", {}).get("num_samples", a.get("num_samples_emitted", r.get("n")))
            add(family(r["task"]), "behaviorbench-prior", r["task"], arm, n,
                a["metrics"], src, a.get("metadata",{}).get("num_failed_parses"))
    metadata_src = "files/eval/behaviorbench-full-coverage-2026-11-12.json"
    old = read(root, metadata_src, sources)
    conditions["behaviorbench-full"] = {k:old[k] for k in ("dataset_revision","evaluator_revision","github_actions","inference_settings_completed_llm_arms")}
    src = "files/eval/behaviorbench-full-coverage-2026-11-12-2150.json"
    d = read(root, src, sources)
    incomplete = []
    for key, r in d.items():
        if r["status"] != "OK":
            incomplete.append(dict(key=key, status=r["status"]))
            continue
        require(r["shards_done"] == r["shards_expected"], "BehaviorBench shard completion mismatch")
        meta = r["metadata"]
        n = r.get("n", meta.get("num_total_attempts"))
        invalid = r.get("n_failed_parse", meta.get("num_failed_parses"))
        valid = r.get("n_valid", meta.get("num_model_samples"))
        require(valid is not None and invalid is not None and valid + invalid == n, "BehaviorBench valid/invalid count mismatch")
        add(family(r["task"]), "behaviorbench-full", r["task"], r["arm"],
            n, r["metrics_official"], src, invalid)
    src = "files/eval/behaviorbench-full-coverage-final-2026-11-13.json"
    d = read(root, src, sources)
    receipts_manifest = json.dumps(d["receipts"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    conditions["behaviorbench-final"] = {
        **{k: d[k] for k in ("dataset_revision", "evaluator_revision", "coverage", "measured_at_utc")},
        # Receipt-gap closure (2026-11-14): fields recoverable from repo sources are
        # pinned here; fields no source records stay null (unmeasured), never filled
        # by transfer from a different run or format.
        "receipts": {"count": len(d["receipts"]),
                     "manifest_sha256": hashlib.sha256(receipts_manifest.encode()).hexdigest(),
                     "source": src},
        "session_end": d["session_end"],
        "github_actions_inherited": {"source": metadata_src, "value": old["github_actions"],
                                     "note": "Final file records no Actions block; the same waves (wave1/wave2) that produced the full-coverage receipts are recorded in the 2026-11-12 coverage file."},
        "inference_settings_inherited": {"source": metadata_src, "value": old["inference_settings_completed_llm_arms"],
                                         "note": "Final file records no inference settings; inherited from the same-wave coverage file, not recorded in the final file itself."},
        "receipt_gap": {
            "model_bytes_sha256": None,
            "model_bytes_sha256_note": "Unmeasured for both LLM arms in this condition. The v1-actions-24 GGUF SHA (befm-actions receipt) is a different format and run and is NOT transferred here.",
            "prompt_version": None,
            "prompt_version_note": "No standalone prompt version or prompt SHA is recorded. evaluator_revision pins the evaluator code that contains the prompts, which is a code-level proxy only.",
            "generation_seed": None,
            "generation_seed_note": "No generation seed is recorded in any source for this condition. Sampling tasks therefore cannot be claimed exactly reproducible.",
        },
    }
    for key, r in sorted(d["results"].items()):
        if r["status"] != "OK":
            incomplete.append(dict(key=f"behaviorbench-final:{key}", status=r["status"],
                                   reason=r.get("reason"), n_expected=r.get("n_expected"),
                                   n_receipted=r.get("n_receipted")))
            continue
        require(r["n_receipted"] == r["n_expected"] == r["n"], "BehaviorBench final receipt count mismatch")
        meta = r.get("metadata") or {}
        invalid = meta.get("num_failed_parses")
        valid = meta.get("num_valid_predictions")
        if valid is not None:
            require(invalid is not None and valid + invalid == r["n"], "BehaviorBench final valid/invalid count mismatch")
        # game_behavior rows carry num_valid_predictions=null (distribution task, 50 draws);
        # failed parses are still recorded (0) and are not converted into a valid count.
        add(family(r["task"]), "behaviorbench-final", r["task"], r["arm"],
            r["n"], r["metrics_official"], src, invalid)
    src = "files/eval/behaviorbench-full-coverage-final-68of68-2026-11-14.json"
    d = read(root, src, sources)
    receipts_manifest = json.dumps(d["receipts"], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    conditions["behaviorbench-final-68"] = {
        **{k: d[k] for k in ("dataset_revision", "evaluator_revision", "coverage", "measured_at_utc")},
        # 68/68 completion (2026-11-14): this condition supersedes behaviorbench-final
        # as a separate condition; the older condition and its baseline stay untouched.
        "supersedes_condition": "behaviorbench-final",
        "supersedes_source": d["supersedes"],
        "completion_source": d["completion_source"],
        "github_actions_completion": d["github_actions_completion"],
        "receipts": {"count": len(d["receipts"]),
                     "manifest_sha256": hashlib.sha256(receipts_manifest.encode()).hexdigest(),
                     "source": src},
        "session_end": d["session_end"],
        "n_provenance_note": "66 rows carry the source field n (== n_expected == n_receipted). "
                             "The 2 completion rows (qwen3-4b-instruct-2507 multiround_behavior_guessing / "
                             "multiround_behavior_push_pull) omit both n and metadata in the source; for those "
                             "rows n is taken from n_receipted (500 == n_expected) and invalid_count stays "
                             "null (unmeasured), never zero-filled.",
        "receipt_gap": {
            "model_bytes_sha256": None,
            "model_bytes_sha256_note": "Unmeasured for both LLM arms in this condition, as in behaviorbench-final. Not transferred from any other run or format.",
            "prompt_version": None,
            "prompt_version_note": "No standalone prompt version or prompt SHA is recorded. evaluator_revision pins the evaluator code that contains the prompts, which is a code-level proxy only.",
            "generation_seed": None,
            "generation_seed_note": "No generation seed is recorded in any source for this condition. Sampling tasks therefore cannot be claimed exactly reproducible.",
        },
    }
    for key, r in sorted(d["results"].items()):
        if r["status"] != "OK":
            incomplete.append(dict(key=f"behaviorbench-final-68:{key}", status=r["status"],
                                   reason=r.get("reason"), n_expected=r.get("n_expected"),
                                   n_receipted=r.get("n_receipted")))
            continue
        require(r["n_receipted"] == r["n_expected"], "BehaviorBench final-68 receipt count mismatch")
        # The 2 completion rows omit the n field itself; n_receipted is the only
        # denominator the source records for them (see n_provenance_note).
        n = r.get("n", r["n_receipted"])
        require(n == r["n_receipted"], "BehaviorBench final-68 denominator mismatch")
        meta = r.get("metadata") or {}
        invalid = meta.get("num_failed_parses")
        valid = meta.get("num_valid_predictions")
        if valid is not None:
            require(valid is not None and invalid is not None and valid + invalid == n, "BehaviorBench valid/invalid count mismatch")
        add(family(r["task"]), "behaviorbench-final-68", r["task"], r["arm"],
            n, r["metrics_official"], src, invalid)
    return dict(schema_version=1, mode="offline_receipt_replay",
                sources_sha256=sources, conditions=conditions,
                rows=sorted(rows,key=lambda r:(r["family"],r["condition"],r["task"],r["arm"])),
                incomplete=incomplete,
                limitations=["No cross-family or cross-task scalar",
                             "Source NaN/Infinity metrics become null (undefined), never zero",
                             "BehaviorBench metrics retain official valid-prediction denominators; strict accuracy/regret unavailable",
                             "Prior full includes scored item; LOO separate. Game prior 1000 draws vs LLM 50: not same condition",
                             "Missing model hashes, prompt versions and seeds remain unmeasured; see source receipts",
                             "Replay verifies aggregation, not fresh inference or statistical significance"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--output", type=Path)
    p.add_argument("--check", type=Path, help="Fail on any change to the frozen replay, including provenance")
    args = p.parse_args()
    result = finite(aggregate(args.root))
    if args.check and result != json.loads(args.check.read_text()):
        raise SystemExit("REPRODUCTION_CONDITION_DIFFERENCE: investigate; do not overwrite baseline")
    payload = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+"\n"
    if args.output:
        args.output.write_text(payload)
    print(f"PASS: {len(result['rows'])} family/task/condition rows; {len(result['incomplete'])} incomplete arms; no pooled score")


if __name__ == "__main__":
    main()
