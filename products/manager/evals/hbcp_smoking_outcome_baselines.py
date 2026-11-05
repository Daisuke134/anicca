"""Reproduce *baseline* outcome forecasts on existing HBCP RCT-arm annotations.

The dataset contains 971 reported arms across ~405 studies, each an aggregated
smoking cessation rate. Reuse original real-world HBCP data and sklearn models,
NOT invented people. Evaluate with study-disjoint GroupKFold (no trial-arm leak).
Not the authors' released RuleNN, and not proof of any individual BCT effect.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import urllib.request

SOURCE_URL = (
    "https://raw.githubusercontent.com/HumanBehaviourChangeProject/"
    "semantic-prediction/main/data/hbcp_gen.csv"
)
SOURCE_SHA256 = "eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b"


def run() -> dict:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import GroupKFold
    from sklearn.pipeline import make_pipeline

    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent":"ManagerOutcomePrediction/0.1"})
    with urllib.request.urlopen(req,timeout=25) as response:
        raw = response.read(800_000)
    if hashlib.sha256(raw).hexdigest()!=SOURCE_SHA256:
        raise ValueError("source changed; do not silently alter model results")
    records = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if len(records)!=971:
        raise ValueError("unexpected original RCT arm count")
    target = "('Outcome', 'Outcome')"
    nonfeatures = {"", "doc_id", "arm_id", "doc", "arm", target}
    features=[c for c in records[0] if c not in nonfeatures]
    raw_features=pd.DataFrame([{c:r[c] for c in features} for r in records])
    X=raw_features.apply(pd.to_numeric,errors="coerce")
    X = X.loc[:, X.notna().any(axis=0)]
    y=np.array([float(r[target]) for r in records],dtype=float)
    groups=np.array([r["doc"] for r in records])
    if not np.isfinite(y).all() or not (0<=y).all() or not (y<=100).all():
        raise ValueError("outcome rates outside percentage range")
    if len(np.unique(groups))<300:
        raise ValueError("study identity was not recovered")
    if (X.isna().mean(axis=0)==1).any():
        raise ValueError("unusable feature")
    folds=GroupKFold(n_splits=5)
    preds={k:np.full(y.shape,np.nan) for k in ("train_mean","ridge","random_forest")}
    splitsets=[]
    for fold,(tr,te) in enumerate(folds.split(X,y,groups)):
        if set(groups[tr]).intersection(groups[te]):
            raise AssertionError("study train-test leakage")
        splitsets.append({"fold":fold,"train_studies":int(len(set(groups[tr]))),
                          "test_studies":int(len(set(groups[te]))),
                          "test_arms":int(len(te))})
        preds["train_mean"][te]=float(np.mean(y[tr]))
        candidates={
            "ridge": make_pipeline(SimpleImputer(strategy="median",add_indicator=True),
                                    Ridge(alpha=30.0)),
            "random_forest": make_pipeline(SimpleImputer(strategy="median",add_indicator=True),
                       RandomForestRegressor(n_estimators=200,min_samples_leaf=8,
                                             random_state=20261106,n_jobs=2))
        }
        for name,model in candidates.items():
            model.fit(X.iloc[tr],y[tr])
            preds[name][te]=np.clip(model.predict(X.iloc[te]),0,100)
    results={}
    for key,p in preds.items():
        if not np.isfinite(p).all():
            raise ValueError("not all heldout groups predicted")
        error=np.abs(y-p)
        results[key]={"mae_percentage_points":float(error.mean()),
                      "rmse_percentage_points":float(np.sqrt(np.mean((y-p)**2)))}
    return {
        "source":SOURCE_URL,
        "sha256":SOURCE_SHA256,
        "paper":"https://doi.org/10.12688/wellcomeopenres.19975.2",
        "source_kind":"published_aggregated_real_RCT_intervention_arms",
        "n_arms":len(records),
        "n_studies":int(len(set(groups))),
        "n_features_after_numeric_coercion":int(X.shape[1]),
        "study_group_key":"doc",
        "split":"GroupKFold_5_study_disjoint",
        "folds":splitsets,
        "results":results,
        "published_rule_nn_mae_9_15_percent_not_directly_comparable":True,
        "source_authors_rule_nn_reproduced":False,
        "individual_causal_effect_estimated":False,
        "measured_manager_product_effect":False,
    }


if __name__=="__main__":
    print(json.dumps(run(),indent=2,ensure_ascii=False,allow_nan=False))
