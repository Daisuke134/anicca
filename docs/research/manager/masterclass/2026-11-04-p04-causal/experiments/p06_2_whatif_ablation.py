"""P06-2: real Python execution on SYNTHETIC randomized data only.

Ablation: a learned 2x2 counterfactual response model (What-if) versus the
best of predeclared no-simulation policies selected on separate validation.
Same features, action set, utility, independent 40k-subject policy RCT.

PREANALYSIS + frozen policies are written BEFORE any policy-trial outcomes.
No real humans, notifications, sales, token charges, research preregistration,
company deployments, or empirical causal effects are involved.

Python 3.11+, NumPy; no special simulator or model dependency.
"""
from __future__ import annotations

from hashlib import sha256
from math import erfc, sqrt
from pathlib import Path
import csv
import json

import numpy as np

SEED_TRAIN = 20261162
SEED_VALIDATION = 20261163
SEED_TRIAL = 20261164
N_TRAIN = 24000
N_VALIDATION = 16000
N_TRIAL = 40000
COST = 0.02

def config() -> dict:
    return {
        "study": "P06-2 SYNTHETIC what-if ablation, NOT a human study",
        "seed_train": SEED_TRAIN, "seed_validation": SEED_VALIDATION,
        "seed_trial": SEED_TRIAL,
        "n_train": N_TRAIN, "n_validation": N_VALIDATION, "n_trial": N_TRIAL,
        "features": ["motivation_pre", "fatigue_pre"],
        "action_set": [0,1],
        "outcome": "net utility = completed task - 0.02*notification",
        "utility_notification_cost": COST,
        "simulator": "empirical p(Y=1 | randomized action, motivation, fatigue)",
        "baseline_candidates": [
            "NO_ACTION","ALL_ACTION","PRESPECIFIED_HEURISTIC","POOLED_GLOBAL_EFFECT"
        ],
        "comparator_selection": "maximum validation IPW utility among four prespecified policies; same training/validation data available",
        "policy_freeze": "both policies recorded with hashes before trial outcomes generated",
        "trial": "independent randomized 1:1 assignment to FROZEN what-if policy vs FROZEN strongest validated baseline",
        "primary_estimand": "E[net utility|What-if arm] - E[net utility|Comparator arm]",
        "primary_analysis": "Welch standard error, two-sided Gaussian p, Wald 95% CI, fixed n; no peeking",
        "secondary": ["task_completion_rate","notification_rate"],
        "positive_effect_needed": "positive preregistered test CI excluding zero (only within toy world)",
        "causal_effect_only_in_synthetic_world": True,
        "external_registry": False,
        "actual_users": 0,
        "actual_business_profit": False,
    }

def fingerprint(x: object) -> str:
    return sha256(json.dumps(x,ensure_ascii=False,sort_keys=True,
                             separators=(",",":"),allow_nan=False).encode()).hexdigest()

def generate(n: int, seed: int, randomized: bool=True) -> dict[str,np.ndarray]:
    """Outcome process is separate from model fitting, with known toy DGP."""
    rng=np.random.default_rng(seed)
    m=rng.integers(0,2,size=n)
    f=rng.integers(0,2,size=n)
    p0=0.22+0.18*m-0.05*f
    tau=0.16-0.20*m-0.06*f
    a=rng.integers(0,2,size=n) if randomized else np.zeros(n,dtype=int)
    y=(rng.random(n)<p0+a*tau).astype(int)
    return {"motivation":m,"fatigue":f,"action":a,"observed":y,
            "p0_hidden":p0,"tau_hidden":tau}

def map_policy(m: np.ndarray, f: np.ndarray, table: dict[str,int]) -> np.ndarray:
    keys=(2*m+f).astype(int)
    return np.asarray([table[str(k)] for k in keys],dtype=int)

def fit_whatif(train: dict) -> tuple[dict[str,int],dict]:
    """Train-time outcomes only; inaccessible hidden true effects."""
    m,f,a,y=(train[k] for k in ("motivation","fatigue","action","observed"))
    tab={}
    rule={}
    for mv in (0,1):
        for fv in (0,1):
            key=str(2*mv+fv)
            group=(m==mv)&(f==fv)
            for action in (0,1):
                if int(np.sum(group&(a==action)))<100:
                    raise ValueError("insufficient overlap for toy fitted simulator")
            p0=float(np.mean(y[group&(a==0)]))
            p1=float(np.mean(y[group&(a==1)]))
            improvement=p1-p0-COST
            rule[key]=int(improvement>0)
            tab[key]={"p_observed_given_no_action":p0,
                      "p_observed_given_action":p1,
                      "net_whatif_gain":improvement,
                      "predicted_action":rule[key]}
    return rule,tab

def baseline_policy_tables(train:dict) -> dict[str,dict[str,int]]:
    pooled=float(np.mean(train["observed"][train["action"]==1])-
                 np.mean(train["observed"][train["action"]==0]))
    return {
        "NO_ACTION":{str(i):0 for i in range(4)},
        "ALL_ACTION":{str(i):1 for i in range(4)},
        "PRESPECIFIED_HEURISTIC": {
            str(2*m+f):int(m==0 and f==0)
            for m in (0,1) for f in (0,1)},
        "POOLED_GLOBAL_EFFECT":{
            str(i):int(pooled>COST) for i in range(4)},
    }

