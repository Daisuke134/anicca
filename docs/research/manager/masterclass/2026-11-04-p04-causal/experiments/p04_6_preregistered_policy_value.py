"""P04-6: synthetic preregistration and policy-vs-policy RCT decision value.

Zero real users, notifications, purchases, psychological interventions, or
preregistered human trials are involved. The experiment is synthetic and the
preanalysis plan is hashed BEFORE any synthetic trial outcomes are sampled.

Python 3.11+, NumPy.
"""
from __future__ import annotations

import csv
import hashlib
import json
from math import erfc, sqrt
from pathlib import Path

import numpy as np

STUDY_ID = "P04-6-SYNTHETIC-POLICY-RCT-20261104"
TRIAL_SEED = 20261146
N_TOTAL = 40_000
ALPHA = 0.05
NOTIFICATION_COST = 0.02


def manager_policy(motivation: np.ndarray, fatigue: np.ndarray) -> np.ndarray:
    """Frozen, P04-4-inspired synthetic rule: notify if motivation is low."""
    return (motivation == 0).astype(int)


def baseline_policy(motivation: np.ndarray, fatigue: np.ndarray) -> np.ndarray:
    """Prespecified plausible heuristic, same input data and available actions."""
    return ((motivation == 0) & (fatigue == 0)).astype(int)


