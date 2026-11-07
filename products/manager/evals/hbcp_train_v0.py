"""G2 trained Manager model v0: reproducible HBCP RCT-arm outcome Ridge head.

This is a *real small supervised model* trained on 971 published human study
arm aggregates, not a 4B BFM, not user personalization, and not an estimated
individual causal treatment effect. It cannot authorize a real intervention.
Only the training set fits imputation, scale and parameters. A disjoint
calibration group estimates exploratory interval width; a sealed group
assesses holdout baseline. JSON contains weights, NOT source rows.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from hbcp_study_disjoint_lightweight import (
    SOURCE_SHA256, SOURCE_URL, TARGET, evaluate_predictions,
    load_pinned_source, numeric_feature_matrix,
)

MODEL_SCHEMA="manager.hbcp.ridge_head.v0"
SEED=20261107
ALPHA=30.0


def frozen_study_split(groups: list[str], seed: int = SEED) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    if type(seed) is not int or not isinstance(groups,list) or len(groups)<12:
        raise ValueError("study split requires sufficiently many rows")
    if any(not isinstance(g,str) or not g for g in groups):
        raise ValueError("invalid study identifier")
    ordered=sorted(set(groups), key=lambda g:(hashlib.sha256(f"{seed}|{g}".encode()).hexdigest(),g))
    if len(ordered)<10:
        raise ValueError("need >=10 independent studies")
    ntrain=int(.7*len(ordered))
    ncal=int(.1*len(ordered))
    train=set(ordered[:ntrain])
    calibration=set(ordered[ntrain:ntrain+ncal])
    test=set(ordered[ntrain+ncal:])
    if not train or not calibration or not test or train&calibration or train&test or calibration&test:
        raise ValueError("overlapping or empty group splits")
    a=np.asarray([i for i,g in enumerate(groups) if g in train],dtype=np.int64)
    b=np.asarray([i for i,g in enumerate(groups) if g in calibration],dtype=np.int64)
    c=np.asarray([i for i,g in enumerate(groups) if g in test],dtype=np.int64)
    return a,b,c


def _split_guard(n_rows:int,tr:np.ndarray,cal:np.ndarray,te:np.ndarray)->None:
    pieces=[np.asarray(x) for x in (tr,cal,te)]
    if (any(x.ndim!=1 or len(x)==0 or x.dtype.kind not in "iu" for x in pieces)
            or len(set(int(i) for x in pieces for i in x))!=n_rows
            or any(int(i)<0 or int(i)>=n_rows for x in pieces for i in x)
            or sum(map(len,pieces))!=n_rows):
        raise ValueError("train/calibration/test must partition all rows disjointly")


def predict_artifact(model: dict, X: np.ndarray, columns: list[str]) -> np.ndarray:
    if model.get("schema")!=MODEL_SCHEMA or model.get("domain")!="HBCP_PUBLISHED_SMOKING_CESSATION_RCT_ARMS":
        raise ValueError("unrecognized model artifact")
    prep=model["preprocessing"]
    try:
        canonical=json.dumps({"head":model["head"],"preprocessing":prep},
            sort_keys=True,separators=(",",":"),allow_nan=False).encode()
        actual_sha=hashlib.sha256(canonical).hexdigest()
    except (ValueError,TypeError,KeyError):
        raise ValueError("invalid saved model encoding") from None
    if model.get("trained_head_sha256")!=actual_sha:
        raise ValueError("saved model head digest missing or tampered")
    if columns!=prep.get("columns"):
        raise ValueError("model feature columns/order mismatch")
    inp=np.asarray(X,dtype=float)
    if inp.ndim!=2 or inp.shape[1]!=len(columns) or np.isinf(inp).any():
        raise ValueError("invalid matrix dimension or infinite feature")
    if not len(inp):
        raise ValueError("empty prediction features")
    med=np.asarray(prep["medians"],dtype=float)
    center=np.asarray(prep["centers"],dtype=float)
    scales=np.asarray(prep["scales"],dtype=float)
    w=np.asarray(model["head"]["weights"],dtype=float)
    bias=model["head"]["intercept"]
    if any(v.shape!=(len(columns),) for v in (med,center,scales,w)) or (scales<=0).any():
        raise ValueError("corrupted learned transform")
    if not all(np.isfinite(x).all() for x in (med,center,scales,w)) or not math.isfinite(float(bias)):
        raise ValueError("nonfinite model weights")
    imputed=np.where(np.isnan(inp),med,inp)
    pred=float(bias)+(imputed-center)/scales@w
    return np.clip(pred,0,100)


def fit_model(X:np.ndarray,y:np.ndarray,columns:list[str],
              tr:np.ndarray,cal:np.ndarray,te:np.ndarray,
              alpha:float=ALPHA)->dict:
    """Fit only on train; return model, calibration and test receipt."""
    data=np.asarray(X,dtype=float)
    outcomes=np.asarray(y,dtype=float)
    if (data.ndim!=2 or outcomes.ndim!=1 or data.shape[0]!=len(outcomes)
            or data.shape[1]<1 or data.shape[0]<12
            or np.isinf(data).any() or not np.isfinite(outcomes).all()
            or (outcomes<0).any() or (outcomes>100).any()):
        raise ValueError("invalid arm-level numeric input")
    if (not isinstance(columns,list) or len(columns)!=data.shape[1]
            or any(not isinstance(s,str) or not s for s in columns)
            or len(set(columns))!=len(columns)
            or any(col == TARGET or col in ("doc","doc_id","user.index","arm","arm_id") for col in columns)):
        raise ValueError("outcome/participant identifiers cannot be model features")
    if not math.isfinite(alpha) or alpha<=0:
        raise ValueError("positive Ridge regularization required")
    _split_guard(len(outcomes),tr,cal,te)
    source=data[tr]
    med=np.zeros(data.shape[1],dtype=float)
    for j in range(data.shape[1]):
        nonmissing=source[:,j][np.isfinite(source[:,j])]
        med[j]=np.median(nonmissing) if len(nonmissing) else 0.
    xtr=np.where(np.isnan(source),med,source)
    centers=np.mean(xtr,axis=0)
    scales=np.std(xtr,axis=0)
    scales=np.where(scales<1e-12,1.,scales)
    Z=(xtr-centers)/scales
    intercept=float(np.mean(outcomes[tr]))
    coef=np.linalg.solve(Z.T@Z+alpha*np.eye(data.shape[1]),Z.T@(outcomes[tr]-intercept))
    artifact={
        "schema":MODEL_SCHEMA,
        "domain":"HBCP_PUBLISHED_SMOKING_CESSATION_RCT_ARMS",
        "task":"study_arm_smoking_cessation_rate",
        "unit":"percentage_points_0_to_100",
        "trained_universal_bfm":False,
        "individual_user_predictions_authorized":False,
        "real_world_interventions_authorized":False,
        "head":{"kind":"ridge_alpha30","alpha":float(alpha),"intercept":intercept,
                "weights":coef.tolist()},
        "preprocessing":{"columns":list(columns),"medians":med.tolist(),
                         "centers":centers.tolist(),"scales":scales.tolist()},
        "n_train_arms":len(tr),"n_calibration_arms":len(cal),"n_test_arms":len(te),
        "n_features":len(columns),
    }
    head_bytes=json.dumps({"head":artifact["head"],"preprocessing":artifact["preprocessing"]},
                          sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    artifact["trained_head_sha256"]=hashlib.sha256(head_bytes).hexdigest()
    pcal=predict_artifact(artifact,data[cal],columns)
    ptest=predict_artifact(artifact,data[te],columns)
    abs_cal=np.abs(outcomes[cal]-pcal)
    halfwidth=float(np.quantile(abs_cal,.9,method="higher"))
    artifact["calibration_halfwidth"]=halfwidth
    artifact["test_interval_coverage_empirical"]=float(np.mean(np.abs(outcomes[te]-ptest)<=halfwidth))
    artifact["test_metrics"]={
        "train_mean":evaluate_predictions(outcomes[te],np.full(len(te),intercept)),
        "ridge":evaluate_predictions(outcomes[te],ptest),
    }
    return artifact


def train_artifact(rows:list[dict]|None=None, bootstrap_reps:int=500)->dict:
    if bootstrap_reps<100:raise ValueError("need >=100 study bootstrap replicates")
    original=load_pinned_source() if rows is None else rows
    if len(original)!=971 or len({r.get("doc") for r in original})!=405:
        raise ValueError("not canonical 971-arm 405-study HBCP source")
    X,columns=numeric_feature_matrix(original)
    y=np.asarray([float(r[TARGET]) for r in original],dtype=float)
    groups=[str(r["doc"]) for r in original]
    tr,cal,te=frozen_study_split(groups)
    model=fit_model(X,y,columns,tr,cal,te)
    study_sets=[{groups[i] for i in ids} for ids in (tr,cal,te)]
    model["source"]={
        "url":SOURCE_URL,"sha256":SOURCE_SHA256,"license_status":"research_source_public_use_requirements_checked_per_provider",
        "kind":"published_aggregate_arm_outcomes",
        "n_arms":971,"n_studies":405,
    }
    model["split"]={
        "method":"sha256 stable per study, seed 20261107, about 70/10/20 group share",
        "train_studies":len(study_sets[0]),
        "calibration_studies":len(study_sets[1]),
        "test_studies":len(study_sets[2]),
        "disjoint":not (study_sets[0]&study_sets[1] or study_sets[0]&study_sets[2] or study_sets[1]&study_sets[2]),
        "study_partition_digest":hashlib.sha256(json.dumps(
            [sorted(s) for s in study_sets],separators=(",",":")).encode()).hexdigest(),
    }
    model["calibration_disclaimer"]="Raw 90pct empirical absolute residual quantile; no conditional/exchangeable guarantee under study shifts"
    test_y=y[te]
    b=np.full(len(te),model["head"]["intercept"],dtype=float)
    c=predict_artifact(model,X[te],columns)
    bins={}
    for pos,i in enumerate(te):
        bins.setdefault(groups[i],[]).append(pos)
    sid=sorted(bins)
    rng=np.random.default_rng(SEED)
    gains=[]
    for _ in range(bootstrap_reps):
        sampled=np.concatenate([np.asarray(bins[s]) for s in rng.choice(sid,size=len(sid),replace=True)])
        gains.append(float(np.mean(np.abs(test_y[sampled]-b[sampled]))-
                           np.mean(np.abs(test_y[sampled]-c[sampled]))))
    ci=list(map(float,np.quantile(gains,[.025,.975])))
    model["test_study_bootstrap_95ci_mae_gain"]=ci
    model["mae_gain_vs_train_mean"]=model["test_metrics"]["train_mean"]["mae"]-model["test_metrics"]["ridge"]["mae"]
    model["model_promotion_approved"]=False
    model["promotion_reason"]="Research-only arm head; no prospective user benefit, no causal effect, no individual permission"
    model["bootstrap_reps"]=bootstrap_reps
    return model


def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--bootstrap-reps",type=int,default=500)
    args=p.parse_args()
    model=train_artifact(bootstrap_reps=args.bootstrap_reps)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(model,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+"\n")
    print(json.dumps({
        "status":"REAL_PUBLISHED_HUMAN_AGGREGATE_RIDGE_HEAD_TRAINED",
        "source":model["source"]["sha256"],
        "split":{k:v for k,v in model["split"].items() if k.endswith("studies") or k=="disjoint"},
        "test":model["test_metrics"],
        "mae_gain_vs_mean":model["mae_gain_vs_train_mean"],
        "boot_ci":model["test_study_bootstrap_95ci_mae_gain"],
        "head_sha256":model["trained_head_sha256"],
        "promotion":model["model_promotion_approved"]},ensure_ascii=False))


if __name__=="__main__":
    main()
