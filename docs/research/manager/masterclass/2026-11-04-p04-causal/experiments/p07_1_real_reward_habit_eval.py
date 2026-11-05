"""P07-1 REAL human choice experiment: reward learning vs habit vs memory.

NO generated human trials: source is authors' MIT-licensed data repository,
https://github.com/AnneCollins/WMH, with actual trial-by-trial choices and
reward feedback. We do not redistribute individual subjects' rows.

Primary: Expe1 (Collins & Frank 2012), subject-disjoint training, validation,
and held-out test; external generalization Expe3 EEG (2018), Expe5 fMRI (2017),
Expe12 developmental (2020), Expe14 probabilistic rewards (2020).
Grouped by subject and block. Candidate features at t include ONLY history
strictly earlier than choice at t, with no correct-answer column.

Reuses SciPy Matlab loader, sklearn GroupShuffleSplit, and SciPy L-BFGS-B.
Our models are small *illustrative predictive ablations inspired by* official
WMH MATLAB equations; this is NOT an exact reproduction of the paper's full
WMH/RLWM models, participant-level hierarchical fits, model recovery, or any
conclusion about causal neural mechanisms / real-world habit intervention.

Models: uniform, reward-value (RW trace), habitual action association +
last repeated action, reward+habit, reward+habit+memory. We use the SAME
precomputed strictly lagged features and participant splits for all variants.
Model/hyperparameter choice from validation; test and independent studies
never used to fit or select. Bootstrap by whole participant (cluster).

Privacy: no personal identifiers, row-level data, names, labels, RTs, or
individual fitted parameters saved in the GitHub output JSON.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from time import monotonic
import json
import os
import sys
import numpy as np
import pandas as pd
from scipy.io import loadmat
from scipy.optimize import minimize
from scipy.special import logsumexp
from scipy.stats import spearmanr
from sklearn.model_selection import GroupShuffleSplit

ROOT=Path(__file__).resolve().parents[6]
ARCHIVE=ROOT/"docs/research/manager/masterclass/2026-11-04-p04-causal"
EVIDENCE=ARCHIVE/"evidence"
SOURCE_ROOT=Path(os.environ.get("MANAGER_BEHAVIOR_SOURCE_DIR",
                       str(Path.home()/"Projects/manager-upstreams-20261105")))
WMH=SOURCE_ROOT/"WMH/RLWM/DataSets"
TWITTER=SOURCE_ROOT/"rl_twitter/03-stats_and_visualisation/source_data/data_fig4.csv"
SEED=202611057
ALPHA_REWARD=0.35
HABIT_UPDATE=0.07
MEMORY_DECAY=0.90
REGULARIZATION=0.002
N_ACTIONS=3
FEATURES=("reward_prediction","outcome_independent_habit","previous_same_stimulus_choice","recent_reward_memory")
MODELS={
 "uniform":(),
 "reward_only":(0,),
 "habit_only":(1,2),
 "reward_plus_habit":(0,1,2),
 "reward_plus_habit_plus_memory":(0,1,2,3),
}
# From original MIT-licensed author repo commit f2d4108dea80642e7d5b95d1c108916091a221c8.
EXPECTED_FILES={
 "Expe1.mat":"6af5270e2c57666984464cf882b34dbe6be39debdedb6995b048c617fb1188aa",
 "Expe3.mat":"5a7426dfaa9167895ae6dde5362feb9070197cedc9ce6ac7fa6b3ceae613751c",
 "Expe5.mat":"ab4a400d1567e065e14feda54245a2aaea64c0d91207f6e67a605097779da8da",
 "Expe12.mat":"2a939eb623252bd3fd7810204939892dbb555c4c72342b4c0cf7dca6497a7a0e",
 "Expe14.mat":"30449a404240174c9fbfb086d48c96fab7c7c4e99814b507e4c50f59b63f3204",
}
EXPECTED_TWITTER_FIG4="3dfb63887a6b7a555edb39b7ddb8adf9133480495d777e6bad15f09ed1c9bce7"


def file_sha(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def read_actual_trials(name:str)->tuple[np.ndarray,dict]:
    if name not in EXPECTED_FILES:raise ValueError("Unsupported official source")
    source=(SOURCE_ROOT/"WMH/RLWMP/DataSets"/name) if name=="Expe14.mat" else WMH/name
    if file_sha(source)!=EXPECTED_FILES[name]:
        raise ValueError(f"Author source data changed: {name}; freeze new version")
    m=loadmat(source,simplify_cells=True)
    arr=m["expe_data"]
    columns=list(m["columns"])
    required=["subno","block","ns","stimseq","choice","rew","rt"]
    if [columns[i] for i in (0,1,2,4,9,12,13)]!=required:
        raise ValueError(f"Column contract drift in {name}")
    if arr.ndim!=2 or arr.shape[1]!=17:raise ValueError("Expected original 17 columns")
    return arr,{
       "source":name,"sha256":file_sha(source),"real_trials_original":int(len(arr)),
       "origin":"Anne Collins, WMH, MIT source code and trial-level research data",
       "license":"MIT repository; original experimental studies must also be cited",
       "trial_original_columns":required,
       "forbidden_current_choice_target_columns":["corAseq","cor","pcor","delay"],
    }


def lagged_features(raw:np.ndarray)->tuple[np.ndarray,np.ndarray,np.ndarray,dict]:
    """Compute features for A=1,2,3 *before* any current choice/reward update.

    q: standard Rescorla–Wagner trace updated only by prior feedback
    h: association strengthened by choosing A, irrespective of reward
    wm: recent reward memory, decayed after every prior trial, downweighted
        by set size per the memory-capacity logic in Collins WMH paper
    prev: one-hot the previous choice for this same stimulus (not next action)
    """
    if raw.ndim!=2 or raw.shape[1]<14:raise ValueError("bad author raw matrix")
    # Source original ordered by subject/block; no reorder after sorting by
    # future correct action/outcome. Series are independent within blocks.
    columns=(0,1,2,4,9,12,13)
    keep=np.isfinite(raw[:,columns]).all(axis=1)
    keep &= np.isin(raw[:,9],[1,2,3])
    keep &= np.isin(raw[:,12],[0,1])
    keep &= raw[:,13]>.15
    keep &= (raw[:,2]>=2)&(raw[:,2]<=6)
    keep &= (raw[:,4]>=1)&(raw[:,4]<=raw[:,2])
    cleaned=raw[keep,:]
    if not len(cleaned):raise ValueError("No eligible real trial data")
    rejected=int(len(raw)-len(cleaned))
    # dictionary preserves the exact original order for each participant/block.
    blocks={}
    for i,r in enumerate(cleaned):
        key=(int(r[0]),int(r[1]))
        blocks.setdefault(key,[]).append(i)
    n=len(cleaned)
    x=np.zeros((n,N_ACTIONS,len(FEATURES)),dtype=np.float32)
    choice=(cleaned[:,9].astype(np.int8)-1)
    subject=cleaned[:,0].astype(np.int32)
    for (person,block),rows in blocks.items():
        first=cleaned[rows[0]]
        ns=int(first[2])
        # standard smooth traces; all current values are pre-choice.
        q=np.full((ns,N_ACTIONS),1/N_ACTIONS,dtype=float)
        h=np.zeros((ns,N_ACTIONS),dtype=float)
        wm=np.zeros((ns,N_ACTIONS),dtype=float)
        last=np.full(ns,-1,dtype=np.int8)
        for idx in rows:
            row=cleaned[idx]
            stim=int(row[4])-1
            if not 0<=stim<ns:
                raise ValueError("stimulus out of range in experiment")
            action=choice[idx]
            reward=float(row[12])
            x[idx,:,0]=q[stim,:]
            x[idx,:,1]=h[stim,:]
            x[idx,:,2]=(last[stim]==np.arange(N_ACTIONS)).astype(float)
            x[idx,:,3]=wm[stim,:]*min(1.0,2/ns)
            # NEXT trial state update, never current outcome in current feature.
            h*=1-HABIT_UPDATE
            h[stim,action]+=HABIT_UPDATE
            wm*=MEMORY_DECAY
            wm[stim,action]=reward
            q[stim,action]+=ALPHA_REWARD*(reward-q[stim,action])
            last[stim]=action
    summary={
       "trials_raw":int(len(raw)),
       "trials_eligible":n,
       "excluded_invalid_choice_reward_rt_or_stim":rejected,
       "participant_count":len(set(subject.tolist())),
       "block_count":len(blocks),
       "n_choices":N_ACTIONS,
       "feature_names":list(FEATURES),
       "future_correct_answer_field_used_as_feature":False,
       "current_reward_leaks_into_current_prediction":False,
       "all_history_reset_by_subject_and_block":True,
    }
    return x,choice,subject,summary


def group_split(subjects:np.ndarray)->dict[str,np.ndarray]:
    dummy=np.zeros(len(subjects))
    first=GroupShuffleSplit(n_splits=1,test_size=0.20,random_state=SEED)
    work,test=next(first.split(dummy,groups=subjects))
    second=GroupShuffleSplit(n_splits=1,test_size=0.25,random_state=SEED+1)
    tr,vl=next(second.split(work,groups=subjects[work]))
    train,val=work[tr],work[vl]
    buckets={"train":train,"validation":val,"test":test}
    group_sets={k:set(subjects[v].tolist()) for k,v in buckets.items()}
    if any(group_sets[a]&group_sets[b] for a,b in
           (("train","validation"),("train","test"),("validation","test"))):
        raise ValueError("subject leakage")
    return buckets


def fit_conditional_softmax(x:np.ndarray,y:np.ndarray,cols:tuple[int,...])->dict:
    """Use SciPy L-BFGS-B for the compact conditional-softmax ablation.

    Negative log-likelihood with participant-agnostic coefficients.
    We are not reimplementing the exact official WMH MLE/hierarchical code.
    """
    if not cols:return {"coef":[],"converged":True,"iterations":0}
    z=np.asarray(x[:,:,cols],dtype=np.float64)
    y=np.asarray(y,dtype=np.int32)
    n=len(y)
    if n<100 or z.shape!=(n,N_ACTIONS,len(cols)):
        raise ValueError("Invalid conditional choice dataset")
    selected=z[np.arange(n),y,:]
    def objective(beta):
        scores=z@beta
        logp=scores-logsumexp(scores,axis=1,keepdims=True)
        p=np.exp(logp)
        nll=-np.mean(logp[np.arange(n),y])+0.5*REGULARIZATION*np.dot(beta,beta)
        expected=np.einsum("na,nak->k",p,z)/n
        observed=np.mean(selected,axis=0)
        grad=expected-observed+REGULARIZATION*beta
        return float(nll),np.asarray(grad,dtype=float)
    result=minimize(objective,x0=np.zeros(len(cols)),jac=True,
                    method="L-BFGS-B",options={"maxiter":180,"ftol":1e-11})
    if not result.success:
        raise RuntimeError(f"Open source optimizer did not converge: {result.message}")
    return {
       "coef":result.x.tolist(),"converged":True,
       "iterations":int(result.nit),
       "solver":"scipy.optimize.minimize L-BFGS-B",
       "hyperparameters_fixed_before_holdout":True,
    }


def probabilities(x:np.ndarray,model:str,fit:dict)->np.ndarray:
    cols=MODELS[model]
    if not cols:
        return np.full((len(x),N_ACTIONS),1/N_ACTIONS)
    scores=np.asarray(x[:,:,cols],dtype=float)@np.asarray(fit["coef"],dtype=float)
    return np.exp(scores-logsumexp(scores,axis=1,keepdims=True))


def trial_scores(y:np.ndarray,p:np.ndarray)->tuple[np.ndarray,dict]:
    if p.shape!=(len(y),N_ACTIONS) or (p<=0).any() or (p>=1).any():
        raise ValueError("Bad action probability scores")
    if not np.allclose(p.sum(axis=1),1,rtol=0,atol=2e-7):
        raise ValueError("Predicted action probabilities don't sum to one")
    value=-np.log(np.maximum(p[np.arange(len(y)),y],1e-10))
    classification=np.argmax(p,axis=1)
    target=np.eye(N_ACTIONS)[y]
    return value,{
      "n_real_trials":int(len(y)),
      "log_loss_nats_per_trial":float(value.mean()),
      "accuracy":float(np.mean(classification==y)),
      "multiclass_brier":float(np.mean(np.sum((p-target)**2,axis=1))),
    }


def subject_bootstrap_advantage(
    model_losses:np.ndarray,base_losses:np.ndarray,subjects:np.ndarray,seed:int,
    bootstrap:int=600,
)->dict:
    """Positive improvement: baseline loss minus model loss. Re-sample subjects."""
    if not(len(model_losses)==len(base_losses)==len(subjects)):
        raise ValueError("inconsistent bootstrap scope")
    if bootstrap<40:raise ValueError("few bootstrap replicates")
    people=np.unique(subjects)
    rng=np.random.default_rng(seed)
    bysubject={}
    delta=np.asarray(base_losses)-np.asarray(model_losses)
    for u in people:
        v=delta[subjects==u]
        bysubject[int(u)]=(float(v.sum()),len(v))
    weighted=np.array([bysubject[int(u)] for u in people])
    draws=rng.integers(0,len(people),size=(bootstrap,len(people)))
    chosen=weighted[draws]
    estimates=chosen[:,:,0].sum(axis=1)/chosen[:,:,1].sum(axis=1)
    return {
       "mean_nll_improvement_nats_per_trial":float(delta.mean()),
       "cluster_bootstrap_CI95":[float(np.quantile(estimates,.025)),
                                 float(np.quantile(estimates,.975))],
       "participants_as_resampling_unit":int(len(people)),
       "bootstrap_replicates":bootstrap,
       "units":"log loss nats/trial: positive favors selected model",
       "uncertainty_is_sampling_conditional_on_historical_task":True,
    }


def describe_social_media_published_fit()->dict:
    """Original authors' figure-source DATA; no individual post rows used."""
    if file_sha(TWITTER)!=EXPECTED_TWITTER_FIG4:
        raise ValueError("Published figure source has changed")
    dat=pd.read_csv(TWITTER)
    required=["x_axis_mean_tpost","a_habit_weight","b_alpha_action","c_alpha_R"]
    if list(dat.columns)!=required:raise ValueError("Plot source columns drift")
    # This is a post-hoc descriptive comparison of already-fitted parameters,
    # NOT our independent refit of the paper's hybrid R model.
    out={"source_git_repo":"https://github.com/georgiaturner/rl_twitter",
         "source_git_commit":"09f418d2c6cb0989cd0c9b47d81d2644401b200d",
         "source_plot_file":"03-stats_and_visualisation/source_data/data_fig4.csv",
         "source_SHA256":file_sha(TWITTER),
         "sample":"paper's published confirmation sample fitted parameters",
         "n_users":int(len(dat)),
         "independent_refit":False,
         "raw_post_or_user_level_rows_committed":False,
         "correlations_exploratory_not_precommitted":True,
         "statistics":{}}
    for variable in required[1:]:
        current=dat[[required[0],variable]].dropna()
        correlation=spearmanr(current[required[0]],current[variable])
        out["statistics"][variable]={
          "spearman_rho":float(correlation.statistic),
          "p_two_sided_unadjusted":float(correlation.pvalue),
          "n":int(len(current)),
        }
    return out


