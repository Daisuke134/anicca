"""Manager BFM-01: train and export a tiny, inspectable human-outcome baseline.

This is a model for RCT study-ARM smoking cessation rates, not a general
Behavioral Foundation Model, not personal treatment advice, and not causal.
Reuses existing HBCP/Ridge code ideas, source URL/hash and study-disjoint
evaluation. Original HBCP annotated training dataset is CC0 (paper).
Weights are exported as plain JSON—no unsafe pickle deserialization.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import urllib.request
from pathlib import Path
from typing import Mapping

LABEL = "('Outcome', 'Outcome')"
SOURCE_URL = ("https://raw.githubusercontent.com/"
              "HumanBehaviourChangeProject/semantic-prediction/main/data/hbcp_gen.csv")
SHA = "eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b"
MODEL_ID = "manager-hbcp-ridge-arm-rate-v0"
ALPHA = 30.0


def source_rows() -> list[dict[str, str]]:
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Manager-HBCP/1.0"})
    with urllib.request.urlopen(req, timeout=25) as res:
        raw = res.read(900_000)
    if hashlib.sha256(raw).hexdigest() != SHA:
        raise ValueError("original HBCP training data does not match pinned bytes")
    result = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if len(result) != 971:
        raise ValueError("published dataset arm count changed")
    return result


def numeric_matrix(records: list[dict]):
    import numpy as np
    import pandas as pd
    if not records or LABEL not in records[0]:
        raise ValueError("missing original HBCP schema")
    excluded = {"", "doc_id", "arm_id", "doc", "arm", LABEL}
    feature_names = [k for k in records[0] if k not in excluded]
    df = pd.DataFrame([{k: r.get(k) for k in feature_names} for r in records])
    matrix = df.apply(pd.to_numeric, errors="coerce")
    matrix = matrix.loc[:, matrix.notna().any(axis=0)]
    y = np.array([float(r[LABEL]) for r in records], dtype=float)
    if not np.isfinite(y).all() or not np.logical_and(0 <= y, y <= 100).all():
        raise ValueError("numeric outcome rates must be in 0..100")
    return matrix, y


def predict_json(model: Mapping, source_features: Mapping[str, object]) -> float:
    """Pure Python deterministic prediction from fixed named study-arm features.

    Do not pass individual health histories. Only aggregated original research
    annotation categories are valid input; no trial ID or outcome allowed.
    """
    if model.get("model_id") != MODEL_ID:
        raise ValueError("unknown or unverified model")
    columns = model["feature_names"]
    medians = model["median_imputation"]
    missing_indices = model["missing_indicator_feature_indices"]
    weights = model["coefficients"]
    if set(source_features) - set(columns):
        raise ValueError("unexpected feature/identity key")
    if len(columns) != len(medians) or len(weights) != len(columns) + len(missing_indices):
        raise ValueError("malformed model card/coefficients")
    values = []
    missing_flags = []
    for k, med in zip(columns, medians):
        v = source_features.get(k)
        try:
            num = float(v) if v is not None and v != "" else math.nan
        except (TypeError, ValueError, OverflowError):
            num = math.nan
        bad = not math.isfinite(num)
        values.append(float(med) if bad else num)
        missing_flags.append(1.0 if bad else 0.0)
    values.extend(missing_flags[i] for i in missing_indices)
    estimate = float(model["intercept"]) + sum(float(w) * x for w, x in zip(weights, values))
    if not math.isfinite(estimate):
        raise ValueError("nonfinite prediction")
    return max(0.0, min(100.0, estimate))


def fit_model(records: list[dict]) -> tuple[dict, dict]:
    import numpy as np
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import make_pipeline
    X, y = numeric_matrix(records)
    if len(X) != 971:
        raise ValueError("wrong training corpus")
    groups = [r["doc"] for r in records]
    if len(set(groups)) != 405:
        raise ValueError("unexpected study count")
    pipeline = make_pipeline(SimpleImputer(strategy="median", add_indicator=True),
                             Ridge(alpha=ALPHA))
    pipeline.fit(X, y)
    imputer = pipeline.named_steps["simpleimputer"]
    ridge = pipeline.named_steps["ridge"]
    indicator = [int(i) for i in imputer.indicator_.features_]
    coefficients = [float(a) for a in ridge.coef_]
    model = {
        "schema_version": "1",
        "model_id": MODEL_ID,
        "model_family": "linear_Ridge_regression_study_arm_outcome",
        "original_source": SOURCE_URL,
        "source_sha256": SHA,
        "source_license": "CC0 1.0 per original HBCP manuscript",
        "study_id_count": len(set(groups)),
        "intervention_arms": len(records),
        "feature_names": list(X.columns),
        "median_imputation": [float(a) for a in imputer.statistics_],
        "missing_indicator_feature_indices": indicator,
        "coefficients": coefficients,
        "intercept": float(ridge.intercept_),
        "ridge_alpha": ALPHA,
        "prediction_target": "observed_RCT_study_arm_smoking_cessation_percent",
        "causal_effect_estimated": False,
        "individual_level_predictions": False,
        "clinical_decision_support_approved": False,
        "trained_behavioral_foundation_model": False,
    }
    if len(coefficients) != len(X.columns) + len(indicator):
        raise AssertionError("export dimensions differ from fitted sklearn model")
    # Prove interchangeability between the inspectable JSON and learned sklearn.
    sk = pipeline.predict(X)
    js = [predict_json(model, {k: r.get(k) for k in model["feature_names"]})
          for r in records]
    expected = np.clip(sk, 0, 100)
    max_delta = float(np.max(np.abs(expected - js)))
    if max_delta > 1e-6:
        raise AssertionError("exported open JSON weights differ from trained model")
    return model, {
        "n_arms": len(records), "n_studies": len(set(groups)),
        "features": int(X.shape[1]), "coefficients": len(coefficients),
        "max_export_vs_sklearn_error_pct_points": max_delta,
        "training_fit_not_holdout_accuracy": True,
        "source_sha256": SHA,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--receipt", required=True)
    args = parser.parse_args()
    model, qa = fit_model(source_rows())
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(model, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
    out.write_text(content)
    qa["weights_sha256"] = hashlib.sha256(content.encode()).hexdigest()
    qa["model_file"] = out.name
    qa["warning"] = ("Study-arm research outcome baseline only; not Manager BFM, "
                     "not causal and not an individual medical recommendation.")
    dest = Path(args.receipt)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(qa, indent=2, sort_keys=True) + "\n")
    print(json.dumps(qa, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
