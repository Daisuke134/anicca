"""P07-2: REAL experience sampling, predicting a person's NEXT state.

Hoebeke (2022) original observed brooding/negative thinking, 40 humans,
4 prompts/day x 14 days, official harmonized CC BY 4.0 openESM/Zenodo TSV.
Dejonckheere (2019) observed affect/stress only, 100 people, 7/day x14d.
IMPORTANT: Dejonckheere released TSV has no rumination measure. Do not
treat negative affect as diagnosed rumination or thought probe MW.

Same-day adjacent prompts only, features at t, outcome at t+1.
Cross-person train/val/test with GroupShuffleSplit. No invented subjects.
Strong last-state persistence baseline vs pooled mean/Ridge/RandomForest/
Histogram Gradient Boosting; model selection on validation only. Keep
observed source data private in /private/tmp and publish aggregates only.
No effect of interventions or benefit to users is measured.

Uses existing scikit-learn, pandas, NumPy, requests rather than new ML code.
"""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone
from time import monotonic
import json

import numpy as np
import pandas as pd
import requests
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[6]
EVIDENCE=ROOT/"docs/research/manager/masterclass/2026-11-04-p04-causal/evidence"
RAW=Path("/private/tmp/manager-p07-2-real-20261105")
SEED=202611052
N_BOOT=500
SOURCES={
    "hoebeke_2022":{
        "url":"https://zenodo.org/api/records/22952951/files/0013_hoebeke_ts.tsv/content",
        "sha256":"85593640b46cc3ab80115ad7e0b1ae5c5ed2ad29ca1ec56d338c45654a17cb58",
        "doi":"10.5281/zenodo.17347619","license":"CC BY 4.0",
        "n_people_expected":40,
        "target":"brooding","inputs":["brooding","perseverance","negativity","self_criticism","replaying","beep"],
        "interpretation":"self-reported brooding next within-day beep, not clinical diagnosis",
        "source":"openESM Hoebeke (2022), https://openesmdata.org/datasets/0013_hoebeke/",
        "has_direct_rumination_item":True,
    },
    "dejonckheere_2019":{
        "url":"https://zenodo.org/api/records/17347570/files/0012_dejonckheere_ts.tsv/content",
        "sha256":"2cabd3f416f2dd5707b1623de5ac8cdba5de2834616e2a8df2a52e8c5473bf53",
        "doi":"10.5281/zenodo.17347569","license":"CC BY 4.0",
        "n_people_expected":100,
        "target":"stressed","inputs":["stressed","happy","relaxed","sad","angry","beep"],
        "interpretation":"next within-day stress self-report; dataset does NOT measure rumination directly",
        "source":"openESM Dejonckheere (2019), https://openesmdata.org/datasets/0012_dejonckheere/",
        "has_direct_rumination_item":False,
    },
}

def digest(raw:bytes)->str:
    return sha256(raw).hexdigest()

def source_frame(name:str)->tuple[pd.DataFrame,dict]:
    spec=SOURCES[name]
    RAW.mkdir(parents=True,exist_ok=True)
    path=RAW/(name+".tsv")
    if path.exists():
        data=path.read_bytes()
    else:
        response=requests.get(spec["url"],timeout=35)
        response.raise_for_status()
        data=response.content
        path.write_bytes(data)
    if digest(data)!=spec["sha256"]:
        raise ValueError("Official ESM source changed; review/pin new version")
    df=pd.read_csv(path,sep="\t")
    required=["id","day","beep","counter",*spec["inputs"]]
    if not set(required).issubset(df.columns):
        raise ValueError("Required official columns missing")
    if int(df["id"].nunique())!=spec["n_people_expected"]:
        raise ValueError("Official participant count changed")
    return df,{k:v for k,v in spec.items() if k not in ("inputs",)} | {
        "file_sha256":digest(data),"original_rows":int(len(df)),
        "actual_people":int(df["id"].nunique()),"original_missing_target_rows":int(df[spec["target"]].isna().sum()),
    }

