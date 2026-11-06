"""P06-4: net contribution, costs, refunds, guardrails, and uncertainty.

All business records are SYNTHETIC and intentionally generated with a
positive conversion effect and an ADVERSE complaint/opt-out guardrail.
The shipping decision must therefore be NO_GO despite possible profit gain.

Uses scipy.stats Welch mean-difference inference; does not reimplement
A/B platform, financial ledger, or classify proxy complaints as clinical harm.
No real customers, bills, bank balances, marketing accounts or interventions.
"""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import json

import numpy as np
from scipy.stats import ttest_ind
from p06_3_trial_design import srm_check

SEED = 202611054
N = 30000
CURRENCY = "JPY"
MAX_ADVERSE_COMPLAINT_INCREASE = 0.003
ALPHA = 0.05


def plan() -> dict:
    return {
        "study": "P06-4 SYNTHETIC ecommerce business impact and guardrail demo",
        "seed": SEED,
        "n_subjects": N,
        "design": "randomized assignment to baseline or what-if-manager; fixed sample",
        "primary_outcome": "net_contribution_yen_per_assigned_unit",
        "formula": (
            "recognized_paid_revenue_after_refunds - provider_fees - fulfillment"
            " - refund_processing - acquisition_cost - model_inference_cost"
            " - incremental_operator_cost - complaint_service_cost"
        ),
        "currency": CURRENCY,
        "price_yen": 5800.0,
        "baseline_purchase_prob": 0.055,
        "manager_purchase_increment": 0.016,
        "refund_prob_among_paid": 0.10,
        "baseline_complaint_prob": 0.012,
        "manager_complaint_increment": 0.012,
        "provider_fee_per_paid_yen": 180.0,
        "fulfillment_per_paid_yen": 1850.0,
        "refund_processing_per_refunded_yen": 130.0,
        "acquisition_per_assignment_yen": 70.0,
        "model_inference_per_manager_assignment_yen": 5.0,
        "operator_per_manager_assignment_yen": 1.5,
        "service_per_complaint_yen": 450.0,
        "guardrail_metric": "complaint_or_optout_rate (fictional, NOT clinical harm)",
        "allowed_guardrail_increase_absolute": MAX_ADVERSE_COMPLAINT_INCREASE,
        "ship_rule": (
            "only when primary 95% CI lower > 0, complaint difference CI upper <="
            " 0.003, no SRM, and real independent receipt/cost/outcome sources exist"
        ),
        "financial_scope_excludes": ["unallocated fixed overhead","taxes","customer lifetime value",
                                     "uncertain future refunds","opportunity cost outside period"],
        "external_payment_receipts_present": False,
        "actual_human_harm_outcomes": False,
        "preregistered_externally": False,
        "fraud_detection_and_user_consent":"not simulated; must gate real studies",
    }


def checksum(raw: bytes) -> str:
    return sha256(raw).hexdigest()


