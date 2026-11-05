"""P06-5: real provenance and *honest* experiment proof cards.

The objective is to refuse false business/welfare claims when only synthetic
simulation or public-site delivery evidence exists. We reuse existing
Manager Core's public served-bundle reader and verifier.

Proof levels in this specific report:
 - research fixture: synthetic RCT/calculation, cannot claim real-world impact
 - public delivery: independently GET current public website + verified manifest,
   verifies delivery/status only (NOT paid business or human behavioral outcome)
 - causal field benefit: requires actual, independent real outcomes + real
   comparator/randomization; absent in this run -> NOT_MEASURED

No production writes, no private logs, no credentials, no survey recruitment.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Optional
import json
import sys

REPO=Path(__file__).resolve().parents[6]
sys.path.insert(0,str(REPO/"products/manager"))
from manager_core.owned_catalog_planner import _read_served_bundle
from manager_core.digital_environment import verify_readback

from p06_2_whatif_ablation import fingerprint as fingerprint_p062
from p06_3_trial_design import sha as sha_p063
from p06_4_incremental_value import checksum as sha_p064

EVIDENCE=REPO/"docs/research/manager/masterclass/2026-11-04-p04-causal/evidence"
PUBLIC_BASE="https://daisuke134.github.io/life-manager/manager-support/"


def sha_file(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def verify_chain(out:Path)->dict:
    """Fail closed on corrupted freeze, plan and result. No generated signatures."""
    required=[
        "P06-2_PREANALYSIS_SYNTHETIC.json",
        "P06-2_POLICY_FREEZE_SYNTHETIC.json",
        "P06-2_SYNTHETIC_ABLATION_RESULTS.json",
        "P06-3_PREANALYSIS_DESIGN_SYNTHETIC.json",
        "P06-3_PLAN_FREEZE_SYNTHETIC.json",
        "P06-3_POWER_AND_STOPPING_RESULTS.json",
        "P06-4_PREANALYSIS_SYNTHETIC.json",
        "P06-4_PREANALYSIS_FREEZE.json",
        "P06-4_INCREMENTAL_VALUE_SYNTHETIC_RESULTS.json",
    ]
    if any(not (out/name).is_file() for name in required):
        raise ValueError("evidence chain is incomplete")
    data={name:json.loads((out/name).read_text(encoding="utf-8"))
          for name in required}
    plan2=data[required[0]];freeze2=data[required[1]];result2=data[required[2]]
    plan3=data[required[3]];freeze3=data[required[4]];result3=data[required[5]]
    plan4=data[required[6]];freeze4=data[required[7]];result4=data[required[8]]
    if not (
        fingerprint_p062(plan2)==freeze2["plan_sha256"]
        ==result2["frozen_plan_sha256"]
        and fingerprint_p062(freeze2["whatif_policy"])==
        freeze2["policy_hashes"]["whatif"]
        and fingerprint_p062(freeze2["baseline_policy"])==
        freeze2["policy_hashes"]["baseline"]
        and freeze2["policy_hashes"]==result2["frozen_policy_sha256"]
        and sha_p063((out/required[3]).read_bytes())==
        freeze3["plan_sha256"]==result3["plan_sha256"]
        and sha_p064((out/required[6]).read_bytes())==
        freeze4["sha256"]==result4["plan_sha256"]
    ):
        raise ValueError("plan or frozen policy hashes disagree")
    if any(bool(x.get("real_trial_registered",False)) or
           bool(x.get("actual_real_participants",0))
           for x in (result2,result3,result4)):
        raise ValueError("synthetic document incorrectly claims real participants")
    return {
        "n_verified_artifacts":len(required),
        "sha256_by_filename":{name:sha_file(out/name) for name in required},
        "study_ids":[result2["study_id"], result3["phase"],result4["study"]],
        "plan_hashes_match_frozen_results":True,
        "code_outputs_are_synthetic":True,
        "real_causal_field_claim_supported":False,
    }


def public_website_evidence(reader=_read_served_bundle) -> dict:
    """Read published public proof with existing source-independent fetch."""
    try:
        manifest,bodies,manifest_raw=reader()
        verify_readback(manifest,bodies)
        if json.loads(manifest_raw)!=manifest:
            raise ValueError("public manifest raw bytes differ from parsed payload")
        return {
            "status":"PUBLIC_SITE_DELIVERY_READBACK_VERIFIED",
            "source": PUBLIC_BASE,
            "observation_utc":datetime.now(timezone.utc).isoformat(),
            "source_commit":manifest.get("source_commit"),
            "manifest_sha256":sha256(manifest_raw).hexdigest(),
            "verified_html_page_count":len(bodies),
            "experiment_enabled":manifest.get("experiment_enabled"),
            "real_participants":manifest.get("real_participants"),
            "beneficiary_outcome":manifest.get("beneficiary_outcome"),
            "real_intervention_effect":None,
            "inference":"technical availability only; no proof of improved user welfare or profit",
        }
    except Exception as exc:
        return {
            "status":"UNVERIFIED_PUBLIC_READBACK",
            "source":PUBLIC_BASE,
            "error_type":type(exc).__name__,
            "real_intervention_effect":None,
            "inference":"No public-site confirmation; cannot claim availability",
        }


def evidence_card(verified:dict, sample3:dict,
                  profit4:dict, public:dict)->dict:
    """No real outcome is ever auto-populated from simulated business figures."""
    causal=profit4["real_financial_outcome"]
    if causal["status"]!="NOT_MEASURED_MISSING_VERIFIED_RECEIPTS":
        raise ValueError("unexpected real-world benefit claim")
    guarded=profit4["toy_strict_ship_gate"]
    if guarded["decision"]!="DO_NOT_SHIP":
        raise ValueError("synthetic safety guardrail unexpectedly accepted")
    if not verified["plan_hashes_match_frozen_results"]:
        raise ValueError("missing frozen provenance")
    proof={
        "card_schema":"manager.p06.proof-card.v0.1",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "research_synthetic":{
            "plan_and_artifact_hashes_verified":verified["n_verified_artifacts"],
            "three_reproducible_educational_studies":True,
            "P06_3_fixed_sample_per_arm":sample3["power"]["fixed_horizon_n_per_arm"],
            "P06_3_AA_four_naive_false_positive":sample3["AA_early_stopping"]["naive_any_of_four_looks_false_positive"],
            "P06_4_toy_incremental_contribution_yen_per_assignment":
                profit4["metrics"]["net_contribution"]["diff"],
            "P06_4_toy_CI95":profit4["metrics"]["net_contribution"]["ci95"],
            "P06_4_toy_complaint_worsening_rate":
                profit4["metrics"]["complaint"]["diff"],
            "P06_4_decision":guarded["decision"],
            "not_real_users":True,
        },
        "technical_real_world_observation":public,
        "actual_business":{
            "payment_provider_receipt":None,
            "reconciled_paid_revenue_yen":None,
            "refunds_verified":None,
            "model_cost_observed":None,
            "control_arm_or_other_valid_counterfactual":None,
            "net_incremental_profit_yen":None,
            "status":"NOT_MEASURED",
        },
        "actual_human_behavior":{
            "real_study_participants":0,
            "validated_behavior_change_outcome":None,
            "rumination_change":None,
            "independent_comparator":None,
            "adverse_event_monitoring":None,
            "status":"NOT_MEASURED",
        },
        "release_decision":{
            "field_effect_confident":False,
            "can_claim_real_business_uplift":False,
            "can_claim_reduced_rumination":False,
            "new_production_action_authorized":False,
            "status":"HOLD_NO_VERIFIED_CAUSAL_FIELD_RESULTS",
            "blockers":[
                "no independently verified real paid revenue/refunds/costs",
                "no real randomized or otherwise identified comparison",
                "no opt-in participant outcome and harm measurements",
                "no authentic live action grant or P05-5 S1/S2 admission",
            ],
        },
    }
    return proof


def run(out:Path=EVIDENCE, *, reader=_read_served_bundle) -> dict:
    out.mkdir(parents=True,exist_ok=True)
    hashes=verify_chain(out)
    third=json.loads((out/"P06-3_POWER_AND_STOPPING_RESULTS.json").read_text())
    fourth=json.loads((out/"P06-4_INCREMENTAL_VALUE_SYNTHETIC_RESULTS.json").read_text())
    public=public_website_evidence(reader=reader)
    card=evidence_card(hashes,third,fourth,public)
    (out/"P06-5_EVIDENCE_CHAIN_AUDIT.json").write_text(
        json.dumps(hashes,ensure_ascii=False,indent=2)+"\n")
    (out/"P06-5_PROOF_CARD_RESEARCH_AND_REAL_WORLD.json").write_text(
        json.dumps(card,ensure_ascii=False,indent=2)+"\n")
    return {"chain":hashes,"proof_card":card}


if __name__=="__main__":
    result=run()
    card=result["proof_card"]
    print(json.dumps({
        "all_artifacts_verified":result["chain"]["n_verified_artifacts"],
        "public_readback":card["technical_real_world_observation"]["status"],
        "real_business_impact":card["actual_business"]["status"],
        "real_human_impact":card["actual_human_behavior"]["status"],
        "release_decision":card["release_decision"]["status"],
    },ensure_ascii=False,indent=2))
