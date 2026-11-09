"""Data-to-model teaching lab for BehaviorBench and Psych-101 (2026-11-08).

100% self-authored SYNTHETIC decisions. No public benchmark test data is used
for training. No Psych-101 rows, sensitive survey respondents, actual users,
gated files, licensed model weights, network calls, or live human actions.

Separate claims: evaluation artifacts vs training corpus vs customer outcomes.
The masked character positions demonstrate response-only supervision, NOT
production token masks: real tokenizers require aligned token offsets.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from json import dumps
from math import exp, log
from random import Random
from statistics import mean
import re

BEHAVIORBENCH_TEST_USAGE="NONCOMMERCIAL_EVALUATION_ONLY_NOT_TRAINING"
PSYCH101_TRAIN_USAGE="APACHE2_DATA_CARD_ADDITIONAL_RIGHTS_REVIEW_REQUIRED"
PSYCH101_TEST_USAGE="GATED_CC_BY_ND_NOT_ACCESSED"
CHOICE_PATTERN=re.compile(r"<<([LR])>>")

def sigmoid(z:float)->float:
    if z>=0:return 1/(1+exp(-z))
    v=exp(z)
    return v/(1+v)

def make_synthetic_decisions(studies:int=4,persons_per_study:int=32,trials:int=9,
                             seed:int=101)->list[dict]:
    """Synthetic per-person trial histories with known simulated label mechanism."""
    if min(studies,persons_per_study,trials)<2:
        raise ValueError("require >=2 studies, persons, and trials")
    rng=Random(seed)
    out=[]
    for study in range(studies):
        for person in range(persons_per_study):
            previous=0
            # This latent value is only a synthetic nuisance, NEVER a protected trait.
            latent=rng.uniform(-.3,.3)
            for t in range(trials):
                context=rng.randrange(2)
                p=sigmoid(-1.30+2.25*context+.75*previous+latent)
                chosen=int(rng.random()<p)
                out.append({
                    "study_id":f"toy-study-{study}",
                    "participant_id":f"toy-participant-{person}",
                    "trial":t,
                    "context":context,
                    "previous_choice":previous,
                    "observed_choice":chosen,
                    "outcome_recorded_before_next_trial":True,
                    "synthetic":True,
                })
                previous=chosen
    return out

def split_by_person_within_study(rows:list[dict],seed:int=17,
                                  train_fraction:float=.7,val_fraction:float=.1)->dict:
    """No (study_id,participant_id) occurs across train/validation/test."""
    if not rows or not 0<train_fraction<1 or not 0<=val_fraction<1-train_fraction:
        raise ValueError("invalid split")
    groups=defaultdict(lambda:defaultdict(list))
    for row in rows:
        if not row.get("synthetic",False):
            raise ValueError("only synthetic examples supported by this lab")
        study=row["study_id"];pid=row["participant_id"]
        groups[study][pid].append(row)
    splits={"train":[],"validation":[],"test":[]}
    for study,subjects in sorted(groups.items()):
        keys=sorted(subjects)
        if len(keys)<5:raise ValueError("need >=5 people per study")
        Random(seed+sum(ord(c) for c in study)).shuffle(keys)
        train=max(1,int(len(keys)*train_fraction))
        validation=max(1,int(len(keys)*val_fraction))
        if train+validation>=len(keys):raise ValueError("not enough holdout people")
        for idx,pid in enumerate(keys):
            role="train" if idx<train else ("validation" if idx<train+validation else "test")
            splits[role].extend(subjects[pid])
    assert_disjoint_groups(splits,"person")
    return splits

def assert_disjoint_groups(splits:dict,kind:str)->None:
    """person or study level grouping. Duplicate rows cannot silently pass."""
    if kind not in ("person","study"):
        raise ValueError("unsupported grouping")
    keys_by_split={}
    for split,rows in splits.items():
        if kind=="person":
            keys={(r["study_id"],r["participant_id"]) for r in rows}
        else:
            keys={r["study_id"] for r in rows}
        keys_by_split[split]=keys
    names=list(keys_by_split)
    for i,x in enumerate(names):
        for y in names[i+1:]:
            if keys_by_split[x]&keys_by_split[y]:
                raise ValueError(f"LEAKAGE between {x} and {y}")

def leave_one_study_out(rows:list[dict],held_out_study:str)->dict:
    if not rows or not any(r["study_id"]==held_out_study for r in rows):
        raise ValueError("valid held-out study required")
    result={
        "train":[r for r in rows if r["study_id"]!=held_out_study],
        "test":[r for r in rows if r["study_id"]==held_out_study],
    }
    assert_disjoint_groups(result,"study")
    return result

def session_to_psych101_style(rows:list[dict])->dict:
    """Illustrative transcript schema, NEVER an actual Psych-101 transcript."""
    if not rows:
        raise ValueError("nonempty session required")
    first=rows[0]
    key=(first["study_id"],first["participant_id"])
    if any((r["study_id"],r["participant_id"])!=key for r in rows):
        raise ValueError("a transcript must contain one participant session")
    ordered=sorted(rows,key=lambda r:r["trial"])
    if [r["trial"] for r in ordered]!=list(range(len(rows))):
        raise ValueError("contiguous trial indices required")
    lines=[
        "SYNTHETIC two-action learning experiment.",
        "At each trial select L or R. Choices, not instructions, are supervised.",
    ]
    for r in ordered:
        label="R" if r["observed_choice"] else "L"
        lines.append(f"Trial {r['trial']}; context {r['context']}. Human chooses <<{label}>>.")
    return {"text":"\n".join(lines),"experiment":first["study_id"],
            "participant":first["participant_id"],"synthetic":True}

def response_only_character_mask(text:str)->list[int]:
    """Teaching artifact: 1 on characters inside <<...>>, 0 elsewhere.

    REAL LM training must tokenize first and align labels to token offsets.
    Fails closed if markers are malformed or no choices exist.
    """
    matches=list(CHOICE_PATTERN.finditer(text))
    if not matches or text.count("<<")!=len(matches) or text.count(">>")!=len(matches):
        raise ValueError("bad or absent choice delimiters")
    mask=[0]*len(text)
    for m in matches:
        for i in range(m.start(1),m.end(1)):
            mask[i]=1
    return mask

def training_example_from_history(rows:list[dict],target_index:int)->dict:
    """BehaviorBench-like chat record using ONLY PAST trials as input."""
    ordered=sorted(rows,key=lambda r:r["trial"])
    if not 0<=target_index<len(ordered):
        raise ValueError("invalid target trial")
    this=ordered[target_index]
    past=ordered[:target_index]
    if any(r["trial"]>=this["trial"] for r in past):
        raise ValueError("future information detected")
    history=", ".join("R" if r["observed_choice"] else "L" for r in past)
    answer="R" if this["observed_choice"] else "L"
    return {
        "system":"You are predicting an observed SYNTHETIC choice, not an ideal choice.",
        "user":f"Past choices: [{history}]. Current context: {this['context']}. Choose L or R.",
        "assistant":answer,
        "label_origin":"SELF_AUTHORED_SYNTHETIC_HUMAN_STYLE_CHOICE",
        "target_trial":this["trial"],
        "history_length":len(past),
        "for_model_training":True,
    }

def bernoulli_nll(probabilities:list[float],labels:list[int])->float:
    if len(probabilities)!=len(labels) or not labels:
        raise ValueError("matching nonempty probabilities/labels required")
    if any(not isinstance(p,(int,float)) or not 0<p<1 for p in probabilities):
        raise ValueError("probabilities must be strictly between zero and one")
    if any(y not in (0,1) for y in labels):
        raise ValueError("binary labels required")
    return mean(-log(p) if y else -log(1-p) for p,y in zip(probabilities,labels))

def brier(probabilities:list[float],labels:list[int])->float:
    if len(probabilities)!=len(labels) or not labels:
        raise ValueError("matching nonempty lists required")
    if any(not 0<=p<=1 for p in probabilities) or any(y not in (0,1) for y in labels):
        raise ValueError("invalid probabilities or binary labels")
    return mean((p-y)**2 for p,y in zip(probabilities,labels))

def tvd_binary(p_of_right:float,q_of_right:float)->float:
    if not 0<=p_of_right<=1 or not 0<=q_of_right<=1:
        raise ValueError("invalid distribution")
    return abs(p_of_right-q_of_right)

def fit_toy_logistic(rows:list[dict],epochs:int=300,lr:float=.55)->tuple[float,float,float]:
    """Real gradient updates on fictional labels; NOT an LLM or real behavioral FM."""
    if not rows or epochs<=0 or not 0<lr<=1:
        raise ValueError("invalid training parameters")
    b=w_context=w_prev=0.
    for _ in range(epochs):
        db=dx=dh=0.
        for row in rows:
            pred=sigmoid(b+w_context*row["context"]+w_prev*row["previous_choice"])
            residual=pred-row["observed_choice"]
            db+=residual;dx+=residual*row["context"];dh+=residual*row["previous_choice"]
        inv=lr/len(rows)
        b-=db*inv;w_context-=dx*inv;w_prev-=dh*inv
    return b,w_context,w_prev

def predict_toy(params:tuple[float,float,float],rows:list[dict])->list[float]:
    b,w_context,w_prev=params
    return [sigmoid(b+w_context*r["context"]+w_prev*r["previous_choice"]) for r in rows]

def enforce_data_rights(dataset:str,purpose:str)->str:
    """Conservative teaching gate: not a substitute for legal rights review."""
    if purpose not in {"academic_evaluation","commercial_model_training","source_review"}:
        raise ValueError("unknown purpose")
    if dataset=="befm/BehaviorBench":
        if purpose!="academic_evaluation":
            raise PermissionError("BehaviorBench public bundle is eval-only CC BY-NC-ND")
        return "ACADEMIC_EVALUATION_ONLY_WITH_UPSTREAM_TERMS"
    if dataset=="marcelbinz/Psych-101-test":
        raise PermissionError("gated test data not acquired or authorized in this lab")
    if dataset=="marcelbinz/Psych-101":
        if purpose=="commercial_model_training":
            raise PermissionError("Apache2 dataset card alone does not clear upstream and model rights")
        return "SOURCE_REVIEW_ONLY_NO_ROWS_ACCESSED"
    if dataset=="self-authored-synthetic":
        return "SYNTHETIC_LEARNING_ONLY"
    raise PermissionError("unreviewed dataset")

def synthetic_training_evidence()->dict:
    rows=make_synthetic_decisions()
    splits=split_by_person_within_study(rows)
    train,test=splits["train"],splits["test"]
    params=fit_toy_logistic(train)
    test_y=[r["observed_choice"] for r in test]
    mean_prior=(sum(r["observed_choice"] for r in train)+.5)/(len(train)+1)
    baseline=[mean_prior]*len(test)
    trained=predict_toy(params,test)
    sample_session=[r for r in rows if r["study_id"]=="toy-study-0" and r["participant_id"]=="toy-participant-0"]
    transcript=session_to_psych101_style(sample_session)
    response_mask=response_only_character_mask(transcript["text"])
    return {
        "evidence":"FULLY_SYNTHETIC_TEACHING_ONLY",
        "n_sessions":4*32,
        "n_decisions":len(rows),
        "train_decisions":len(train),
        "validation_decisions":len(splits["validation"]),
        "test_decisions":len(test),
        "baseline_nll":bernoulli_nll(baseline,test_y),
        "toy_trained_nll":bernoulli_nll(trained,test_y),
        "baseline_brier":brier(baseline,test_y),
        "toy_trained_brier":brier(trained,test_y),
        "toy_trained_parameters":list(params),
        "heldout_study_synthetic":True,
        "supervised_character_count_in_sample":sum(response_mask),
        "masked_character_count_in_sample":len(response_mask)-sum(response_mask),
        "sample_transcript_sha256":sha256(transcript["text"].encode()).hexdigest(),
        "test_never_used_for_weight_updates":True,
        "behaviorbench_evaluation_data_for_training":False,
        "real_human_responses_used":False,
        "actual_foundation_model_trained":False,
        "commercial_model_rights_cleared":False,
    }

if __name__=="__main__":
    print(dumps(synthetic_training_evidence(),ensure_ascii=False,sort_keys=True,indent=2))