def proposed_plan() -> dict:
    """What we commit to before looking at any synthetic outcomes."""
    return {
        "study_id": STUDY_ID,
        "study_type": "EDUCATIONAL SYNTHETIC RANDOMIZED POLICY EXPERIMENT",
        "not_real_or_publicly_registered": True,
        "claim": "Policy choice matters, beyond individual-outcome prediction accuracy",
        "population": "40,000 independent synthetic individuals (binary baseline traits)",
        "assignment_unit": "individual",
        "n_total_fixed": N_TOTAL,
        "randomization": "equal random assignment to two decision policies",
        "reference_seed": TRIAL_SEED,
        "manager_policy_version": "synthetic-cate-two-feature-fixed-rule-v1",
        "manager_policy": "notify iff motivation_pre == 0",
        "strong_comparator_note":
            "Plausible preregistered heuristic, NOT established globally strongest comparator",
        "baseline_policy": "notify iff motivation_pre == 0 and fatigue_pre == 0",
        "shared_available_features": ["motivation_pre", "fatigue_pre"],
        "shared_action_set": ["notify_once", "do_not_notify"],
        "followup_window": "one simulated period",
        "primary_outcome":
            "net_utility = observed_binary_task_completion - 0.02*notification_sent",
        "primary_estimand":
            "E[net_utility | randomized_manager_policy] - E[net_utility | randomized_heuristic_policy]",
        "null_hypothesis": "primary estimand == 0",
        "primary_direction_of_interest": "positive manager minus comparator",
        "two_sided_alpha": ALPHA,
        "analysis": "difference of randomized arm means and Wald 95% CI; fixed N",
        "planned_secondary_outcomes": ["task_completion_rate", "notification_rate"],
        "safety_guardrails": [
            "No more than one notification per synthetic subject",
            "Report completion and notification burden separately",
            "Never interpret this proxy utility as measured psychological benefit",
        ],
        "planned_subgroups": ["motivation_pre", "fatigue_pre"],
        "subgroup_inference": "descriptive/exploratory; not additional primary tests",
        "sequential_peeking": "PROHIBITED in confirmatory policy RCT",
        "distinct_optional_stopping_demo":
            "Separate A/A Monte Carlo showing inflated false-positive probability",
        "real_user_interventions": False,
        "outside_registry_preregistration": False,
    }


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def prepare(out: Path) -> dict:
    """Write and hash the complete specification, without any outcome generation."""
    out.mkdir(parents=True, exist_ok=True)
    plan = proposed_plan()
    plan_path = out / "P04-6_PREANALYSIS_PLAN_SYNTHETIC.json"
    plan_path.write_text(json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2)
                         + "\n", encoding="utf-8")
    digest = sha(plan_path.read_bytes())
    receipt = {
        "study_id": STUDY_ID,
        "plan_sha256": digest,
        "freeze_stage": "before synthetic outcome generation",
        "external_registry": "NOT REGISTERED; local educational hash only",
        "n_total_fixed": plan["n_total_fixed"],
        "policy_frozen_before_outcomes": True,
        "primary_outcome_frozen_before_outcomes": True,
    }
    (out / "P04-6_PLAN_FREEZE_RECEIPT.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return receipt


def verify_plan(out: Path) -> dict:
    plan_path = out / "P04-6_PREANALYSIS_PLAN_SYNTHETIC.json"
    receipt = json.loads((out / "P04-6_PLAN_FREEZE_RECEIPT.json")
                         .read_text(encoding="utf-8"))
    if sha(plan_path.read_bytes()) != receipt["plan_sha256"]:
        raise ValueError("Preanalysis plan changed after freezing")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    if plan != proposed_plan():
        raise ValueError("Study specification differs from frozen version")
    return plan


def two_arm_mean_difference(y: np.ndarray, randomized_arm: np.ndarray) -> dict:
    """Fixed-sample arm contrast; z-based two-sided CI, no optional peeking."""
    group1 = np.asarray(y)[randomized_arm == 1]
    group0 = np.asarray(y)[randomized_arm == 0]
    if min(len(group1),len(group0)) < 2:
        raise ValueError("At least two subjects required in each arm")
    diff = float(group1.mean()-group0.mean())
    se = float(np.sqrt(group1.var(ddof=1)/len(group1) +
                       group0.var(ddof=1)/len(group0)))
    if se == 0:
        raise ValueError("Standard error zero; inference undefined")
    z=diff/se
    return {
        "manager_policy_arm_mean": float(group1.mean()),
        "comparator_policy_arm_mean": float(group0.mean()),
        "difference": diff,
        "standard_error": se,
        "z": float(z),
        "p_two_sided": float(erfc(abs(z)/sqrt(2.0))),
        "ci95": [float(diff-1.96*se),float(diff+1.96*se)],
        "n_manager_arm": len(group1),
        "n_comparator_arm": len(group0),
    }


def simulate_trial(seed: int=TRIAL_SEED, n: int=N_TOTAL) -> dict[str, np.ndarray]:
    if n < 100:
        raise ValueError("n too small for this demonstration")
    rng=np.random.default_rng(seed)
    motivation=rng.integers(0,2,n)
    fatigue=rng.integers(0,2,n)
    randomized_arm=rng.integers(0,2,n)  # 1=Manager, 0=comparator
    manager_a=manager_policy(motivation,fatigue)
    baseline_a=baseline_policy(motivation,fatigue)
    selected_a=np.where(randomized_arm == 1,manager_a,baseline_a)
    p0=0.22+0.18*motivation-0.05*fatigue
    tau=0.16-0.20*motivation-0.06*fatigue
    potential_probability=p0+selected_a*tau
    assert np.all((potential_probability>0)&(potential_probability<1))
    outcome=(rng.random(n)<potential_probability).astype(int)
    utility=outcome-NOTIFICATION_COST*selected_a
    return dict(
        motivation=motivation,fatigue=fatigue,randomized_arm=randomized_arm,
        notify_sent=selected_a,outcome=outcome,net_utility=utility,
        oracle_p0=p0,oracle_tau=tau,
    )


def peek_demo(seed: int=20261147,repetitions: int=750,
              n_per_arm: int=1200) -> dict:
    """A/A false positives: repeatedly checking unadjusted nominal z-tests."""
    rng=np.random.default_rng(seed)
    looks=(200,400,600,800,1000,1200)
    if n_per_arm < max(looks):
        raise ValueError("Not enough samples for the specified looks")
    fixed_flags,peek_flags=[],[]
    for _ in range(repetitions):
        left=(rng.random(n_per_arm)<0.40).astype(int)
        right=(rng.random(n_per_arm)<0.40).astype(int)
        flags=[]
        for n in looks:
            dif=left[:n].mean()-right[:n].mean()
            se=np.sqrt(left[:n].var(ddof=1)/n+right[:n].var(ddof=1)/n)
            flags.append(bool(abs(dif/se)>1.96) if se>0 else False)
        fixed_flags.append(flags[-1])
        peek_flags.append(any(flags))
    return {
        "fully_synthetic_aa_trials":repetitions,
        "p_of_each_group":0.40,
        "nominal_alpha":0.05,
        "looks_n_per_arm":list(looks),
        "fixed_single_test_false_positive_rate":float(np.mean(fixed_flags)),
        "naive_peeking_any_look_false_positive_rate":float(np.mean(peek_flags)),
        "important": "Nominal 5% per look is NOT a 5% experimentwise false-positive bound",
    }


def theoretical_policy_value() -> dict:
    """Compute the true policy values in the synthetic 2x2 population."""
    rows=[]
    for m in (0,1):
        for f in (0,1):
            p0=0.22+0.18*m-0.05*f
            tau=0.16-0.20*m-0.06*f
            a1=int(m==0)
            a0=int(m==0 and f==0)
            rows.append(dict(
                motivation=m,fatigue=f,
                manager_policy_utility=p0+a1*tau-NOTIFICATION_COST*a1,
                comparator_utility=p0+a0*tau-NOTIFICATION_COST*a0,
            ))
    return {
        "expected_manager_policy_utility":
            float(np.mean([r["manager_policy_utility"] for r in rows])),
        "expected_comparator_policy_utility":
            float(np.mean([r["comparator_utility"] for r in rows])),
        "expected_incremental_net_utility":
            float(np.mean([r["manager_policy_utility"]-r["comparator_utility"]
                           for r in rows])),
        "subgroup_values":rows,
    }


def execute(out: Path) -> dict:
    """Read locked plan FIRST, then generate synthetic outcomes ONCE."""
    plan=verify_plan(out)
    data=simulate_trial(plan["reference_seed"],plan["n_total_fixed"])
    primary=two_arm_mean_difference(data["net_utility"],data["randomized_arm"])
    raw=two_arm_mean_difference(data["outcome"],data["randomized_arm"])
    notification=two_arm_mean_difference(data["notify_sent"],data["randomized_arm"])
    groups=[]
    for m in (0,1):
        for f in (0,1):
            sel=(data["motivation"]==m)&(data["fatigue"]==f)
            groups.append({
                "motivation_pre":m,
                "fatigue_pre":f,
                "n":int(sel.sum()),
                "exploratory_net_utility_difference":
                    two_arm_mean_difference(data["net_utility"][sel],
                                            data["randomized_arm"][sel])["difference"],
            })
    with (out / "P04-6_POLICY_RCT_SYNTHETIC.csv").open(
            "w",encoding="utf-8",newline="") as f:
        writer=csv.writer(f)
        writer.writerow(["synthetic_subject_id","motivation_pre","fatigue_pre",
                         "randomized_policy_arm","actual_notification",
                         "observed_binary_completion","net_utility"])
        for i in range(len(data["outcome"])):
            writer.writerow([i+1,int(data["motivation"][i]),int(data["fatigue"][i]),
                             int(data["randomized_arm"][i]),
                             int(data["notify_sent"][i]),int(data["outcome"][i]),
                             f'{data["net_utility"][i]:.2f}'])
    report={
        "study_id":STUDY_ID,
        "source":"SYNTHETIC EDUCATIONAL TRIAL - NO REAL PARTICIPANTS",
        "n":plan["n_total_fixed"],
        "primary_pre_specified_net_utility_contrast":primary,
        "secondary_completion_contrast":raw,
        "secondary_notification_rate_contrast":notification,
        "pre_specified_exploratory_subgroups":groups,
        "theoretical_2x2_population_values":theoretical_policy_value(),
        "plan_sha256":sha((out / "P04-6_PREANALYSIS_PLAN_SYNTHETIC.json").read_bytes()),
        "separate_aa_optional_peeking_demo":peek_demo(),
        "real_user_trial":False,
        "external_preregistration":False,
        "causal_claim": "within the stipulations of this synthetic randomized policy trial only",
    }
    (out / "P04-6_POLICY_RCT_SYNTHETIC_RESULTS.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report


def run(out: str|Path) -> dict:
    out=Path(out)
    prepare(out) # freeze first
    return execute(out)


if __name__=="__main__":
    base=Path(__file__).resolve().parent.parent / "evidence"
    report=run(base)
    print(json.dumps(report,ensure_ascii=False,indent=2))