def prefreeze(out: Path) -> dict:
    out.mkdir(parents=True,exist_ok=True)
    doc=out/"P06-4_PREANALYSIS_SYNTHETIC.json"
    doc.write_text(json.dumps(plan(),ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    freeze={"sha256":checksum(doc.read_bytes()),
            "stage":"BEFORE_SYNTHETIC_OUTCOME_GENERATION",
            "external_registration":False,"real_ledger_accessed":False}
    (out/"P06-4_PREANALYSIS_FREEZE.json").write_text(
        json.dumps(freeze,ensure_ascii=False,indent=2)+"\n")
    return freeze


def generate(seed:int=SEED, n:int=N) -> dict[str,np.ndarray]:
    if not 100<=n<=300000:
        raise ValueError("bounded synthetic size")
    spec=plan()
    rng=np.random.default_rng(seed)
    group=rng.integers(0,2,size=n)
    purchase=(rng.random(n) <
              spec["baseline_purchase_prob"]+
              group*spec["manager_purchase_increment"])
    refund=purchase & (rng.random(n)<spec["refund_prob_among_paid"])
    complaint=(rng.random(n) <
               spec["baseline_complaint_prob"]+
               group*spec["manager_complaint_increment"])
    price=spec["price_yen"]
    gross=price*purchase
    refunded_revenue=price*refund
    recognized=gross-refunded_revenue
    variable_cost=(spec["provider_fee_per_paid_yen"]+
                   spec["fulfillment_per_paid_yen"])*purchase
    variable_cost+=spec["refund_processing_per_refunded_yen"]*refund
    variable_cost+=spec["acquisition_per_assignment_yen"]
    variable_cost+=spec["model_inference_per_manager_assignment_yen"]*group
    variable_cost+=spec["operator_per_manager_assignment_yen"]*group
    variable_cost+=spec["service_per_complaint_yen"]*complaint
    contribution=recognized-variable_cost
    return {
        "arm":group,"paid_purchase":purchase.astype(int),
        "refunded_purchase":refund.astype(int),
        "complaint":complaint.astype(int),
        "gross_revenue":gross.astype(float),
        "refund_yen":refunded_revenue.astype(float),
        "recognized_revenue":recognized.astype(float),
        "variable_cost":variable_cost.astype(float),
        "net_contribution":contribution.astype(float),
    }


def mean_diff(y:np.ndarray, group:np.ndarray) -> dict:
    """Scipy Welch inference; no custom statistical test implementation."""
    treated=np.asarray(y)[group==1].astype(float)
    control=np.asarray(y)[group==0].astype(float)
    if len(treated)<3 or len(control)<3:
        raise ValueError("insufficient observations")
    res=ttest_ind(treated,control,equal_var=False)
    ci=res.confidence_interval(confidence_level=.95)
    return {
        "manager_mean":float(treated.mean()),
        "baseline_mean":float(control.mean()),
        "diff":float(treated.mean()-control.mean()),
        "ci95":[float(ci.low),float(ci.high)],
        "p_two_sided":float(res.pvalue),
        "n_manager":int(len(treated)),
        "n_baseline":int(len(control)),
    }


def decision(primary:dict, complaint:dict, quality:dict,
             independent_outcomes:bool) -> dict:
    """Success metric alone is NEVER sufficient to ship."""
    positive=primary["ci95"][0]>0
    safe=complaint["ci95"][1]<=MAX_ADVERSE_COMPLAINT_INCREASE
    data_valid=not quality["invalid_srm_at_p_lt_0_001"]
    ready=positive and safe and data_valid and independent_outcomes
    return {
        "decision": "ELIGIBLE_FOR_REVIEW" if ready else "DO_NOT_SHIP",
        "positive_primary_CI":bool(positive),
        "guardrail_upper_below_max":bool(safe),
        "sample_ratio_valid":bool(data_valid),
        "verified_external_real_outcomes":bool(independent_outcomes),
        "reason": [
            title for title,ok in (
                ("primary_lower_CI_not_positive",positive),
                ("complaint_guardrail_not_proven_safe",safe),
                ("invalid_sample_ratio",data_valid),
                ("no_independent_real_benefit_receipt",independent_outcomes),
            ) if not ok
        ],
    }


def real_world_proof_outcome(official_receipts:Optional[object]=None) -> dict:
    """Fail closed: None does not mean zero cost, zero harm or no outcomes."""
    if official_receipts is None:
        return {"paid_recognized_revenue_yen":None,"refunds_yen":None,
                "actual_variable_cost_yen":None,"real_complaint_rate":None,
                "real_incremental_contribution_yen":None,
                "status":"NOT_MEASURED_MISSING_VERIFIED_RECEIPTS",
                "can_ship":False}
    raise ValueError("Real financial adapter not yet implemented; do not guess")


def run(out:Path) -> dict:
    frozen=prefreeze(out)
    doc=out/"P06-4_PREANALYSIS_SYNTHETIC.json"
    if checksum(doc.read_bytes())!=frozen["sha256"]:
        raise ValueError("financial prereg changed after freeze")
    toy=generate()
    arm=toy["arm"]
    metrics={k:mean_diff(toy[k],arm) for k in (
        "paid_purchase","refunded_purchase","complaint",
        "gross_revenue","refund_yen","recognized_revenue",
        "variable_cost","net_contribution")}
    ratio=srm_check(int(np.sum(arm==0)),int(np.sum(arm==1)))
    toy_decision=decision(metrics["net_contribution"],metrics["complaint"],
                          ratio,independent_outcomes=False)
    real=real_world_proof_outcome()
    return_data={
        "study":"P06-4 synthetic sales/returns/costs and adverse guardrail",
        "plan_sha256":frozen["sha256"],
        "n":N,"currency":CURRENCY,
        "metrics":metrics,
        "sample_ratio_quality":ratio,
        "toy_strict_ship_gate":toy_decision,
        "real_financial_outcome":real,
        "no_cost_field_imputed_from_missing":True,
        "no_real_customers_or_payment_records":True,
        "no_real_intervention_performed":True,
        "fixed_cost_and_tax_not_included":True,
    }
    (out/"P06-4_INCREMENTAL_VALUE_SYNTHETIC_RESULTS.json").write_text(
        json.dumps(return_data,ensure_ascii=False,indent=2)+"\n")
    return return_data

if __name__=="__main__":
    out=Path(__file__).resolve().parents[1]/"evidence"
    result=run(out)
    print(json.dumps({
        "profit_per_assigned_user":result["metrics"]["net_contribution"],
        "adverse_complaint_rate":result["metrics"]["complaint"],
        "decision":result["toy_strict_ship_gate"],
        "real_business_proof":result["real_financial_outcome"],
    },ensure_ascii=False,indent=2))
