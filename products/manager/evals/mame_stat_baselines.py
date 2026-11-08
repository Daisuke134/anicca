"""Todo #1 (BFM-01): statistical baselines re-scored on the SAME frozen
MaMe-Re slice and split as the BFM-02 Qwen3-4B pilot.

Methods, all trained/scored without ever touching test-context labels:
  * train_mean   -- the BFM-02 recorded baseline: choose the candidate whose
                    mean human score over the 160 TRAIN contexts is higher.
  * ridge        -- Ridge regression (score ~ features) fit on the 160x400
                    train grid only; choose the candidate with higher
                    predicted score for the held-out test context.
  * random_forest-- RandomForestRegressor, same features/target/protocol.

Features per (context, item) use NO label from the context being scored:
  item_mean       item's mean score over train contexts (leave-one-context-out
                  when the scored context is itself a train context),
  item_std        item's train-score std (same leave-one-out rule),
  item_mean_rank  percentile rank of item_mean across the 400 items,
  tfidf_cos       character n-gram TF-IDF cosine between the context text and
                  the item description (unsupervised; fitted on texts only),
  desc_len        description length in characters,
  ctx_len         context length in characters.

Scoring reuses qwen3_mame_text_eval.score_pairs verbatim, so strict win
accuracy and mean regret are defined identically to the Qwen3-4B receipts.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.metrics.pairwise import cosine_similarity

from qwen3_mame_text_eval import (
    build_cases,
    download_pinned_text_data,
    frozen_split,
    load_labeled_table,
    score_pairs,
    verify_sources,
)

SEED = 20261107


def build_features(contexts, descriptions, scores, train_ids):
    """Return a function features(ctx_id, item_id) -> np.array (float64)."""
    n_items = len(descriptions)
    sums = np.zeros(n_items)
    sq_sums = np.zeros(n_items)
    for i in train_ids:
        for j in range(n_items):
            v = scores[(i, j)]
            sums[j] += v
            sq_sums[j] += v * v
    n_train = len(train_ids)
    item_mean_full = sums / n_train
    order = item_mean_full.argsort()
    ranks = np.empty(n_items)
    ranks[order] = np.arange(n_items)
    item_rank_pct = ranks / (n_items - 1)

    corpus = [contexts[i] for i in sorted(contexts)] + \
             [descriptions[j] for j in sorted(descriptions)]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                                 max_features=20000, sublinear_tf=True)
    matrix = vectorizer.fit_transform(corpus)
    ctx_vec = {cid: matrix[k] for k, cid in enumerate(sorted(contexts))}
    item_vec = {iid: matrix[len(contexts) + k]
                for k, iid in enumerate(sorted(descriptions))}

    def features(ctx_id: int, item_id: int) -> np.ndarray:
        if ctx_id in train_ids:
            own = scores[(ctx_id, item_id)]
            mean = (sums[item_id] - own) / (n_train - 1)
            var = (sq_sums[item_id] - own * own) / (n_train - 1) - mean * mean
        else:
            mean = item_mean_full[item_id]
            var = sq_sums[item_id] / n_train - mean * mean
        std = math.sqrt(max(var, 0.0))
        cos = float(cosine_similarity(ctx_vec[ctx_id], item_vec[item_id])[0, 0])
        return np.array([mean, std, item_rank_pct[item_id], cos,
                         float(len(descriptions[item_id])),
                         float(len(contexts[ctx_id]))], dtype=np.float64)

    return features


def method_choices(cases, chooser):
    rows = []
    for case in cases:
        choice = chooser(case)
        rows.append({
            "context_id": case["context_id"], "item_a": case["item_a"],
            "item_b": case["item_b"], "prior_mode": case["prior_mode"],
            "model": choice, "baseline": case["baseline"],
            "human_a": case["human_a"], "human_b": case["human_b"],
        })
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--n-cases", type=int, default=24)
    args = p.parse_args()

    download_pinned_text_data(args.input_dir)
    contexts, descriptions, scores = load_labeled_table(args.input_dir)
    train_ids, _, _ = frozen_split()
    train_set = set(train_ids)
    cases = build_cases(args.input_dir, n_cases=args.n_cases)
    features = build_features(contexts, descriptions, scores, train_set)

    # Fit regressors on the full train grid only (160 contexts x 400 items).
    item_ids = sorted(descriptions)
    X_train, y_train = [], []
    for i in train_ids:
        for j in item_ids:
            X_train.append(features(i, j))
            y_train.append(scores[(i, j)])
    X_train = np.vstack(X_train)
    y_train = np.array(y_train)

    ridge = Ridge(alpha=1.0)
    ridge.fit(X_train, y_train)
    forest = RandomForestRegressor(
        n_estimators=400, max_depth=10, min_samples_leaf=5,
        n_jobs=4, random_state=SEED)
    forest.fit(X_train, y_train)

    def pick(predict):
        def choose(case):
            pa = float(predict(features(case["context_id"], case["item_a"])))
            pb = float(predict(features(case["context_id"], case["item_b"])))
            if abs(pa - pb) < 1e-12:
                return case["baseline"]  # deterministic tie -> train-mean choice
            return "A" if pa > pb else "B"
        return choose

    results = {}
    detail = {}
    methods = {
        "train_mean": lambda case: case["baseline"],
        "ridge": pick(lambda x: ridge.predict([x])[0]),
        "random_forest": pick(lambda x: forest.predict([x])[0]),
    }
    for name, chooser in methods.items():
        rows = method_choices(cases, chooser)
        results[name] = score_pairs(rows)
        detail[name] = [{"context_id": r["context_id"], "choice": r["model"]}
                        for r in rows]

    out = {
        "status": "STATISTICAL_BASELINES_SAME_FROZEN_SLICE_AS_BFM02",
        "dataset": "CyberAgent AI Lab MaMe-Re",
        "file_sha256": verify_sources(args.input_dir),
        "holdout": ("frozen prior P09-5 context-disjoint 160 train/40 valid/50 "
                    "test; identical 24 selected heldout contexts, seed "
                    "20261107, as BFM-02 (run 42486958602 and re-runs)"),
        "n_cases": len(cases),
        "n_train_rows": int(X_train.shape[0]),
        "features": ["item_mean_train_LOCO", "item_std_train_LOCO",
                     "item_mean_percentile_rank", "tfidf_charwb_2_4_cosine",
                     "description_chars", "context_chars"],
        "leakage_controls": [
            "regressors fit on train contexts only",
            "item statistics for a train row exclude that row's own context",
            "no test-context label is used by features, selection or fitting",
            "candidate pairs and test contexts are the frozen BFM-02 selection",
        ],
        "methods": results,
        "choices": detail,
        "comparison_reference": (
            "Qwen3-4B GGUF receipts from workflow manager-bfm02: strict "
            "accuracy and mean regret are computed by the identical "
            "score_pairs function on the identical cases"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps({k: {"strict": v["model_strict_win_accuracy_including_invalid"],
                          "regret": v["mean_model_regret_invalid_counted"],
                          "n_non_tied": v["n_human_non_tied"]}
                      for k, v in results.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
