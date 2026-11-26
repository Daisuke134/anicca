#!/usr/bin/env python3
"""Population-mean (prior_marginal) wrapper + official-metric record layer.

Evaluation-only. Does not train. Does not redistribute BehaviorBench data
(CC BY-NC-ND 4.0). Requires a local clone of befm/BehaviorBench and
umich-foreseer/behaviorbench_eval.

Primary prior (prior_marginal_full): for each official test item, predict the
empirical mode (classification / Likert / push-pull / multi-choice) or mean
(numeric) of the same group on the same official test split. Groups follow the
official group_by (Big Five dimension or target item). This is the definition
that reproduces Muse's published full-split survey Acc 0.3944 (surv_resp_pred).
It uses the evaluation labels, so it is a leakage-light baseline, not a
deployable model.

Secondary prior (prior_loo): same statistic with the current item held out.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


SKIP_TASKS = {
    # BLEURT checkpoint not installed; out of scope for this run.
    "workflow_idea_generation",
    "workflow_method_recommendation",
    "workflow_outcome_prediction",
    "workflow_title_prediction",
    "workflow_impact_prediction",
    "research_workflow",
    # Win-rate task needs a different protocol; not a population-mean prior.
    "strategic_gameplay_guessing",
    "game_behavior",  # generic base, not a concrete file
}

# Official classification metrics that need sklearn (f1_macro). Dropped here
# if sklearn is missing; Accuracy is retained.
OPTIONAL_SKLEARN_METRICS = {"f1_macro", "F1_macro"}


def _jsonable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, (np.integer, int)):
        return int(obj)
    if isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    if obj is None or isinstance(obj, str):
        return obj
    return str(obj)


def _mode(values: list[Any]) -> Any:
    if not values:
        raise ValueError("mode of empty list")
    counts = Counter(values)
    best = max(counts.values())
    # Deterministic tie-break: first most_common then smallest/lexical.
    tied = [k for k, c in counts.items() if c == best]
    try:
        return sorted(tied, key=lambda x: (str(type(x).__name__), x))[0]
    except TypeError:
        return sorted(tied, key=lambda x: str(x))[0]


def _mean(values: list[Any]) -> float:
    arr = np.asarray(values, dtype=float)
    return float(np.mean(arr))


def _policy_for(output_type: str) -> str:
    if output_type in {"integer", "push_pull", "multi_choice", "choice"}:
        return "mode"
    return "mean"


def _format_output(value: Any, output_type: str) -> str:
    if output_type in {"multi_choice", "choice"}:
        return str(value)
    if output_type == "push_pull":
        # Official parser: [Push] -> 0, [Pull] -> 1
        iv = int(round(float(value)))
        return "[Pull]" if iv == 1 else "[Push]"
    if output_type == "integer":
        return f"[{int(round(float(value)))}]"
    # numeric
    fv = float(value)
    if abs(fv - round(fv)) < 1e-9:
        return f"[{int(round(fv))}]"
    return f"[{fv:.4f}]"


class FrozenBatchModel:
    """Return precomputed outputs in order. Used with official run_evaluation."""

    def __init__(self, outputs: list[str], repeat: str | None = None):
        self.outputs = list(outputs)
        self.repeat = repeat

    def batch_call(self, prompts: list[Any], **kwargs) -> list[str]:
        if self.repeat is not None:
            return [self.repeat] * len(prompts)
        if len(prompts) != len(self.outputs):
            raise ValueError(
                f"FrozenBatchModel got {len(prompts)} prompts but has {len(self.outputs)} outputs"
            )
        return list(self.outputs)

    def __call__(self, prompt: Any, **kwargs) -> str:
        if self.repeat is not None:
            return self.repeat
        raise TypeError("per-prompt call requires repeat or a pop interface")


def _task_output_type(task_name: str, load_task_config) -> str:
    cfg = load_task_config()
    return cfg.get(task_name, {}).get("output_type", "numeric")


def _is_game_behavior(task) -> bool:
    return task.__class__.__name__.startswith("GameBehavior") or getattr(
        task, "num_samples_per_game", None
    ) is not None and task.name.startswith("game_behavior")


def _build_grouped_predictions(
    golds: list[Any],
    groups: list[str] | None,
    policy: str,
    loo: bool,
) -> list[Any]:
    n = len(golds)
    if groups is None:
        groups = ["__all__"] * n
    by: dict[str, list[tuple[int, Any]]] = defaultdict(list)
    for i, (y, g) in enumerate(zip(golds, groups, strict=True)):
        by[g].append((i, y))
    preds: list[Any] = [None] * n
    for g, items in by.items():
        idxs = [i for i, _ in items]
        vals = [v for _, v in items]
        if not loo:
            stat = _mode(vals) if policy == "mode" else _mean(vals)
            for i in idxs:
                preds[i] = stat
        else:
            for j, i in enumerate(idxs):
                pool = [vals[k] for k in range(len(vals)) if k != j]
                if not pool:
                    # singleton group: fall back to global (excluding self if possible)
                    global_pool = [golds[k] for k in range(n) if k != i]
                    pool = global_pool or vals
                preds[i] = _mode(pool) if policy == "mode" else _mean(pool)
    return preds


def _human_human_w(
    human: list[float],
    n_repeat: int,
    seed: int,
    value_range: tuple[float, float] | None,
    normalize_range: tuple[float, float] | None,
    wasserstein_fn,
) -> dict[str, float]:
    rng = np.random.default_rng(seed)
    arr = np.asarray(human, dtype=float)
    n = len(arr)
    if n < 4:
        return {"n_human": n, "repeats": 0}
    # Match Muse's split: 50 predict / 150 reference when n=200; else 25%/75%.
    n_pred = 50 if n == 200 else max(1, n // 4)
    distances = []
    for _ in range(n_repeat):
        perm = rng.permutation(n)
        pred = arr[perm[:n_pred]]
        ref = arr[perm[n_pred:]]
        distances.append(
            float(
                wasserstein_fn(
                    pred,
                    ref,
                    value_range=value_range,
                    normalize_range=normalize_range,
                )
            )
        )
    d = np.asarray(distances, dtype=float)
    return {
        "n_human": n,
        "n_pred_side": n_pred,
        "n_ref_side": n - n_pred,
        "repeats": n_repeat,
        "seed": seed,
        "W_mean": float(np.mean(d)),
        "W_std": float(np.std(d, ddof=1) if len(d) > 1 else 0.0),
    }


def run_one(
    task_name: str,
    data_path: Path,
    TASK_REGISTRY,
    load_task_config,
    wasserstein_fn,
    num_samples_per_game: int,
    hh_repeats: int,
    hh_seed: int,
) -> dict[str, Any]:
    output_type = _task_output_type(task_name, load_task_config)
    policy = _policy_for(output_type)
    task_cls = TASK_REGISTRY[task_name]
    task = task_cls(data_path=str(data_path), name=task_name)
    # Drop sklearn-only metrics so the official scorer can run without sklearn.
    if hasattr(task, "_metrics"):
        task._metrics = [m for m in task.metrics if m not in OPTIONAL_SKLEARN_METRICS]
    elif hasattr(task, "metrics") and isinstance(task.metrics, list):
        # ConfigurableTask uses self.metrics as an attribute
        try:
            task.metrics = [m for m in task.metrics if m not in OPTIONAL_SKLEARN_METRICS]
        except Exception:
            pass

    task.load_data()
    is_game = task.name.startswith("game_behavior") and hasattr(task, "human_actions")
    record: dict[str, Any] = {
        "task": task_name,
        "data_path_relative": str(data_path),
        "output_type": output_type,
        "prior_policy": policy,
        "official_metrics_requested": list(task.metrics),
        "skipped_metrics": sorted(OPTIONAL_SKLEARN_METRICS.intersection(set(getattr(task, "metrics", [])).union(OPTIONAL_SKLEARN_METRICS))),
    }

    if is_game:
        human = list(task.human_actions)
        record["n_human"] = len(human)
        mu = _mean(human)
        # Point-mass population mean, official protocol (N samples of the same mean).
        model = FrozenBatchModel([], repeat=_format_output(mu, output_type if output_type != "push_pull" else "push_pull"))
        # For push_pull, mean is not the right primary; also emit mode.
        results = {}
        # mean arm
        mean_model = FrozenBatchModel([], repeat=_format_output(mu, "numeric" if output_type != "push_pull" else "push_pull"))
        if output_type == "push_pull":
            mean_model = FrozenBatchModel([], repeat=_format_output(round(mu), "push_pull"))
        ev_mean = task.run_evaluation(mean_model, num_samples=num_samples_per_game)
        results["prior_constant_mean"] = {
            "value": mu,
            "num_samples_emitted": num_samples_per_game,
            "metrics": _jsonable(ev_mean.metrics),
            "metadata": _jsonable(ev_mean.metadata),
        }
        mode_v = _mode([int(round(float(x))) if output_type in {"push_pull", "integer"} else x for x in human])
        ev_mode = task.run_evaluation(
            FrozenBatchModel([], repeat=_format_output(mode_v, output_type)),
            num_samples=num_samples_per_game,
        )
        results["prior_constant_mode"] = {
            "value": mode_v,
            "num_samples_emitted": num_samples_per_game,
            "metrics": _jsonable(ev_mode.metrics),
            "metadata": _jsonable(ev_mode.metadata),
        }
        clip = getattr(task, "clip_range", None)
        norm = getattr(task, "normalize_range", None)
        results["human_human_split_half"] = _human_human_w(
            human,
            n_repeat=hh_repeats,
            seed=hh_seed,
            value_range=tuple(clip) if clip else None,
            normalize_range=tuple(norm) if norm else None,
            wasserstein_fn=wasserstein_fn,
        )
        record["arms"] = results
        record["primary_arm"] = "prior_constant_mean"
        return record

    # Item-level tasks (Big Five, multiround, acrossgame, IEO)
    golds = list(task.ground_truth)
    if hasattr(task, "_extract_group") and getattr(task, "_group_by", None):
        groups = [task._extract_group(p) for p in task.prompts]
    else:
        groups = None
    record["n"] = len(golds)
    if groups is not None:
        record["group_by"] = task._group_by
        record["n_groups"] = len(set(groups))

    arms = {}
    for arm_name, loo in (("prior_marginal_full", False), ("prior_loo", True)):
        preds = _build_grouped_predictions(golds, groups, policy, loo=loo)
        outputs = [_format_output(v, output_type) for v in preds]
        ev = task.run_evaluation(FrozenBatchModel(outputs))
        arms[arm_name] = {
            "loo": loo,
            "policy": policy,
            "metrics": _jsonable(ev.metrics),
            "metadata": _jsonable(
                {k: v for k, v in ev.metadata.items() if k != "predictions"}
            ),
            "num_failed_parses": ev.metadata.get("num_failed_parses"),
        }
    record["arms"] = arms
    record["primary_arm"] = "prior_marginal_full"
    return record


def resolve_data_path(task_name: str, data_root: Path, default_paths: dict[str, str]) -> Path:
    rel = default_paths[task_name]
    # DEFAULT_DATA_PATHS start with "data/"
    rel_path = Path(rel)
    parts = rel_path.parts
    if parts and parts[0] == "data":
        rel_path = Path(*parts[1:]) if len(parts) > 1 else Path(".")
    candidate = data_root / rel_path
    if not candidate.exists():
        raise FileNotFoundError(f"{task_name}: {candidate} not found")
    return candidate


def git_sha(repo: Path) -> str | None:
    head = repo / ".git" / "HEAD"
    if not head.exists():
        return None
    text = head.read_text().strip()
    if text.startswith("ref:"):
        ref = text.split(" ", 1)[1].strip()
        ref_path = repo / ".git" / ref
        if ref_path.exists():
            return ref_path.read_text().strip()
        # packed-refs fallback
        packed = repo / ".git" / "packed-refs"
        if packed.exists():
            for line in packed.read_text().splitlines():
                if line.endswith(ref) and not line.startswith("#"):
                    return line.split()[0]
        return None
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--evaluator-src", type=Path, required=True, help="path to behaviorbench_eval/src")
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--tasks", nargs="*", default=None)
    parser.add_argument("--num-samples-per-game", type=int, default=1000)
    parser.add_argument("--hh-repeats", type=int, default=200)
    parser.add_argument("--hh-seed", type=int, default=20261111)
    args = parser.parse_args()

    src = args.evaluator_src.resolve()
    sys.path.insert(0, str(src))
    from behaviorbench.eval.main import DEFAULT_DATA_PATHS, TASK_REGISTRY  # noqa: E402
    from behaviorbench.eval.tasks import load_task_config  # noqa: E402
    from behaviorbench.eval.metrics import wasserstein  # noqa: E402

    evaluator_root = src.parent
    tasks = args.tasks or [
        t
        for t in DEFAULT_DATA_PATHS
        if t in TASK_REGISTRY and t not in SKIP_TASKS
    ]

    results = []
    errors = []
    for task_name in tasks:
        data_path = resolve_data_path(task_name, args.data_root, DEFAULT_DATA_PATHS)
        print(f"== {task_name} == {data_path}", flush=True)
        try:
            rec = run_one(
                task_name,
                data_path,
                TASK_REGISTRY,
                load_task_config,
                wasserstein,
                num_samples_per_game=args.num_samples_per_game,
                hh_repeats=args.hh_repeats,
                hh_seed=args.hh_seed,
            )
            results.append(rec)
            primary = rec["arms"][rec["primary_arm"]]
            metrics = primary.get("metrics", {})
            # compact stdout
            keys = [k for k in metrics if not k.endswith("_per_group") and not isinstance(metrics[k], dict)]
            summary = {k: metrics[k] for k in keys[:8]}
            print("   ", rec["primary_arm"], summary, flush=True)
        except Exception as exc:
            print(f"   ERROR {type(exc).__name__}: {exc}", flush=True)
            errors.append({"task": task_name, "error": f"{type(exc).__name__}: {exc}"})

    payload = {
        "title": "BehaviorBench population-mean prior (prior_marginal) — 2026-11-12",
        "run_started_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": "befm/BehaviorBench",
        "dataset_revision": git_sha(args.data_root) or "unknown",
        "evaluator": "umich-foreseer/behaviorbench_eval",
        "evaluator_revision": git_sha(evaluator_root) or "unknown",
        "license": "Dataset CC BY-NC-ND 4.0 (eval only, not redistributed). Evaluator MIT.",
        "citation": "Huang et al., BehaviorBench, arXiv:2606.24162",
        "mg_cursor_note": "Does not advance MG-02. External calibration only; MG-04 gate remains MaMe-Re.",
        "definition": {
            "prior_marginal_full": "Grouped empirical mode (classification) or mean (numeric) on the official test split, including the scored item. Reproduces Muse full-split surv_resp_pred Acc 0.3944.",
            "prior_loo": "Same grouped statistic with the scored item held out.",
            "prior_constant_mean": "For first-round game_behavior: official protocol of N identical draws of the population mean (point mass).",
            "prior_constant_mode": "Same protocol with the population mode.",
            "human_human_split_half": "Not a model. Split human actions (50/150 when n=200) and measure W; seed 20261111, 200 repeats, to sit next to Muse's published human baseline.",
        },
        "num_samples_per_game": args.num_samples_per_game,
        "tasks_attempted": tasks,
        "results": results,
        "errors": errors,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(_jsonable(payload), indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {args.out_json} tasks_ok={len(results)} errors={len(errors)}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
