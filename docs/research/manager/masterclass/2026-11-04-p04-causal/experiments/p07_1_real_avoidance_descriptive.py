"""P07-1: REAL observed repeat-after-reward/error vs set-size.

Uses same original MIT source and author RT threshold, but NO simulation and
NO fitting human psychology from protected demographics. Outcome is a strictly
descriptive historical correlation, not causal evidence that memory or reward
made any particular person act. Never save per-subject records.
"""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import json
import numpy as np
from p07_1_real_reward_habit_eval import (
  EVIDENCE, read_actual_trials, SEED,EXPECTED_FILES,
)

STUDIES=tuple(EXPECTED_FILES)
BOOTSTRAPS=750


def counts_from_source(raw:np.ndarray)->dict[int,np.ndarray]:
    """Per participant [low-error, low-reward, high-error, high-reward] 2 columns.

    Last observation of the SAME stimulus, rather than previous global trial.
    Preceding reward is historical; current choice is the observed outcome.
    """
    require=(0,1,2,4,9,12,13)
    valid=np.isfinite(raw[:,require]).all(axis=1)
    valid &= np.isin(raw[:,9],[1,2,3]) & np.isin(raw[:,12],[0,1])
    valid &= (raw[:,13]>.15)&(raw[:,2]>=2)&(raw[:,2]<=6)
    valid &= (raw[:,4]>=1)&(raw[:,4]<=raw[:,2])
    selected=raw[valid]
    per_block={}
    for row in selected:
        key=(int(row[0]),int(row[1]))
        per_block.setdefault(key,[]).append(row)
    counts=defaultdict(lambda:np.zeros((4,2),dtype=np.int64))
    for (participant,block),trials in per_block.items():
        last={}
        for row in trials:
            ns=int(row[2])
            stimulus=int(row[4])
            action=int(row[9])
            reward=int(row[12])
            if stimulus in last and (ns<=3 or ns>=5):
                prev_action,prev_reward=last[stimulus]
                key=0 if ns<=3 else 2
                key+=prev_reward
                counts[participant][key,0]+=1
                counts[participant][key,1]+=int(prev_action==action)
            last[stimulus]=(action,reward)
    return dict(counts)


def rates(total:np.ndarray)->dict:
    labels=("low_load_after_no_reward","low_load_after_reward",
            "high_load_after_no_reward","high_load_after_reward")
    if total.shape!=(4,2):raise ValueError("invalid contingency summary")
    return {
        label:{
          "n_events":int(total[i,0]),
          "repeat_rate":float(total[i,1]/total[i,0])
                         if total[i,0]>0 else None,
          "n_repeats":int(total[i,1]),
        } for i,label in enumerate(labels)
    }


def cluster_bootstrap(counts:np.ndarray, seed:int) -> dict:
    rng=np.random.default_rng(seed)
    n=len(counts)
    if n<5:raise ValueError("need real independent participants")
    result=[]
    for j in range(BOOTSTRAPS):
        selected=counts[rng.integers(0,n,n)].sum(axis=0)
        if np.any(selected[:,0]==0):continue
        r=selected[:,1]/selected[:,0]
        result.append([
            r[2]-r[0],  # after incorrect: high vs low load
            r[1]-r[0],  # low: correct vs incorrect prior feedback
            r[3]-r[2],  # high: correct vs incorrect prior feedback
        ])
    vals=np.asarray(result)
    total=counts.sum(axis=0)
    m=total[:,1]/total[:,0]
    names=(
        "after_no_reward_high_minus_low_load",
        "low_load_rewarded_minus_unrewarded",
        "high_load_rewarded_minus_unrewarded",
    )
    points=(m[2]-m[0],m[1]-m[0],m[3]-m[2])
    return {
        name:{
          "absolute_repeat_rate_difference":float(value),
          "participant_cluster_bootstrap_ci95":[float(np.quantile(vals[:,i],.025)),
                                                float(np.quantile(vals[:,i],.975))],
          "bootstrap_repetitions":len(vals),
        } for i,(name,value) in enumerate(zip(names,points))
    }


def run()->dict:
    all_groups={}
    by_study={}
    for dataset in STUDIES:
        raw,meta=read_actual_trials(dataset)
        each=counts_from_source(raw)
        if not each:raise ValueError("no real participants available")
        array=np.stack(list(each.values()))
        summary=array.sum(axis=0)
        by_study[dataset]={
            "n_real_participants":len(each),
            "n_eligible_repeated_stimulus_events":int(summary[:,0].sum()),
            "rates":rates(summary),
        }
        for participant,counts in each.items():
            key=(dataset,participant)
            if key in all_groups:raise ValueError("group identity collision")
            all_groups[key]=counts
        print("DESCRIPTIVE_REPEAT",dataset,by_study[dataset],flush=True)
    pooled=np.stack(list(all_groups.values()))
    pooled_total=pooled.sum(axis=0)
    deterministic=np.stack([v for k,v in all_groups.items() if k[0]!="Expe14.mat"])
    probabilistic=np.stack([v for k,v in all_groups.items() if k[0]=="Expe14.mat"])
    if len(deterministic)!=445 or len(probabilistic)!=35:
        raise ValueError("unexpected cross-study people counts")
    out={
       "study":"P07-1 real reward/avoidance versus set size, descriptive not causal",
       "n_independent_study_datasets":len(STUDIES),
       "n_real_individuals_across_study_participant_ids":len(all_groups),
       "n_real_repeat_exposures":int(pooled_total[:,0].sum()),
       "per_study":by_study,
       "combined_rates":rates(pooled_total),
       "combined_participant_cluster_uncertainty":
            cluster_bootstrap(pooled,seed=SEED+1307),
       "deterministic_tasks_only":{
           "n_individuals":len(deterministic),
           "n_observed_repeat_events":int(deterministic[:,:,0].sum()),
           "rates":rates(deterministic.sum(axis=0)),
           "cluster_bootstrap":cluster_bootstrap(deterministic,SEED+1308),
       },
       "probabilistic_reward_task_only":{
           "n_individuals":len(probabilistic),
           "n_observed_repeat_events":int(probabilistic[:,:,0].sum()),
           "rates":rates(probabilistic.sum(axis=0)),
           "cluster_bootstrap":cluster_bootstrap(probabilistic,SEED+1309),
       },
       "Expe14_zero_reward_not_equivalent_to_wrong_action":True,
       "setsize_zero_reward_associations_not_mechanism_proof":True,
       "low_load_set_sizes":[2,3],
       "high_load_set_sizes":[5,6],
       "set_size_four_excluded_from_this_contrast":True,
       "last_reward_is_previous_same_stimulus_feedback":True,
       "outcome_is_current_choice_repeat":True,
       "no_future_reward_or_correct_answer_used_as_predictor":True,
       "source_experiment_results_observed_not_generated":True,
       "participant_level_rows_saved":False,
       "clinical_benefit_or_rumination_not_measured":True,
       "causal_explanation_of_reward_or_habit_not_identified":True,
    }
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    (EVIDENCE/"P07-1_REAL_AVOIDANCE_BY_LOAD_20261105.json").write_text(
        json.dumps(out,ensure_ascii=False,indent=2)+"\n")
    return out


if __name__=="__main__":
    r=run()
    print("AGGREGATE_REAL_REPEAT_COUNTS",r["combined_rates"])
    print("CLUSTER_BOOTSTRAP",r["combined_participant_cluster_uncertainty"])
    print("DETERMINISTIC_SPLIT",r["deterministic_tasks_only"])
    print("PROBABILISTIC_SPLIT",r["probabilistic_reward_task_only"])
