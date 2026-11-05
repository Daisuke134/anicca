"""P06-3: preregistration, power, SRM, and safe stopping.

Reuses statsmodels NormalIndPower and SciPy t-test/chisquare; does NOT
reimplement a full experiment analysis platform or claim Statsig mSPRT.

This is exclusively a REPRODUCIBLE SYNTHETIC educational design, not an
actual registered trial, randomization of people, clinical experiment,
company feature release, or live experiment result.

Run with the isolated statistical Python environment on Mac mini:
 /private/tmp/manager-p06-statistics-20261105/bin/python p06_3_trial_design.py
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from math import ceil
from pathlib import Path
import json

import numpy as np
from scipy.stats import chisquare, ttest_ind
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

ALPHA = 0.05
POWER = 0.80
BASE_RATE = 0.25
MDE = 0.03
ATTRITION = 0.15
EARLY_LOOKS = (100, 200, 300, 400)
EARLY_LOOKS_COUNT = len(EARLY_LOOKS)
AA_REPLICATIONS = 2400
AA_SEED = 202611053


def sha(value: bytes) -> str:
    return sha256(value).hexdigest()


def plan() -> dict:
    return {
        "study": "P06-3 SYNTHETIC experiment design; NOT registered or run on real people",
        "version": "0.1",
        "hypothesis": "Manager changed-navigation variant improves correct official-link finding vs no-change",
        "randomization_unit": "participant, if future consent/ethics approvals allow",
        "assignment": "50:50 persistent per unit, pre-specified seed",
        "primary": "found_correct_official_link_within_prespecified_seconds",
        "p_control_assumption": BASE_RATE,
        "minimum_detectable_absolute_improvement": MDE,
        "alpha": ALPHA,
        "target_power": POWER,
        "anticipated_attrition": ATTRITION,
        "analysis": "two-sided two-independent-proportion z approximation, one fixed final analysis",
        "multiple_looks_example": "If four unplanned efficacy decisions are needed, conservative Bonferroni alpha/4",
        "real_early_stopping": "Statsig mSPRT/SPRT or preregistered group sequential spending, not naive p-value peeking",
        "data_quality_sample_ratio_mismatch": "p < 0.001 chi-squared triggers review; no ship",
        "quality_gates": ["exposure logged","assignment unit stable","valid control source",
                          "independent outcome readback","consent and data rights",
                          "no unexpected leakage","no duplicated users",
                          "sufficient follow-up","predefined missingness handling"],
        "guardrails": ["wrong external site navigation","complaints/opt-outs",
                       "dropout","privacy incidents","site availability"],
        "harm_rule": "Stop for serious safety incidents regardless of primary p-value",
        "decision_rule": "Must pass data quality and powered primary + guardrails; no outcomes = inconclusive",
        "participant_data_available": False,
        "independent_real_outcomes_available": False,
        "external_preregistration": False,
        "phase5_live_release_completed": False,
        "four_aa_looks_n_per_arm": list(EARLY_LOOKS),
        "aa_repetitions": AA_REPLICATIONS,
        "aa_seed": AA_SEED,
    }


def write_plan(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    spec=plan()
    document=output/"P06-3_PREANALYSIS_DESIGN_SYNTHETIC.json"
    document.write_text(json.dumps(spec,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    digest=sha(document.read_bytes())
    freeze={
        "document": document.name,
        "plan_sha256": digest,
        "status": "LOCALLY_FROZEN_BEFORE_AA_SIMULATION",
        "external_registry": False,
        "real_participants": 0,
    }
    (output/"P06-3_PLAN_FREEZE_SYNTHETIC.json").write_text(
        json.dumps(freeze,ensure_ascii=False,indent=2)+"\n")
    return freeze


def sample_size() -> dict:
    """Reuse the official statsmodels calculations; no hand-coded replacement."""
    ps=proportion_effectsize(BASE_RATE+MDE,BASE_RATE)
    power=NormalIndPower()
    fixed=power.solve_power(effect_size=abs(ps),nobs1=None,alpha=ALPHA,
                            power=POWER,ratio=1,alternative="two-sided")
    corrected=power.solve_power(effect_size=abs(ps),nobs1=None,
                                alpha=ALPHA/EARLY_LOOKS_COUNT,power=POWER,
                                ratio=1,alternative="two-sided")
    return {
        "baseline_completion_assumption": BASE_RATE,
        "treatment_completion_assumption": BASE_RATE+MDE,
        "MDE_pp": MDE*100,
        "alpha": ALPHA, "power": POWER,
        "library": "statsmodels.stats.power.NormalIndPower.solve_power",
        "effect_size_cohen_h": float(ps),
        "fixed_horizon_n_per_arm": ceil(fixed),
        "fixed_horizon_total_recruited_for_15pct_loss":
            2*ceil(ceil(fixed)/(1-ATTRITION)),
        "four_planned_looks_naive_bonferroni_alpha_per_look":
            ALPHA/EARLY_LOOKS_COUNT,
        "bonferroni_n_per_arm_at_80pct_power": ceil(corrected),
        "bonferroni_total_recruited_for_15pct_loss":
            2*ceil(ceil(corrected)/(1-ATTRITION)),
        "cannot_start_real_trial": True,
        "real_study_populations": 0,
        "interpretation": "illustrative sample requirement; baseline and MDE are NOT measured on real Manager users",
    }


def srm_check(n_control: int, n_treat: int,
              expected_control_share: float=.5) -> dict:
    if n_control<0 or n_treat<0 or n_control+n_treat==0:
        raise ValueError("invalid sample ratio")
    if not 0<expected_control_share<1:
        raise ValueError("invalid expected share")
    n=n_control+n_treat
    stat,p=chisquare([n_control,n_treat],
                     f_exp=[n*expected_control_share,n*(1-expected_control_share)])
    return {"n_control":n_control,"n_treatment":n_treat,
            "expected_control_share":expected_control_share,
            "chi_square":float(stat),"p":float(p),
            "invalid_srm_at_p_lt_0_001":bool(p<.001)}


def aa_peeking_demo() -> dict:
    """Evaluate FWER under NULL; fixed and repeated are DIFFERENT tests.

    Same null means, 4 correlated looks, z/t p-values *only* for demo.
    Bonferroni is a valid but conservative workaround, not Statsig mSPRT.
    """
    rng=np.random.default_rng(AA_SEED)
    ctrl=rng.standard_normal((AA_REPLICATIONS,max(EARLY_LOOKS)))
    treat=rng.standard_normal((AA_REPLICATIONS,max(EARLY_LOOKS)))
    pvals=np.empty((AA_REPLICATIONS,len(EARLY_LOOKS)))
    for idx,each in enumerate(EARLY_LOOKS):
        test=ttest_ind(treat[:,:each],ctrl[:,:each],
                       axis=1,equal_var=False)
        pvals[:,idx]=test.pvalue
    naive=np.any(pvals<ALPHA,axis=1)
    corrected=np.any(pvals<ALPHA/EARLY_LOOKS_COUNT,axis=1)
    final=(pvals[:,-1]<ALPHA)
    return {
        "simulation_kind":"A/A all effects exactly zero in DGP",
        "n_repetitions": AA_REPLICATIONS,
        "looks_n_per_arm":list(EARLY_LOOKS),
        "naive_any_of_four_looks_false_positive":float(np.mean(naive)),
        "bonferroni_any_of_four_looks_false_positive":float(np.mean(corrected)),
        "only_last_look_false_positive":float(np.mean(final)),
        "nominal_alpha":ALPHA,
        "bonferroni_per_look_alpha":ALPHA/EARLY_LOOKS_COUNT,
        "caution":"finite Monte Carlo uncertainty; conservative Bonferroni only; not mSPRT; no people",
    }


def run(output: Path) -> dict:
    receipt=write_plan(output)
    pre=output/"P06-3_PREANALYSIS_DESIGN_SYNTHETIC.json"
    if sha(pre.read_bytes())!=receipt["plan_sha256"]:
        raise ValueError("preanalysis plan changed after freeze")
    sizes=sample_size()
    aa=aa_peeking_demo()
    result={
        "phase":"P06-3","research_only":True,
        "plan_sha256":receipt["plan_sha256"],
        "power":sizes,"AA_early_stopping":aa,
        "normal_505_495":srm_check(505,495),
        "broken_560_440":srm_check(560,440),
        "real_trial_registered":False,
        "real_RCT_started":False,
        "actual_real_participants":0,
    }
    (output/"P06-3_POWER_AND_STOPPING_RESULTS.json").write_text(
        json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    return result

if __name__=="__main__":
    r=run(Path(__file__).resolve().parents[1]/"evidence")
    print(json.dumps({"sample_size":r["power"],
                      "aa":r["AA_early_stopping"],
                      "srm_bad":r["broken_560_440"]},
                     ensure_ascii=False,indent=2))