def sequences(df:pd.DataFrame,name:str)->tuple[pd.DataFrame,dict]:
    spec=SOURCES[name]
    d=df.copy()
    d=d.sort_values(["id","day","beep"],kind="stable")
    if d.duplicated(["id","day","beep"]).any():
        raise ValueError("nonunique person/day/beep")
    d["next_target"]=d.groupby(["id","day"],sort=False)[spec["target"]].shift(-1)
    d["next_beep"]=d.groupby(["id","day"],sort=False)["beep"].shift(-1)
    admissible=(d["next_beep"]==d["beep"]+1)
    if name=="hoebeke_2022":
        d["time"]=pd.to_datetime(d["created"],utc=True,errors="coerce")
        d["next_time"]=d.groupby(["id","day"],sort=False)["time"].shift(-1)
        d["gap_hours"]=(d["next_time"]-d["time"]).dt.total_seconds()/3600
        admissible &= d["gap_hours"].between(0.2,8.0)
    required=[*spec["inputs"],"next_target"]
    for col in required:
        d[col]=pd.to_numeric(d[col],errors="coerce")
    d=d.loc[admissible].dropna(subset=required)
    d=d[(d[spec["target"]].between(0,100))&(d["next_target"].between(0,100))].copy()
    if len(d)<500:raise ValueError("not enough eligible real ESM transitions")
    assert d["id"].nunique()==spec["n_people_expected"],"a participant vanished"
    return d,{
        "eligible_actual_consecutive_within_day_transitions":int(len(d)),
        "participants_with_eligible_transitions":int(d["id"].nunique()),
        "observed_target_range":[float(d.next_target.min()),float(d.next_target.max())],
        "current_target_mean":float(d[spec["target"]].mean()),
        "next_target_mean":float(d["next_target"].mean()),
        "missing_observations_not_imputed":True,
        "adjacent_prompt_only":True,
        "same_day_only":True,
    }

def split_people(df:pd.DataFrame)->dict[str,np.ndarray]:
    groups=df["id"].astype(str).to_numpy()
    whole=np.arange(len(df))
    cv=GroupShuffleSplit(n_splits=1,test_size=.20,random_state=SEED)
    pre,test=next(cv.split(whole,groups=groups))
    cv2=GroupShuffleSplit(n_splits=1,test_size=.25,random_state=SEED+1)
    tri,vali=next(cv2.split(pre,groups=groups[pre]))
    ix={"train":pre[tri],"validation":pre[vali],"test":test}
    names=[set(groups[index]) for index in ix.values()]
    if names[0]&names[1] or names[0]&names[2] or names[1]&names[2]:
        raise ValueError("participant overlap across train/val/test")
    return ix

def models()->dict:
    return {
        "ridge_a1":Pipeline([("scale",StandardScaler()),("model",Ridge(alpha=1.0))]),
        "ridge_a100":Pipeline([("scale",StandardScaler()),("model",Ridge(alpha=100.0))]),
        "random_forest":RandomForestRegressor(n_estimators=150,max_depth=5,
                                              min_samples_leaf=5,n_jobs=4,
                                              random_state=SEED),
        "hist_gradient_boosting":HistGradientBoostingRegressor(
            max_iter=125,max_leaf_nodes=14,max_depth=4,l2_regularization=5,
            learning_rate=.06,random_state=SEED),
    }

def metrics(y:np.ndarray,p:np.ndarray)->dict:
    y=np.asarray(y,dtype=float)
    pred=np.clip(np.asarray(p,dtype=float),0,100)
    if len(y)!=len(pred) or not np.all(np.isfinite(pred)):
        raise ValueError("invalid real outcome prediction")
    return {
        "n":int(len(y)),
        "mae":float(mean_absolute_error(y,pred)),
        "rmse":float(np.sqrt(mean_squared_error(y,pred))),
        "r2":float(r2_score(y,pred)),
        "actual_sd":float(y.std(ddof=1)),
        "range_0_100":True,
    }