def run()->dict:
    start=monotonic()
    data={}
    all_features={}
    for dataset in ("Expe1.mat","Expe3.mat","Expe5.mat","Expe12.mat","Expe14.mat"):
        rows,meta=read_actual_trials(dataset)
        x,y,subject,qc=lagged_features(rows)
        data[dataset]={"meta":meta,"qc":qc}
        all_features[dataset]=(x,y,subject)
        print("LOADED_AUTHOR_REAL_TRIALS",dataset,qc,flush=True)

    x,y,subjects=all_features["Expe1.mat"]
    splits=group_split(subjects)
    split_qc={
      k:{
       "n_trials":len(idx),"n_subjects":len(np.unique(subjects[idx])),
       "subject_ids_sha256":sha256(np.unique(subjects[idx]).tobytes()).hexdigest(),
      } for k,idx in splits.items()
    }
    settings={
      "seed":SEED,
      "features":list(FEATURES),
      "reward_RW_learning_rate_fixed":ALPHA_REWARD,
      "habit_choice_update_fixed":HABIT_UPDATE,
      "recent_memory_decay_fixed":MEMORY_DECAY,
      "n_actions":N_ACTIONS,
      "L2_penalty":REGULARIZATION,
      "selection_metric":"minimum validation action log loss",
      "model_candidates":{k:list(v) for k,v in MODELS.items()},
      "participant_disjoint":True,
      "external_studies_never_used_for_fit_or_select":True,
      "note":"Hand-fixed trace rates are pedagogical; beta fitted to training only",
    }
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    frozen=EVIDENCE/"P07-1_REAL_HABIT_PREANALYSIS_AND_MODEL_PLAN_20261105.json"
    frozen.write_text(json.dumps({"plan":settings,"source":data,
                                 "participant_split":split_qc},
                                ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    settings_hash=file_sha(frozen)
    fitted={
       name:fit_conditional_softmax(x[splits["train"]],y[splits["train"]],cols)
       for name,cols in MODELS.items()
    }
    def score_all(target_x,target_y):
        report={}
        loss={}
        for model,fit in fitted.items():
            p=probabilities(target_x,model,fit)
            l,s=trial_scores(target_y,p)
            report[model]=s
            loss[model]=l
        return report,loss
    validation,_=score_all(x[splits["validation"]],y[splits["validation"]])
    ranked=sorted(validation,
                  key=lambda k:(validation[k]["log_loss_nats_per_trial"],k))
    selected=ranked[0]
    simple_baseline=min(("reward_only","habit_only"),
                        key=lambda k:(validation[k]["log_loss_nats_per_trial"],k))
    # Test and OOD outputs only after model selection frozen.
    freeze={
       "preanalysis_file_sha256":settings_hash,
       "selected_on_validation_only":selected,
       "best_simple_model_selected_on_validation_only":simple_baseline,
       "models_fitted":fitted,
       "validation_scores":validation,
       "holdout_or_OOD_labels_used_to_tune":False,
       "all_test_and_OOD_outcomes_scored_only_after_freeze":True,
    }
    (EVIDENCE/"P07-1_REAL_HABIT_MODEL_FREEZE_20261105.json").write_text(
       json.dumps(freeze,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

    report={}
    for i,(dataset,idx) in enumerate((("Expe1.mat",splits["test"]),
                                      ("Expe3.mat",None),("Expe5.mat",None),
                                      ("Expe12.mat",None),("Expe14.mat",None))):
        xx,yy,sub=all_features[dataset]
        if idx is not None: xx,yy,sub=xx[idx],yy[idx],sub[idx]
        scores,losses=score_all(xx,yy)
        gain_uniform=subject_bootstrap_advantage(
            losses[selected],losses["uniform"],sub,seed=SEED+i*100)
        gain_strong=subject_bootstrap_advantage(
            losses[selected],losses[simple_baseline],sub,seed=SEED+i*100+1)
        gain_memory=subject_bootstrap_advantage(
            losses[selected],losses["reward_plus_habit"],sub,seed=SEED+i*100+2)
        report[dataset]={
           "evaluation":"participant-disjoint held-out" if idx is not None
                        else "independent external study; no tuning",
           "real_trials":len(yy),"unique_people":len(set(sub.tolist())),
           "mean_true_choices_by_action":[float(np.mean(yy==k)) for k in range(N_ACTIONS)],
           "all_model_scores":scores,
           "selected_model_gain_vs_uniform":gain_uniform,
           "selected_model_gain_vs_simple_baseline":gain_strong,
           "selected_model_gain_vs_reward_plus_habit_without_recent_memory":gain_memory,
           "no_individual_rows_or_subject_parameters_exported":True,
        }
        print("ACTUAL_CHOICE_EVALUATION",dataset,"SELECTED",selected,
              "MODELS_LOGLOSS",{k:round(v["log_loss_nats_per_trial"],4)
                                for k,v in scores.items()},
              "vs_simple",gain_strong,flush=True)
    social=describe_social_media_published_fit()
    result={
       "study":"P07-1: observed human reward and habit prediction on original Collins WMH task",
       "date":"2026-11-05","license_and_source":"AnneCollins/WMH MIT; original cited studies",
       "authors_code_commit":"f2d4108dea80642e7d5b95d1c108916091a221c8",
       "actual_experimental_datasets":data,
       "feature_construction":"exact historical lagged reward, non-reward choice trace, last choice, and recent WM",
       "supplementary_OOD_datasets_Expe12_and_Expe14_added_after_first_three_dataset_run":True,
       "original_matlab_full_model_reexecuted":False,
       "used_scipy_sklearn_numerical_libraries":True,
       "training_split":split_qc,
       "frozen_validation_selection":selected,
       "best_simple_validation_selection":simple_baseline,
       "models_fit":fitted,
       "validation_scores":validation,
       "heldout_and_external_generalization":report,
       "twitter_real_2026_habit_published_fig4_descriptive_replication":social,
       "fully_real_human_trials":True,
       "synthetic_human_subjects_added":0,
       "feature_contains_future_reward_or_correct_action":False,
       "real_human_stimulus_or_choice_intervention_executed":False,
       "reduced_rumination_or_clinical_effect_proven":False,
       "social_media_habit_link_is_descriptive_not_intervention_effect":True,
       "task_specific_model_not_general_behavior_FM":True,
       "real_behavior_training_data_committed":False,
       "human_subject_data_in_GitHub":False,
       "elapsed_seconds":round(monotonic()-start,2),
    }
    (EVIDENCE/"P07-1_REAL_REWARD_HABIT_HELDOUT_RESULTS_20261105.json").write_text(
       json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


if __name__=="__main__":
    run()
