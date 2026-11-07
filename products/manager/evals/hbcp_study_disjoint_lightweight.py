"""P09-5 external study generalization: HBCP published smoking cessation RCT arm data.

Only 971 aggregate trial-arm outcomes across 405 studies; 93 numeric-coercible
feature columns from the CC0 source, not the author's final 82-feature RuleNN.
Five-fold study-disjoint evaluation for fixed train-mean and train-only ridge.
No individual-person data, real treatment-effect estimation, or causal claim.

Reuses the source SHA and feature exclusions from the existing sibling
hbcp_smoking_outcome_baselines.py; no new dependency beyond installed NumPy.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

SOURCE_URL="https://raw.githubusercontent.com/HumanBehaviourChangeProject/semantic-prediction/main/data/hbcp_gen.csv"
SOURCE_SHA256="eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b"
TARGET="('Outcome', 'Outcome')"
EXCLUDE={"","doc_id","arm_id","doc","arm",TARGET}


def load_pinned_source() -> list[dict]:
    with urllib.request.urlopen(
        urllib.request.Request(SOURCE_URL,headers={"User-Agent":"Manager/HBCP-StudyEval-2026-11-07"}),
        timeout=30,
    ) as r:
        raw=r.read(800000)
    sha=hashlib.sha256(raw).hexdigest()
    if sha!=SOURCE_SHA256:
        raise ValueError("source bytes differ; no score can be asserted")
    rows=list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if len(rows)!=971 or len({r["doc"] for r in rows})!=405:
        raise ValueError("unexpected public study/arm counts")
    return rows


def numeric_feature_matrix(rows: list[dict]) -> tuple[np.ndarray,list[str]]:
    if not rows:raise ValueError("empty HBCP source")
    names=[k for k in rows[0] if k not in EXCLUDE]
    def parse(v):
        try:
            f=float(v)
            return f if math.isfinite(f) else math.nan
        except (ValueError, TypeError):
            return math.nan
    values=np.asarray([[parse(r.get(name)) for name in names] for r in rows],dtype=np.float64)
    usable=np.isfinite(values).any(axis=0)
    if not usable.any():raise ValueError("no numeric features")
    return values[:,usable], [n for n,keep in zip(names,usable) if keep]


def study_folds(groups: list[str], n_splits:int=5) -> list[tuple[np.ndarray,np.ndarray]]:
    if n_splits<2 or len(set(groups))<n_splits or any(not v for v in groups):
        raise ValueError("invalid group split")
    group_sizes=Counter(groups)
    studies=sorted(group_sizes,key=lambda s:(-group_sizes[s],s))
    held=[set() for _ in range(n_splits)]
    sizes=[0]*n_splits
    for s in studies:
        k=min(range(n_splits),key=lambda i:(sizes[i],i))
        held[k].add(s)
        sizes[k]+=group_sizes[s]
    folds=[]
    for x in held:
        te=np.asarray([i for i,s in enumerate(groups) if s in x],dtype=int)
        tr=np.asarray([i for i,s in enumerate(groups) if s not in x],dtype=int)
        if not len(te) or not len(tr):raise AssertionError("empty fold")
        if {groups[i] for i in te}&{groups[i] for i in tr}:
            raise AssertionError("study leakage")
        folds.append((tr,te))
    assert sorted(i for _,te in folds for i in te)==list(range(len(groups)))
    return folds


def ridge_on_train(X:np.ndarray,y:np.ndarray,train:np.ndarray,test:np.ndarray,alpha:float=30.) -> np.ndarray:
    if alpha<=0:raise ValueError("ridge must regularize")
    if not len(train) or not len(test):raise ValueError("empty split")
    a,b=X[train],X[test]
    med=np.zeros(X.shape[1],dtype=float)
    for j in range(X.shape[1]):
        good=a[:,j][np.isfinite(a[:,j])]
        med[j]=float(np.median(good)) if len(good) else 0.
    a=np.where(np.isfinite(a),a,med)
    b=np.where(np.isfinite(b),b,med)
    center=a.mean(0)
    scale=a.std(0)
    scale[scale<1e-12]=1.
    a=(a-center)/scale
    b=(b-center)/scale
    mu=float(np.mean(y[train]))
    weight=np.linalg.solve(a.T@a+np.eye(a.shape[1])*alpha,a.T@(y[train]-mu))
    return np.clip(mu+b@weight,0.,100.)


def evaluate_predictions(y:np.ndarray,pred:np.ndarray)->dict:
    if y.shape!=pred.shape or not np.isfinite(y).all() or not np.isfinite(pred).all():
        raise ValueError("invalid outcome predictions")
    e=y-pred
    return {"n":len(y),"mae":float(np.abs(e).mean()),"rmse":float(np.sqrt((e*e).mean()))}


def run(reps:int=1000)->dict:
    rows=load_pinned_source()
    groups=[x["doc"] for x in rows]
    y=np.asarray([float(x[TARGET]) for x in rows])
    if not (np.isfinite(y).all() and ((0<=y)&(y<=100)).all()):
        raise ValueError("bad original percentage outcome")
    X,names=numeric_feature_matrix(rows)
    folds=study_folds(groups)
    simple=np.full(len(y),np.nan)
    ridge=np.full(len(y),np.nan)
    fold_counts=[]
    for i,(tr,te) in enumerate(folds):
        simple[te]=float(y[tr].mean())
        ridge[te]=ridge_on_train(X,y,tr,te,alpha=30.)
        fold_counts.append({"fold":i,"n_train_studies":len({groups[k] for k in tr}),
                            "n_test_studies":len({groups[k] for k in te}),
                            "n_test_arms":len(te)})
    baseline=evaluate_predictions(y,simple)
    model=evaluate_predictions(y,ridge)
    study_ids=sorted(set(groups))
    buckets=defaultdict(list)
    for i,s in enumerate(groups):buckets[s].append(i)
    rng=np.random.default_rng(20261107)
    deltas=[]
    for _ in range(reps):
        chosen=[k for s in rng.choice(study_ids,size=len(study_ids),replace=True) for k in buckets[s]]
        yt=y[chosen]
        deltas.append(float(np.mean(np.abs(yt-simple[chosen]))-
                            np.mean(np.abs(yt-ridge[chosen]))))
    return {
        "scope":"real HBCP RCT-arm smoking cessation RATE prediction; NOT a causal effect nor a model of individuals",
        "source":SOURCE_URL,"sha256":SOURCE_SHA256,
        "license":"CC0 public dataset; attribution and file-level rights recorded by original authors",
        "n_studies":len(study_ids),"n_trial_arms":len(rows),
        "n_numeric_features":X.shape[1],"n_paper_features":82,
        "study_holdout":"5-fold non-overlapping study groups, fixed deterministic greedy balance; training-only median impute/scale",
        "folds":fold_counts,
        "train_mean":baseline,
        "ridge_alpha30":model,
        "mae_improvement":baseline["mae"]-model["mae"],
        "study_cluster_bootstrap_95ci_mae_improvement":list(map(float,np.quantile(deltas,[.025,.975]))),
        "bootstrap_reps":reps,
        "new_llm_or_bfm_executed":False,"individual_human_welfare_improved":False,
        "reference":"https://pmc.ncbi.nlm.nih.gov/articles/PMC12603517/",
        "caveat":"Not the author's RuleNN or identical original data preparation, and 93 numeric columns do not equal the published 82 ontology features."
    }


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--bootstrap-reps",type=int,default=1000)
    a=p.parse_args()
    output=run(reps=a.bootstrap_reps)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:output[k] for k in ("n_studies","n_trial_arms","n_numeric_features","train_mean","ridge_alpha30","mae_improvement","study_cluster_bootstrap_95ci_mae_improvement")},ensure_ascii=False,indent=2))