def cluster_ci(y:np.ndarray, selected:np.ndarray, baseline:np.ndarray,
               participants:np.ndarray,seed:int)->dict:
    """Absolute RMSE gain baseline-selected on same heldout persons."""
    rng=np.random.default_rng(seed)
    people=np.unique(participants.astype(str))
    parts={s:np.where(participants.astype(str)==s)[0] for s in people}
    values=[]
    for _ in range(N_BOOT):
        selected_people=rng.choice(people,size=len(people),replace=True)
        idx=np.concatenate([parts[p] for p in selected_people])
        e0=np.sqrt(np.mean((y[idx]-baseline[idx])**2))
        e1=np.sqrt(np.mean((y[idx]-selected[idx])**2))
        values.append(e0-e1)
    raw=np.asarray(values)
    return {
        "rmse_improvement_vs_persistence":float(
            np.sqrt(np.mean((y-baseline)**2))-np.sqrt(np.mean((y-selected)**2))),
        "cluster_bootstrap_95ci":[float(np.quantile(raw,.025)),float(np.quantile(raw,.975))],
        "n_independent_participants":len(people),
        "n_replicates":N_BOOT,
        "positive_values_support_added_model_utility":True,
        "not_a_causal_effect":True,
    }

def run()->dict:
    tic=monotonic()
    out={
        "research":"P07-2 real ESM state prediction (NOT intervention impact)",
        "date":datetime.now(timezone.utc).isoformat(),
        "all_records_real_observed_human_responses":True,
        "model_methods":"scikit-learn GroupShuffleSplit, Ridge, RF, HistGradientBoost; strong persistence",
        "n_synthetic_humans":0,
        "datasets":{},
        "external_clinical_trial_run":False,
        "mental_health_treatment_effect_measured":False,
        "mind_wandering_probe_or_EEG_used":False,
    }
    for name,spec in SOURCES.items():
        original,source=source_frame(name)
        pairs,qc=sequences(original,name)
        ids=split_people(pairs)
        feat=spec["inputs"]
        x=pairs[feat].to_numpy(dtype=float)
        y=pairs["next_target"].to_numpy(dtype=float)
        previous=pairs[spec["target"]].to_numpy(dtype=float)
        group=pairs["id"].astype(str).to_numpy()
        models_fit=models()
        train,val,test=(ids[z] for z in ("train","validation","test"))
        model_predictions={}
        train_mean=float(y[train].mean())
        baselines={
            "train_global_mean":np.full(len(y),train_mean),
            "persistence_last_state":previous,
        }
        for tag,m in models_fit.items():
            m.fit(x[train],y[train])
            model_predictions[tag]=m.predict(x)
        all_p={**baselines,**model_predictions}
        val_scores={k:metrics(y[val],v[val]) for k,v in all_p.items()}
        # Always take best score from VALIDATION before touching any TEST result.
        chosen=min(val_scores,key=lambda k:(val_scores[k]["rmse"],k))
        test_scores={k:metrics(y[test],v[test]) for k,v in all_p.items()}
        ci=cluster_ci(y[test],all_p[chosen][test],baselines["persistence_last_state"][test],
                      group[test],seed=SEED+len(name))
        report={
            "source":source,"data_quality":qc,
            "split_type":"participant-disjoint train/validation/test; no same-day future row in X",
            "split_counts":{k:{"observed_transitions":int(len(index)),
                               "n_people":int(len(set(group[index])))}
                            for k,index in ids.items()},
            "split_hash_sha256":{k:sha256(np.sort(index).tobytes()).hexdigest()
                                  for k,index in ids.items()},
            "inputs_available_at_time_t":feat,
            "next_target_at_t_plus_one":spec["target"],
            "model_chosen_by_validation_rmse_only":chosen,
            "validation_scores":val_scores,
            "heldout_test_scores":test_scores,
            "test_improvement_vs_last_value":ci,
            "baseline_last_value_of_same_person_usable_only_after_earlier_probe":True,
            "no_heldout_model_selection":True,
            "no_actual_intervention_happened":True,
            "does_not_prove_causal_benefit_or_diagnosis":True,
        }
        out["datasets"][name]=report
        print("REAL_ESM",name,"rows",len(original),"transitions",len(pairs),
              "heldout_people",report["split_counts"]["test"]["n_people"],
              "selected",chosen,"test_rmse",test_scores[chosen]["rmse"],
              "persistence_rmse",test_scores["persistence_last_state"]["rmse"],
              "ci",ci["cluster_bootstrap_95ci"],flush=True)
    out["runtime_seconds"]=round(monotonic()-tic,2)
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (EVIDENCE/"P07-2_REAL_ESM_HOEBEKE_AFFECT_RESULTS_20261105.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return out

if __name__=="__main__":
    run()
