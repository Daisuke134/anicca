"""P04-5: Study-held-out effect forecasting benchmark, SYNTHETIC DATA ONLY.

The benchmark uses a genuine study-level holdout protocol, but none of the
studies are real. No result here establishes prediction on public human RCTs.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import numpy as np

SEED = 20261145
SPLITS = {"train": 90, "validation": 30, "heldout_in_domain": 30, "heldout_new_domain": 30}
BASE_FEATURES = ("baseline", "intensity", "burden")
PUBLIC_FIELDS = ("study_id", "domain", "baseline", "intensity", "burden", "planned_n", "expected_trial_se")
GOLD_FIELDS = ("study_id", "domain", "observed_trial_effect", "oracle_effect", "expected_trial_se")
LABEL = "observed_trial_effect"


def build_world(seed: int = SEED) -> list[dict]:
    rng = np.random.default_rng(seed)
    rows = []
    i = 0
    for split, count in SPLITS.items():
        for _ in range(count):
            i += 1
            domain = ("novel_C" if split == "heldout_new_domain"
                      else ("known_A" if i % 2 == 0 else "known_B"))
            baseline = float(rng.uniform(0.2, 0.8))
            intensity = float(rng.uniform(0.1, 0.9))
            burden = float(rng.uniform(0.0, 0.8))
            se = float(rng.uniform(0.010, 0.025))
            n = int(rng.integers(800, 4000))
            oracle = (0.008 + 0.062 * intensity - 0.074 * burden
                      + 0.031 * (baseline - 0.5)
                      + 0.022 * intensity * burden
                      + 0.012 * np.sin(5 * baseline)
                      + (0.043 if domain == "novel_C" else 0.0))
            observed = float(oracle + rng.normal(0, se))
            rows.append(dict(
                study_id=f"SYN-{i:04d}", domain=domain,
                baseline=baseline, intensity=intensity, burden=burden,
                planned_n=n, expected_trial_se=se,
                observed_trial_effect=observed, oracle_effect=oracle, split=split,
            ))
    return rows


def write_rows(path: Path, rows: list[dict], fields: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row[name] for name in fields})


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def make_release(folder: str | Path) -> dict:
    """Create simulated studies. Labels are absent from heldout public metadata."""
    out = Path(folder)
    rows = build_world()
    for split in ("train", "validation"):
        members = [r for r in rows if r["split"] == split]
        write_rows(out / f"P04-5_{split.upper()}_SYNTHETIC.csv", members,
                   PUBLIC_FIELDS + (LABEL,))
    heldout = [r for r in rows if r["split"].startswith("heldout")]
    write_rows(out / "P04-5_HOLDOUT_METADATA_SYNTHETIC.csv", heldout, PUBLIC_FIELDS)
    write_rows(out / "P04-5_GOLD_SYNTHETIC_FOR_SCORING_ONLY.csv",
               heldout, GOLD_FIELDS)
    return {split: sum(row["split"] == split for row in rows)
            for split in SPLITS}


def features(rows: list[dict]) -> np.ndarray:
    return np.array([[1.0, float(r["baseline"]) - 0.5, float(r["intensity"]),
                      float(r["burden"]), float(r["intensity"]) * float(r["burden"])]
                     for r in rows], dtype=float)


def ridge_fit(x: np.ndarray, y: np.ndarray, penalty: float) -> np.ndarray:
    regularizer = np.diag([0, 1, 1, 1, 1])
    return np.linalg.solve(x.T @ x + penalty * regularizer + np.eye(x.shape[1]) * 1e-10, x.T @ y)


def rmse(y: np.ndarray, pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y - pred) ** 2)))


def freeze_predictions(folder: str | Path) -> dict:
    """STRICTLY reads train/validation labels and held-out metadata, never gold."""
    out = Path(folder)
    train = read_rows(out / "P04-5_TRAIN_SYNTHETIC.csv")
    val = read_rows(out / "P04-5_VALIDATION_SYNTHETIC.csv")
    heldout = read_rows(out / "P04-5_HOLDOUT_METADATA_SYNTHETIC.csv")
    assert all(LABEL not in row and "oracle_effect" not in row for row in heldout)
    ids_train = {r["study_id"] for r in train}
    ids_val = {r["study_id"] for r in val}
    ids_test = {r["study_id"] for r in heldout}
    assert not (ids_train & ids_val or ids_train & ids_test or ids_val & ids_test)
    x_train, x_val = features(train), features(val)
    y_train = np.array([float(r[LABEL]) for r in train])
    y_val = np.array([float(r[LABEL]) for r in val])
    choices = [0.0001, 0.01, 0.1, 1.0]
    candidates = [(rmse(y_val, x_val @ ridge_fit(x_train, y_train, c)), c)
                  for c in choices]
    _, penalty = min(candidates)
    pool = train + val
    weight = ridge_fit(features(pool), np.array([float(r[LABEL]) for r in pool]), penalty)
    predictions = features(heldout) @ weight
    constant = float(np.mean([float(r[LABEL]) for r in pool]))
    output = []
    for row, pred in zip(heldout, predictions):
        output.append({
            "study_id": row["study_id"],
            "domain": row["domain"],
            "prediction_zero": f"{0.0:.9f}",
            "prediction_mean": f"{constant:.9f}",
            "prediction_ridge": f"{float(pred):.9f}",
        })
    pred_path = out / "P04-5_FROZEN_PREDICTIONS_SYNTHETIC.csv"
    write_rows(pred_path, output, tuple(output[0]))
    digest = hashlib.sha256(pred_path.read_bytes()).hexdigest()
    receipt = {"dataset": "fully synthetic; NOT genuine public RCT forecasts",
               "prediction_sha256": digest, "n_train": len(train),
               "n_validation": len(val), "n_heldout": len(heldout),
               "ridge_penalty_selected_on_validation": penalty,
               "public_features": list(PUBLIC_FIELDS),
               "gold_read_during_prediction": False}
    (out / "P04-5_FREEZE_RECEIPT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


def metrics(y: np.ndarray, p: np.ndarray, threshold: np.ndarray) -> dict[str, float]:
    error = p - y
    resolved = np.abs(y) > threshold
    correct_sign = np.sign(p) == np.sign(y)
    return {
        "mae": float(np.mean(np.abs(error))),
        "rmse": rmse(y, p),
        "sign_accuracy_all": float(np.mean(correct_sign)),
        "sign_accuracy_observed_effect_larger_than_se":
            float(np.mean(correct_sign[resolved])) if np.any(resolved) else None,
        "n_resolved": int(np.sum(resolved)),
        "pearson_r": float(np.corrcoef(p, y)[0, 1]) if np.std(p) > 1e-9 else None,
    }


def score_frozen(folder: str | Path) -> dict:
    """Open the synthetic gold file ONLY after predictions are frozen and hashed."""
    out = Path(folder)
    pred_path = out / "P04-5_FROZEN_PREDICTIONS_SYNTHETIC.csv"
    pred_data = pred_path.read_bytes()
    receipt = json.loads((out / "P04-5_FREEZE_RECEIPT.json").read_text(encoding="utf-8"))
    if hashlib.sha256(pred_data).hexdigest() != receipt["prediction_sha256"]:
        raise ValueError("Frozen predictions changed after registration")
    preds = read_rows(pred_path)
    gold = read_rows(out / "P04-5_GOLD_SYNTHETIC_FOR_SCORING_ONLY.csv")
    by_id = {row["study_id"]: row for row in gold}
    if len(by_id) != len(preds) or set(by_id) != {r["study_id"] for r in preds}:
        raise ValueError("Study IDs in predictions and gold are not identical")
    results = {
        "dataset": "synthetic study holdout (not public RCT)",
        "prediction_sha256": receipt["prediction_sha256"],
        "n_train": receipt["n_train"],
        "n_validation": receipt["n_validation"],
        "n_heldout": receipt["n_heldout"],
        "metrics_by_split": {},
        "public_rct_out_of_study_validation": "NOT PERFORMED",
    }
    for name, selector in [
        ("in_domain", lambda p: p["domain"] != "novel_C"),
        ("new_domain", lambda p: p["domain"] == "novel_C"),
        ("all", lambda p: True),
    ]:
        part = [p for p in preds if selector(p)]
        y = np.array([float(by_id[p["study_id"]][LABEL]) for p in part])
        truth = np.array([float(by_id[p["study_id"]]["oracle_effect"]) for p in part])
        se = np.array([float(by_id[p["study_id"]]["expected_trial_se"]) for p in part])
        results["metrics_by_split"][name] = {
            "n_studies": len(part),
            "ridge": metrics(y, np.array([float(p["prediction_ridge"]) for p in part]), se),
            "mean": metrics(y, np.array([float(p["prediction_mean"]) for p in part]), se),
            "zero": metrics(y, np.array([float(p["prediction_zero"]) for p in part]), se),
            "ridge_oracle_mae_simulator_only":
                float(np.mean(np.abs(np.array([float(p["prediction_ridge"]) for p in part]) - truth))),
        }
    (out / "P04-5_SYNTHETIC_BENCHMARK_RESULTS.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return results


def run(folder: str | Path) -> dict:
    make_release(folder)
    freeze_predictions(folder)
    return score_frozen(folder)


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent / "evidence"
    print(json.dumps(run(base), ensure_ascii=False, indent=2))
