"""Real randomized-trial outcomes from public RCT Bench 125-trial collection.

A deliberately small, source-pinned aggregate audit of intervention outcomes.
Research-only: individual participant rows are NEVER committed nor uploaded.
RCT Bench trial datasets are curated from separately published trials; verify
rights for each underlying study before further commercial redistribution/use.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import math
import random
import statistics
import urllib.request

BASE = "https://bingkaiwang.github.io/RCT_Bench-main/cleaned_data/"
TRIALS = {
    20: {
        "sha256": "96c8b0d0108f3da7e29c0fbbba4d0a533c3a6dc35b3b87f91a1d0a75c7de5f56",
        "arms": ["IWT only", "IWT+Support"],
        "outcomes": ["YP_IWT_minutes_12w"],
        "context": "walking training 12-week adherence with additional support",
        "n_expected": 37,
    },
    103: {
        "sha256": "7a647f4511046c90f351a024a2207707c24a172d7c0aa203b8cdcabe33d70b19",
        "arms": ["Standard care", "MMHU"],
        "outcomes": ["YP_qaly_90d_observed"],
        "context": "90-day observed quality-adjusted life years (QALY) in older-adult hospital care",
        "n_expected": 599,
    },
    116: {
        "sha256": "7b991624a0f12b9f42e44acafdc8837640956f9ef9579a11bab012f7be1047d4",
        "arms": ["Group 1", "Group 2"],
        "outcomes": ["YP_factg_total_t2", "YP_dass_total_t2"],
        "context": "wellbeing/quality-of-life and distress measures after music + relaxation intervention; group coding unverified",
        "n_expected": 24,
    },
}
SEED = 20261106


def load(trial: int) -> list[dict[str, str]]:
    if trial not in TRIALS:
        raise ValueError("trial not in pinned rights-and-quality catalog")
    url = f"{BASE}trial{trial}.csv"
    req = urllib.request.Request(url, headers={"User-Agent": "Manager-Real-Intervention-Audit/0.1"})
    with urllib.request.urlopen(req,timeout=20) as resp:
        b=resp.read(2_000_000)
    if hashlib.sha256(b).hexdigest()!=TRIALS[trial]["sha256"]:
        raise ValueError("source hash mismatch; do not silently update dataset")
    rows=list(csv.DictReader(io.StringIO(b.decode("utf-8-sig"))))
    if len(rows)!=TRIALS[trial]["n_expected"]:
        raise ValueError("unexpected sample count")
    return rows


def numeric(x: object) -> float | None:
    if x is None or str(x).strip().upper() in {"", "NA", "NAN", "NULL"}:
        return None
    try:
        v=float(x)
    except (ValueError,TypeError,OverflowError):
        return None
    return v if math.isfinite(v) else None


def two_arm_summary(rows: list[dict], arm0: str, arm1: str,
                    outcome: str, n_boot: int = 1600, seed: int=SEED) -> dict:
    if len(rows)<4 or n_boot<100 or not outcome.startswith("YP_"):
        raise ValueError("invalid trial preconditions")
    if any("Treatment" not in row or outcome not in row for row in rows):
        raise ValueError("required columns absent")
    arms={arm0:[],arm1:[]}
    assigned={arm0:0,arm1:0}
    for r in rows:
        a=r["Treatment"]
        if a not in assigned:
            raise ValueError("unexpected third arm or treatment encoding")
        assigned[a]+=1
        v=numeric(r[outcome])
        if v is not None:
            arms[a].append(v)
    if not all(arms.values()):
        raise ValueError("no outcome in one group")
    rng=random.Random(seed)
    boot=[]
    for _ in range(n_boot):
        means=[]
        for label in (arm0,arm1):
            group=arms[label]
            means.append(sum(group[rng.randrange(len(group))] for _ in range(len(group)))/len(group))
        boot.append(means[1]-means[0])
    boot.sort()
    def q(p:float):
        x=(len(boot)-1)*p
        lo=int(x);hi=min(lo+1,len(boot)-1)
        return boot[lo]+(boot[hi]-boot[lo])*(x-lo)
    m0=statistics.mean(arms[arm0])
    m1=statistics.mean(arms[arm1])
    return {
        "outcome":outcome,
        "unit":"as coded in RCT Bench dataset; verify primary paper",
        "arm0":arm0,"arm1":arm1,
        "n_assigned_arm0":assigned[arm0],"n_assigned_arm1":assigned[arm1],
        "n_observed_arm0":len(arms[arm0]),"n_observed_arm1":len(arms[arm1]),
        "missing_arm0":assigned[arm0]-len(arms[arm0]),"missing_arm1":assigned[arm1]-len(arms[arm1]),
        "mean_arm0":m0,"mean_arm1":m1,
        "arm1_minus_arm0":m1-m0,
        "bootstrap_95ci_respondent_resample":[q(.025),q(.975)],
        "bootstrap_repetitions":n_boot,
        "seed":seed,
        "caveat":"Exploratory unadjusted complete-case contrast; does not replace prespecified trial analysis or correct differential attrition.",
        "individual_effects_known":False,
        "manager_intervention_efficacy_measured":False,
    }


def main():
    result={
        "date":"2026-11-06",
        "source":"https://bingkaiwang.github.io/RCT_Bench-main/",
        "study_type":"three_existing_individually_randomized_real_human_trials",
        "scope":"first public cross-domain baseline for Manager product model/eval",
        "license_boundary":"Underlying trial datasets may have individual reuse terms; no redistribution",
        "trials":[]
    }
    for id in sorted(TRIALS):
        info=TRIALS[id]
        rows=load(id)
        result["trials"].append({
            "trial_id":id,
            "n_source_rows":len(rows),
            "pinned_source_sha256":info["sha256"],
            "context":info["context"],
            "comparisons":[
                two_arm_summary(rows, info["arms"][0],info["arms"][1],outcome)
                for outcome in info["outcomes"]
            ]
        })
    print(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False))


if __name__=="__main__":
    main()
