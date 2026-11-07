"""G1 ManagerBench v1: read-only, multi-task, provenance-checked evaluation ledger.

This is an orchestrating contract around real published *aggregate* human
outcomes, not a universal benchmark score, individual-person model, live
intervention, or a newly inferred GPT answer. It fails on unpinned source
changes, invalid cohort or split, and nonfinite metrics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

NATURE_HASH = "b51b86c03639728b39c713c815ec22b6daabf3383163efa70fd54366944a6214"
MAME_SCORE_HASH = "aad13533093fe9d2fcf80d0299c1abcaf751d3016e7d897b37604924abf56568"
HBCP_HASH = "eec4ba6ffc51961fda1308f690a97a60111d93858fa67ca19ffd4392fd49679b"
QWEN_GGUF_HASH = "2fde00ce69dd4899c70d020845e2638353015bba0fdf161b3eb965f2bca4464e"
ROOT = Path(__file__).resolve().parents[3]
NATURE_PATH = ROOT / "docs/research/manager/masterclass/2026-11-04-p04-causal/evidence/P09-1_NATURE_FIG1_RESULT_20261107.json"
P09_PATH = ROOT / "docs/research/manager/masterclass/2026-11-04-p04-causal/evidence/P09-2_TO_P09-5_REAL_TWO_DOMAIN_EVAL_20261107.json"


def _finite(value: Any, *, low: float = 0., high: float = float("inf")) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("invalid metric type")
    number = float(value)
    if not math.isfinite(number) or not low <= number <= high:
        raise ValueError("invalid metric value")
    return number


def _track(task_id: str, unit: str, *,
           baseline: float, candidate: float, n_groups: int,
           lower_is_better: bool, source_sha256: str,
           split: str, evidence: str, statement: str) -> dict:
    if len(source_sha256) != 64 or any(c not in "0123456789abcdef" for c in source_sha256):
        raise ValueError("invalid dataset digest")
    base = _finite(baseline)
    model = _finite(candidate)
    if type(n_groups) is not int or n_groups < 1:
        raise ValueError("missing evaluated groups")
    delta = (base - model) if lower_is_better else (model - base)
    return {
        "task_id":task_id, "unit":unit,
        "source_sha256":source_sha256,
        "split":split, "n_groups":n_groups,
        "baseline":base, "candidate":model,
        "lower_is_better":lower_is_better,
        "delta":delta,
        "status":"EXPLORATORY_IMPROVEMENT" if delta > 0 else "NOT_DEMONSTRATED",
        "evidence_kind":evidence, "scientific_boundary":statement,
    }


def build_report(nature: dict, p09: dict, hbcp: dict, qwen: dict | None = None) -> dict:
    """Validate four distinct outcome scales. Never compute pooled accuracy."""
    if not all(isinstance(v, dict) for v in (nature,p09,hbcp)):
        raise ValueError("missing benchmark receipts")
    checks=p09.get("input_checksums_sha256",{})
    if (nature.get("normalized_csv_sha256") != NATURE_HASH
            or checks.get("nature_panelA_normalized_csv") != NATURE_HASH
            or checks.get("mame_re_score.csv") != MAME_SCORE_HASH):
        raise ValueError("Nature/MaMe source hash mismatch")
    if (nature.get("study_count")!=70 or
            p09.get("nature_fig1",{}).get("n_studies")!=70 or
            nature.get("original_codeocean_RDS_rerun") is not False):
        raise ValueError("incorrect Nature provenance or scope")

    p2=p09["p09_2_fewshot_study_effect_adaptation"]
    if (p2.get("eligible_studies") != 36 or
            p2["results"]["partial_pool_k5"]["n_study_folds"] != 36):
        raise ValueError("few-shot eligible studies mismatch")
    t2=_track(
        "nature_effect", "fractional_treatment_effect_RMSE",
        baseline=p2["results"]["raw"]["rmse_micro"],
        candidate=p2["results"]["partial_pool_k5"]["rmse_micro"],
        n_groups=36, lower_is_better=True,source_sha256=NATURE_HASH,
        split="LOSO 69 train studies + 1 heldout; k5 target support/query different",
        evidence="published_GPT4_effects_then_study_calibration",
        statement="Published Figure1 aggregate effect contrasts; original RDS not replayed; macro bootstrap compares global calibrated vs k5 only.")

    meme=p09["p09_5_meme_distinct_task_holdout"]
    tr,valid,te=(meme.get(x) for x in ("train_ids","validation_ids","test_ids"))
    if not all(isinstance(x,list) for x in (tr,valid,te)):
        raise ValueError("missing fixed context split")
    if ([len(tr),len(valid),len(te)]!=[160,40,50]
            or sorted(tr+valid+te)!=list(range(250))
            or meme.get("n_aggregate_pairs")!=100000
            or meme.get("test_aggregate_pairs")!=20000):
        raise ValueError("invalid split or target cardinality")
    mm=meme["metrics"]
    t5=_track(
        "mame_rating","fractional_5vote_funniness_RMSE",
        baseline=mm["image_historical_mean"]["rmse"],
        candidate=mm["text_context_description_ridge"]["rmse"],
        n_groups=50,lower_is_better=True,source_sha256=MAME_SCORE_HASH,
        split="disjoint Japanese context IDs: 160 train / 40 validation / 50 test",
        evidence="published_human_5vote_aggregate_new_ridge",
        statement="No manga image/dialogue; historical item mean performs slightly better; no individual laughing-person prediction.")

    if (hbcp.get("sha256")!=HBCP_HASH or hbcp.get("n_studies")!=405
            or hbcp.get("n_trial_arms")!=971 or hbcp.get("n_numeric_features")!=93
            or "study" not in hbcp.get("study_holdout","")
            or sum(f.get("n_test_arms",0) for f in hbcp.get("folds",[]))!=971
            or len(hbcp.get("folds",[]))!=5):
        raise ValueError("invalid HBCP source/split/fold audit")
    hm=hbcp["train_mean"]
    hc=hbcp["ridge_alpha30"]
    for rec in (hm,hc):
        if rec.get("n")!=971:
            raise ValueError("invalid HBCP arm count")
    t3=_track(
        "hbcp_quit_rate","smoking_cessation_arm_rate_MAE_percentage_points",
        baseline=hm["mae"],candidate=hc["mae"],
        n_groups=405,lower_is_better=True,source_sha256=HBCP_HASH,
        split="five-fold study-disjoint with train-only imputation",
        evidence="published_study_arm_aggregate_regression",
        statement="Study bootstrap CI includes zero, so observed +0.062pp improvement not established as reliable; no individual treatment effects.")
    ci=hbcp.get("study_cluster_bootstrap_95ci_mae_improvement")
    if not isinstance(ci,list) or len(ci)!=2 or _finite(ci[1],low=-1000,high=1000)<_finite(ci[0],low=-1000,high=1000):
        raise ValueError("HBCP confidence interval invalid")
    if ci[0]<=0<=ci[1]:
        t3["status"]="NOT_DEMONSTRATED"

    tracks=[t2,t5,t3]
    if qwen is not None:
        if not isinstance(qwen,dict):
            raise ValueError("invalid optional model receipt")
        score=qwen.get("scores",{})
        if (qwen.get("status")!="REAL_QWEN3_4B_CPU_TEXT_ONLY_HUMAN_AGGREGATE_EVAL"
                or qwen.get("model_forward_pass_executed") is not True
                or qwen.get("model_sha256")!=QWEN_GGUF_HASH
                or qwen.get("n_cases")!=24
                or qwen.get("file_sha256",{}).get("score.csv")!=MAME_SCORE_HASH
                or score.get("n_total")!=24 or score.get("n_human_non_tied")!=18
                or score.get("n_ties")!=6 or score.get("n_model_invalid")!=0):
            raise ValueError("invalid Qwen real-forward human evaluation provenance")
        t4=_track(
            "mame_qwen_pairwise","human_5vote_pairwise_proxy_strict_accuracy",
            baseline=_finite(score["baseline_strict_win_accuracy"],low=0,high=1),
            candidate=_finite(score["model_strict_win_accuracy_including_invalid"],low=0,high=1),
            n_groups=18,lower_is_better=False,source_sha256=MAME_SCORE_HASH,
            split="24 frozen heldout contexts; 6 human rating ties; 18 comparable",
            evidence="real_qwen3_4b_gguf_forward_and_human_aggregate",
            statement="Separate independent five-vote ratings, NOT direct pairwise human judgments; no image understanding and pilot is small.")
        tracks.append(t4)

    return {
        "schema":"managerbench.v1",
        "source_provenance":"pinned official research result receipts; independently rerunnable via linked scripts",
        "tracks":tracks,
        "global_accuracy":None,
        "global_score_prohibited":True,
        "all_tracks_better_than_baseline":all(t["delta"]>0 for t in tracks),
        "shared_behavior_foundation_model_trained":False,
        "prospective_human_intervention":False,
        "product_benefit_measured":False,
        "no_test_label_train_leakage_claim":"study/context split asserted by original scripts; detailed row identity not independently encoded in every receipt",
    }


def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--nature",type=Path,default=NATURE_PATH)
    p.add_argument("--p09",type=Path,default=P09_PATH)
    p.add_argument("--hbcp",type=Path)
    p.add_argument("--qwen",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--bootstrap-reps",type=int,default=400)
    a=p.parse_args()
    nature=json.loads(a.nature.read_text())
    p09=json.loads(a.p09.read_text())
    if a.hbcp is None:
        from hbcp_study_disjoint_lightweight import run
        hbcp=run(reps=a.bootstrap_reps)
    else:
        hbcp=json.loads(a.hbcp.read_text())
    qwen=json.loads(a.qwen.read_text()) if a.qwen else None
    result=build_report(nature,p09,hbcp,qwen)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
    print(json.dumps({
        "status":"SOURCE_BACKED_MULTI_TASK_REPORT",
        "tracks":[{"name":t["task_id"],"baseline":t["baseline"],"candidate":t["candidate"],"status":t["status"]} for t in result["tracks"]],
        "no_global_metric":True,
        "output":str(a.output)},ensure_ascii=False))


if __name__=="__main__":
    main()