def ipw_value(data:dict,table:dict[str,int]) -> dict:
    chosen=map_policy(data["motivation"],data["fatigue"],table)
    observed_utility=data["observed"]-COST*data["action"]
    z=2*(data["action"]==chosen)*observed_utility
    return {"estimated_utility":float(np.mean(z)),
            "standard_error":float(np.std(z,ddof=1)/np.sqrt(len(z)))}

def choose_strong_baseline(train:dict, validation:dict):
    candidates=baseline_policy_tables(train)
    scores={k:ipw_value(validation,v) for k,v in candidates.items()}
    chosen=max(scores,key=lambda k:(scores[k]["estimated_utility"],k))
    return chosen,candidates[chosen],scores

def trial_for_policies(learned:dict,baseline:dict)->dict:
    """Only here are evaluation outcomes generated: policies already frozen."""
    rng=np.random.default_rng(SEED_TRIAL)
    n=N_TRIAL
    m=rng.integers(0,2,size=n)
    f=rng.integers(0,2,size=n)
    arm=rng.integers(0,2,size=n) # arm1=What-if, arm0=comparator
    a_manager=map_policy(m,f,learned)
    a_baseline=map_policy(m,f,baseline)
    a=np.where(arm==1,a_manager,a_baseline)
    # Known toy population, NEVER used for policy training or baseline selection.
    p0=0.22+0.18*m-0.05*f
    tau=0.16-0.20*m-0.06*f
    y=(rng.random(n)<p0+a*tau).astype(int)
    utility=y-COST*a
    return {"motivation":m,"fatigue":f,"arm":arm,"action":a,
            "outcome":y,"utility":utility,"true_tau":tau}

def arm_delta(values:np.ndarray, arm:np.ndarray) -> dict:
    a=values[arm==1]; b=values[arm==0]
    diff=float(np.mean(a)-np.mean(b))
    se=float(np.sqrt(np.var(a,ddof=1)/len(a)+np.var(b,ddof=1)/len(b)))
    return {"whatif_mean":float(np.mean(a)),"baseline_mean":float(np.mean(b)),
            "increment":diff,"se":se,"ci95":[diff-1.96*se,diff+1.96*se],
            "two_sided_p":float(erfc(abs(diff/se)/sqrt(2))),
            "n_whatif":len(a),"n_baseline":len(b)}

def theoretical_gain(whatif:dict,comparator:dict) -> float:
    """Display-only oracle after inference, not available to either policy."""
    vals=[]
    for m in (0,1):
        for f in (0,1):
            key=str(2*m+f)
            tau=.16-.20*m-.06*f
            vals.append((whatif[key]-comparator[key])*(tau-COST))
    return float(np.mean(vals))

def run(output:Path) -> dict:
    output.mkdir(parents=True,exist_ok=True)
    spec=config()
    (output/"P06-2_PREANALYSIS_SYNTHETIC.json").write_text(
        json.dumps(spec,ensure_ascii=False,indent=2)+"\n")
    # Both train and validation are independent, and do NOT use trial outcomes.
    train=generate(N_TRAIN,SEED_TRAIN)
    validation=generate(N_VALIDATION,SEED_VALIDATION)
    learned,forecast=fit_whatif(train)
    baseline_name,baseline,scores=choose_strong_baseline(train,validation)
    freeze={
        "plan_sha256":fingerprint(spec),
        "whatif_policy":learned,
        "baseline_policy":baseline,
        "baseline_name":baseline_name,
        "policy_hashes":{"whatif":fingerprint(learned),"baseline":fingerprint(baseline)},
        "test_outcomes_generated_before_freeze":False,
        "outcomes_source":"purely synthetic independent RNG",
    }
    (output/"P06-2_POLICY_FREEZE_SYNTHETIC.json").write_text(
        json.dumps(freeze,ensure_ascii=False,indent=2)+"\n")
    # NOW trial outcomes first generated; no retuning.
    trial=trial_for_policies(learned,baseline)
    primary=arm_delta(trial["utility"],trial["arm"])
    completion=arm_delta(trial["outcome"],trial["arm"])
    burden=arm_delta(trial["action"],trial["arm"])
    # Predeclared secondary outcomes, true value only AFTER trial.
    report={
        "study_id":"P06-2-SYNTHETIC-ABLATION-20261104",
        "scope":"NO actual humans; no published intervention or company profit",
        "n_train":N_TRAIN,"n_validation":N_VALIDATION,"n_trial":N_TRIAL,
        "whatif_model":"2x2 estimated intervention-specific outcome rates on randomized training set",
        "whatif_fitted":forecast,
        "baseline_heldout_ipw_selection_scores":scores,
        "baseline_selected_without_trial_peeking":baseline_name,
        "whatif_rule":learned,
        "comparator_rule":baseline,
        "train_validation_trial_seeds": [SEED_TRAIN,SEED_VALIDATION,SEED_TRIAL],
        "primary_net_utility_policy_rct":primary,
        "secondary_task_completion":completion,
        "secondary_notification_rate":burden,
        "synthetic_true_increment":theoretical_gain(learned,baseline),
        "true_effect_used_in_training":False,
        "real_user_or_business_effect":False,
        "frozen_plan_sha256":fingerprint(spec),
        "frozen_policy_sha256":freeze["policy_hashes"],
    }
    (output/"P06-2_SYNTHETIC_ABLATION_RESULTS.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    return report

if __name__=="__main__":
    out=Path(__file__).resolve().parents[1]/"evidence"
    r=run(out)
    print(json.dumps({k:r[k] for k in
        ("baseline_selected_without_trial_peeking","n_trial",
         "primary_net_utility_policy_rct","synthetic_true_increment")},
        ensure_ascii=False,indent=2))
