"""P12-2/3/4: synthetic longitudinal, editorial and monitoring research exercises.

Educational mathematics only.  No user health data, patient data, real-world
intervention, clinical decision, automated publishing or production deployment.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import log, isfinite
from hashlib import sha256
from json import dumps


def attrition_binary_effect_bounds(n_t: int, observed_t: int, success_t: int,
                                   n_c: int, observed_c: int, success_c: int) -> dict:
    """Outcome-risk-difference extremes with completely unknown binary outcomes.

    Does not claim that randomization occurred; not a confidence interval.
    """
    values=(n_t,observed_t,success_t,n_c,observed_c,success_c)
    if any(type(v) is not int for v in values):
        raise ValueError("integer participant counts required")
    if not (n_t>0 and n_c>0 and 0<=success_t<=observed_t<=n_t
            and 0<=success_c<=observed_c<=n_c):
        raise ValueError("inconsistent allocated/observed/success counts")
    lower=success_t/n_t-(success_c+n_c-observed_c)/n_c
    upper=(success_t+n_t-observed_t)/n_t-success_c/n_c
    observed_only=(success_t/observed_t-success_c/observed_c
                   if observed_t and observed_c else None)
    return {
        "evidence":"SYNTHETIC_BINARY_MISSING_OUTCOME_BOUND",
        "observed_only_difference":observed_only,
        "range_of_unobserved_binary_effect":[lower,upper],
        "treatment_missing":n_t-observed_t,
        "control_missing":n_c-observed_c,
        "not_a_confidence_interval":True,
        "not_real_human_causal_effect":True,
    }


def evaluate_benefit_harm_guard(benefit_state: str, harm_state: str,
                                consent: bool, independently_verified: bool) -> dict:
    """Conservative information gate; never grants authority to intervene."""
    allowed={"NOT_MEASURED","NO_HARM_OBSERVED","HARM_OBSERVED"}
    if harm_state not in allowed or benefit_state not in {
        "NOT_MEASURED","BENEFIT_OBSERVED","NO_BENEFIT_OBSERVED"}:
        raise ValueError("unsupported evidence label")
    reasons=[]
    if not consent:reasons.append("NO_CONSENT")
    if not independently_verified:reasons.append("NO_INDEPENDENT_OUTCOME")
    if benefit_state=="NOT_MEASURED":reasons.append("BENEFIT_NOT_MEASURED")
    if harm_state=="NOT_MEASURED":reasons.append("HARM_NOT_MEASURED")
    if harm_state=="HARM_OBSERVED":reasons.append("HARM_REQUIRES_STOP_REVIEW")
    if reasons:
        state="RESEARCH_HOLD"
    else:
        state="DESCRIPTIVE_EVIDENCE_ONLY"
    return {"status":state,"reasons":reasons,
            "live_intervention_authority":False,
            "causal_effect_identified":False}


def validate_claim_record(rec: dict) -> dict:
    """P12-3 scientific provenance contract, not peer review or legal advice."""
    fields={
        "claim_id","source_url","source_revision","experiment_evidence_level",
        "article_revision_sha256","outcome_type","supports_human_benefit",
        "explicit_limitations","language","publication_state"
    }
    if type(rec) is not dict or set(rec)!=fields:
        raise ValueError("missing or extra provenance field")
    if not all(isinstance(rec[x],str) and rec[x].strip() for x in
               ("claim_id","source_url","source_revision","outcome_type","language")):
        raise ValueError("required identifiers")
    if not rec["source_url"].startswith("https://"):
        raise ValueError("source must be an explicit HTTPS URL")
    if rec["experiment_evidence_level"] not in {
            "PUBLISHED_PRIOR_RESEARCH","SYNTHETIC_INTERNAL",
            "REAL_OBSERVATIONAL","RANDOMIZED_REAL_HUMAN","INDEPENDENT_REPLICATED"}:
        raise ValueError("unknown evidence level")
    if (type(rec["supports_human_benefit"]) is not bool
       or type(rec["explicit_limitations"]) is not str
       or not rec["explicit_limitations"].strip()):
        raise ValueError("limitations and benefit flag required")
    if (rec["experiment_evidence_level"]=="SYNTHETIC_INTERNAL"
            and rec["supports_human_benefit"]):
        raise ValueError("synthetic data cannot demonstrate human benefit")
    if rec["language"] not in ("ja","en"):
        raise ValueError("unsupported publication language")
    if rec["publication_state"] not in ("DRAFT","REVIEWED","LIVE_VERIFIED"):
        raise ValueError("invalid publication state")
    h=rec["article_revision_sha256"]
    if (not isinstance(h,str) or len(h)!=64
        or any(x not in "0123456789abcdef" for x in h)):
        raise ValueError("article content digest is required")
    return {"claim_id":rec["claim_id"],
            "claim_record_sha256":sha256(dumps(rec,sort_keys=True,
                               ensure_ascii=False).encode("utf8")).hexdigest(),
            "evidence_level":rec["experiment_evidence_level"],
            "independent_peer_review_proven":False}


def _valid_distribution(xs):
    if (not isinstance(xs,(list,tuple)) or len(xs)<2
        or any(type(x) not in (int,float) or not isfinite(x) or x<0 for x in xs)
        or abs(sum(xs)-1)>1e-9):
        raise ValueError("valid probability distribution required")


def js_divergence(p:list[float],q:list[float]) -> float:
    """Natural-log JSD; non-negative bounded by ln(2)."""
    _valid_distribution(p);_valid_distribution(q)
    if len(p)!=len(q):
        raise ValueError("distributions must have the same support")
    m=[(a+b)/2 for a,b in zip(p,q)]
    kl=lambda a,b:sum(x*log(x/y) for x,y in zip(a,b) if x>0)
    return (kl(p,m)+kl(q,m))/2


def brier_score(predictions:list[float], outcomes:list[int|None])->dict:
    """Never interpret pending outcomes as zero; coverage is mandatory."""
    if len(predictions)!=len(outcomes) or not predictions:
        raise ValueError("same nonempty length")
    if any(type(p) not in (int,float) or not isfinite(p) or not 0<=p<=1
           for p in predictions):
        raise ValueError("invalid prediction")
    if any(y is not None and y not in (0,1) for y in outcomes):
        raise ValueError("binary outcomes only")
    observed=[(p,y) for p,y in zip(predictions,outcomes) if y is not None]
    if not observed:
        return {"status":"PERFORMANCE_UNKNOWN","brier":None,
                "coverage":0.0,"not_a_causal_effect":True}
    value=sum((p-y)**2 for p,y in observed)/len(observed)
    return {"status":"PARTIAL_LABEL_COVERAGE" if len(observed)<len(outcomes)
                       else "OBSERVED_LABELS_ONLY",
            "brier":value,"coverage":len(observed)/len(outcomes),
            "not_a_causal_effect":True}


def model_update_proposal(*, rights_verified:bool, host_authority:bool,
                          baseline_better:bool, harm_stopped:bool,
                          evidence_complete:bool, budget_ok:bool)->dict:
    """P12-4 research gate: suggestion ONLY, never production deployment."""
    conditions={
        "RIGHTS":rights_verified,
        "HOST_AUTHORITY":host_authority,
        "MODEL_BASELINE":baseline_better,
        "NO_HARM_STOP":not harm_stopped,
        "EVIDENCE_COMPLETE":evidence_complete,
        "BUDGET":budget_ok,
    }
    missing=[name for name,ok in conditions.items() if not ok]
    return {
      "status":"REJECTED" if missing else "RESEARCH_CANDIDATE_ONLY",
      "failed_checks":missing,
      "production_deployed":False,
      "automatic_human_intervention":False,
      "source":"SYNTHETIC_EDUCATIONAL_POLICY",
    }


def synthetic_demo()->dict:
    toy={
        "P12-2":attrition_binary_effect_bounds(100,80,60,100,90,54),
        "P12-3":validate_claim_record({
            "claim_id":"P12-3-EXAMPLE-001",
            "source_url":"https://www.bmj.com/content/389/bmj-2024-081123",
            "source_revision":"2025-04-14",
            "experiment_evidence_level":"SYNTHETIC_INTERNAL",
            "article_revision_sha256":"a"*64,
            "outcome_type":"EDUCATIONAL_CASE_ONLY",
            "supports_human_benefit":False,
            "explicit_limitations":"Not a real human trial or actual manuscript",
            "language":"ja","publication_state":"DRAFT"
        }),
        "P12-4":{
            "two_bin_jsd":js_divergence([.5,.5],[.9,.1]),
            "same_distribution_jsd":js_divergence([.5,.5],[.5,.5]),
            "delayed_labels":brier_score([.9,.2,.7],[1,None,0]),
            "unmeasured_labels":brier_score([.9,.2],[None,None]),
            "update":model_update_proposal(rights_verified=True,host_authority=True,
                baseline_better=True,harm_stopped=False,evidence_complete=True,
                budget_ok=True)
        },
    }
    toy["all_examples_synthetic"]=True
    toy["real_user_benefit"]="NOT_MEASURED"
    toy["real_software_deployment"]="NOT_PERFORMED"
    return toy


if __name__=="__main__":
    print(dumps(synthetic_demo(),ensure_ascii=False,indent=2,sort_keys=True))
