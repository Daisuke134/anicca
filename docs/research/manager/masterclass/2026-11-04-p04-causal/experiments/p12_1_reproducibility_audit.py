"""P12-1: third-party-ready reproducibility audit for P11 synthetic claims.

Pure-standard-library evidence package. Does NOT verify any real human result,
make a public-research reproduction claim, or train/serve a foundation model.

Key distinctions:
- Same authors running their own code => REPEATABILITY (not independent replication).
- Alternate formula/estimator against frozen synthetic data => within-team cross-check.
- External reviewers and independent data have NOT been involved.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import fsum, log
from pathlib import Path
from random import Random
from statistics import mean
import json
import platform
from typing import Iterable, Mapping

PINNED_P11_COMMIT = "0c236f249ac4503764770135a86e2026cd37fec9"
PINNED_P11_SOURCE_SHA256 = "4a3c76b12f7423c575af526a35906e6d7d1ac2b5f6ef9d1b1db895c6a91f4818"

from p11_1_5_research_labs import (
    synthetic_contextual_log,
    p11_1_demo,
    synthetic_two_domain_choices,
    p11_4_demo,
    logistic_log_loss,
)


def canonical_json_bytes(value: object) -> bytes:
    """Deterministic serialization for portable content hashes."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: object) -> str:
    return sha256(canonical_json_bytes(value)).hexdigest()


def robust_mean(values: Iterable[float]) -> float:
    seq = list(values)
    if not seq:
        raise ValueError("nonempty observations required")
    return fsum(seq) / len(seq)


def alternative_ope(rows, target_p1: Mapping[int, float]) -> dict:
    """Re-derive IPS/SNIPS/DR WITHOUT invoking P11's evaluation implementation.

    Uses only source trial records plus independent target policy and
    reference outcome probabilities. This is an author-made verification,
    not an unrelated third-party replication.
    """
    if not rows:
        raise ValueError("empty rows")
    reward_table = {
        (0, 0): .20, (0, 1): .40,
        (1, 0): .35, (1, 1): .75
    }
    weights, weighted_rewards, dr_items, direct_items = [], [], [], []
    for row in rows:
        x, action, y = row.context, row.action, row.reward
        if x not in (0, 1) or action not in (0, 1):
            raise ValueError("unrecognized synthetic context or action")
        if not 0 <= y <= 1 or not 0 < row.logged_propensity <= 1:
            raise ValueError("invalid propensity or outcome")
        p = target_p1[x] if action == 1 else (1 - target_p1[x])
        w = p / row.logged_propensity
        q = reward_table[(x, action)]
        qpi = (1 - target_p1[x]) * reward_table[(x, 0)] + target_p1[x] * reward_table[(x, 1)]
        weights.append(w)
        weighted_rewards.append(w * y)
        direct_items.append(qpi)
        dr_items.append(qpi + w * (y - q))
    n = len(rows)
    return {
        "n": n, "ips": fsum(weighted_rewards) / n,
        "snips": fsum(weighted_rewards) / fsum(weights),
        "dr": fsum(dr_items) / n,
        "direct": fsum(direct_items) / n,
        "effective_sample_size": fsum(weights)**2 / fsum(w*w for w in weights),
        "method": "INDEPENDENT_FORMULA_SAME_AUTHOR_AND_SYNTHETIC_DATA",
    }


def frozen_bandit_inputs(seed: int = 1101, n: int = 20000) -> dict:
    """Canonical public toy records, never sensitive participant records."""
    rows = synthetic_contextual_log(n=n, seed=seed)
    # preserve relevant fields only, and hash dataset content as canonical bytes
    payload = [
        {"x": x.context, "a": x.action, "r": x.reward,
         "logging_p": x.logged_propensity} for x in rows
    ]
    return {
        "name": "P11 synthetic 2-context contextual bandit",
        "sha256": digest(payload),
        "rows": n,
        "seed": seed,
        "generator": "p11_1_5_research_labs.synthetic_contextual_log",
        "license": "self-authored synthetic example; no real-person data",
        "records": payload,
    }


def alternate_logistic_mle(rows: list[tuple[float, int]]) -> tuple[float, float]:
    """Closed-form two-bin log-odds, NOT P11 gradient descent.

    For x in {-1, +1}, the unregularized logistic MLE may be obtained
    from the observed success fraction per group. Jeffreys 0.5 smoothing
    keeps extreme small samples finite; large samples approximate MLE.
    """
    bins = {-1: [], 1: []}
    for x, y in rows:
        if x not in bins or y not in (0, 1):
            raise ValueError("binary symmetric features/labels only")
        bins[x].append(y)
    if not all(bins.values()):
        raise ValueError("both x bins required")
    logits = {}
    for x, ys in bins.items():
        k, n = sum(ys), len(ys)
        p = (k + 0.5) / (n + 1)
        logits[x] = log(p / (1 - p))
    return (logits[1] + logits[-1]) / 2, (logits[1] - logits[-1]) / 2


def alternate_negative_transfer(seed: int = 1104) -> dict:
    data = synthetic_two_domain_choices(n_per_domain=400, seed=seed)
    tr = {k: v[:300] for k, v in data.items()}
    te = {k: v[300:] for k, v in data.items()}
    pooled = alternate_logistic_mle(tr["A"] + tr["B"])
    specialists = {k: alternate_logistic_mle(tr[k]) for k in tr}
    return {
        "seed": seed,
        "pooled": {k: logistic_log_loss(te[k], pooled) for k in te},
        "specialists": {k: logistic_log_loss(te[k], specialists[k]) for k in te},
        "alternate_fit": "smoothed_group_logit_closed_form",
        "same_source_generator": True,
        "actual_trained_shared_bfm": False,
    }


def group_holdout_integrity(records: list[dict], training: list[int],
                            testing: list[int], group_field: str) -> dict:
    """Fail closed on row reuse and group leakage; no claim of data rights."""
    if not training or not testing:
        raise ValueError("nonempty train/test required")
    if any(type(i) is not int or i < 0 or i >= len(records) for i in training + testing):
        raise ValueError("invalid row index")
    if len(set(training)) != len(training) or len(set(testing)) != len(testing):
        raise ValueError("duplicate row indices")
    overlap_row = set(training) & set(testing)
    group_train = {records[i].get(group_field) for i in training}
    group_test = {records[i].get(group_field) for i in testing}
    if None in group_train or None in group_test:
        raise ValueError("missing group identity")
    group_overlap = group_train & group_test
    if overlap_row or group_overlap:
        raise ValueError(f"LEAKAGE: row={len(overlap_row)} group={len(group_overlap)}")
    return {
        "disjoint_rows": True, "disjoint_groups": True,
        "training_groups": sorted(group_train),
        "testing_groups": sorted(group_test),
        "evaluation_grain": group_field,
    }


def artificial_group_split_demo() -> dict:
    """Repeated observations per synthetic person/study; row split leaks."""
    rows = [
        {"person": f"person-{i//3}", "study": f"study-{i//9}",
         "y": int((i//3) % 2)}
        for i in range(36)
    ]
    # row-wise 3 visits of each synthetic subject in both sets
    naive_training = [i for i in range(36) if i % 3 != 2]
    naive_testing = [i for i in range(36) if i % 3 == 2]
    try:
        group_holdout_integrity(rows, naive_training, naive_testing, "person")
    except ValueError:
        naive_outcome = "REJECTED_PERSON_LEAKAGE"
    else:
        raise AssertionError("expected repeated-person leakage")
    study_train = list(range(27))
    study_test = list(range(27, 36))
    study_good = group_holdout_integrity(rows, study_train, study_test, "study")
    return {
        "data_kind": "SYNTHETIC_ONLY",
        "row_wise_split": naive_outcome,
        "study_holdout": study_good,
        "no_human_data": True,
    }


def validate_benchmark_card(card: Mapping[str, object]) -> None:
    """Minimum metadata schema for an auditable claim, NOT legal permission."""
    required = {
        "claim_id", "kind", "dataset_revision_sha256", "code_commit_sha",
        "model_revision", "split_unit", "train_groups", "test_groups",
        "metric", "metric_direction", "sample_count", "seeds",
        "baseline", "license_status", "raw_outcome_status",
        "human_outcome_claim", "evaluation_time_cutoff"
    }
    if set(card) != required:
        raise ValueError("missing/extra benchmark-card fields")
    if card["kind"] != "SYNTHETIC" or card["human_outcome_claim"] is not False:
        raise ValueError("toy audit may never claim human efficacy")
    if (not isinstance(card["dataset_revision_sha256"], str)
            or len(card["dataset_revision_sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in card["dataset_revision_sha256"])):
        raise ValueError("invalid dataset SHA")
    if (not isinstance(card["code_commit_sha"], str)
            or len(card["code_commit_sha"]) != 40
            or any(ch not in "0123456789abcdef" for ch in card["code_commit_sha"])):
        raise ValueError("invalid source commit SHA")
    if card["metric_direction"] not in ("higher", "lower"):
        raise ValueError("metric direction required")
    if (card["raw_outcome_status"] != "SYNTHETIC_NO_HUMAN_DATA"
            or card["license_status"] != "SELF_AUTHORED_SYNTHETIC"):
        raise ValueError("unsupported evidence/license status")
    if (not isinstance(card["sample_count"], int) or card["sample_count"] < 1
            or not isinstance(card["seeds"], list) or not card["seeds"]):
        raise ValueError("invalid number of cases/seeds")
    if set(card["train_groups"]) & set(card["test_groups"]):
        raise ValueError("group-leaked split is not releasable")
    for label in ("claim_id","split_unit","metric","model_revision","baseline","evaluation_time_cutoff"):
        if not isinstance(card[label], str) or not card[label].strip():
            raise ValueError("missing name or cutoff")


def seed_variance_report(seeds=tuple(range(1101, 1111)), n=3000) -> dict:
    vals=[]
    for seed in seeds:
        rows=synthetic_contextual_log(n, seed=seed)
        result=alternative_ope(rows,{0:.2,1:.7})
        vals.append(result["dr"])
    center=robust_mean(vals)
    # This is descriptive SE across independent synthetic seeds, not a
    # participant-cluster confidence interval or a confidence bound for humans.
    std=(fsum((x-center)**2 for x in vals)/(len(vals)-1))**.5 if len(vals)>1 else 0.
    return {"seeds":list(seeds),"n_per_seed":n,"seed_dr_values":vals,
            "mean_dr":center,"between_seed_sd":std,
            "uncertainty_claim":"DESCRIPTIVE_SIMULATED_SEED_VARIATION_NOT_REAL_HUMAN_CI"}


def run_audit(source_commit_sha: str) -> dict:
    if not isinstance(source_commit_sha, str) or len(source_commit_sha)!=40 or any(x not in "0123456789abcdef" for x in source_commit_sha):
        raise ValueError("full source commit SHA required")
    if source_commit_sha != PINNED_P11_COMMIT:
        raise ValueError("source commit must equal immutable original P11 reference")
    actual_source=sha256(Path(__file__).with_name("p11_1_5_research_labs.py").read_bytes()).hexdigest()
    if actual_source != PINNED_P11_SOURCE_SHA256:
        raise ValueError("original P11 source byte hash mismatch; not a reproducible replay")
    old=p11_1_demo()
    trials=frozen_bandit_inputs()
    alt=alternative_ope(synthetic_contextual_log(),{0:.2,1:.7})
    # Use tolerance for floating-point summation order ONLY
    delta={"ips":abs(old["ips"]-alt["ips"]),
           "snips":abs(old["snips"]-alt["snips"]),
           "dr":abs(old["doubly_robust"]-alt["dr"])}
    if any(d>1e-10 for d in delta.values()):
        raise AssertionError("independent arithmetic disagrees with P11")
    orig=p11_4_demo()
    closed=alternate_negative_transfer()
    for domain in ("A","B"):
        if (not closed["specialists"][domain] < closed["pooled"][domain]
                or abs(orig["specific_test_logloss"][domain] - closed["specialists"][domain]) > .03
                or abs(orig["pooled_test_logloss"][domain] - closed["pooled"][domain]) > .03):
            raise AssertionError("alternate fit did not reproduce toy negative transfer")
    group_demo=artificial_group_split_demo()
    card={
        "claim_id":"P12-1-SYNTHETIC-BANDIT-OPE-V1",
        "kind":"SYNTHETIC",
        "dataset_revision_sha256":trials["sha256"],
        "code_commit_sha":source_commit_sha,
        "model_revision":"toy-conditional-probabilities-v1",
        "split_unit":"synthetic_decision",
        "train_groups":["source-sim-train"],
        "test_groups":["source-sim-heldout"],
        "metric":"DR_reward_value",
        "metric_direction":"higher",
        "sample_count":20000,
        "seeds":[1101],
        "baseline":"oracle known from data generating process",
        "license_status":"SELF_AUTHORED_SYNTHETIC",
        "raw_outcome_status":"SYNTHETIC_NO_HUMAN_DATA",
        "human_outcome_claim":False,
        "evaluation_time_cutoff":"synthetic-seed-1101"
    }
    validate_benchmark_card(card)
    return {
        "report_schema":"manager.p12-1.same-author-repro-audit.v1",
        "evidence_level":"SAME_AUTHOR_ALTERNATE_CALCULATION",
        "external_independent_reviewer":"NOT_PERFORMED",
        "real_human_study_replication":"NOT_PERFORMED",
        "actual_shared_BFM_training":"NOT_PERFORMED",
        "source_commit_sha":source_commit_sha,
        "source_code_sha256":actual_source,
        "p11_bandit_replay":{"dataset_hash_sha256":trials["sha256"],
                             "reference_ips":old["ips"],"alternate_ips":alt["ips"],
                             "reference_dr":old["doubly_robust"],"alternate_dr":alt["dr"],
                             "maximum_numeric_difference":max(delta.values()),
                             "synthetic_oracle":old["oracle_population_value"]},
        "p11_negative_transfer_alternate_fit":{
            "alternate":closed,"p11_gradient_descent_reference":orig
        },
        "synthetic_group_leakage_check":group_demo,
        "synthetic_seed_variance":seed_variance_report(),
        "benchmark_card":card,
        "limits":["No real human data accessed","No third-party reproduction",
                  "No actual model weights trained","No commercial use of gated datasets",
                  "No live intervention, account mutation, money transfer or paid API",
                  "No published ACM badge, no final scientific peer review"],
    }


if __name__ == "__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-sha",required=True,
                        help="immutable 40-char commit SHA of original P11 code")
    args=parser.parse_args()
    print(json.dumps(run_audit(args.source_sha),indent=2,ensure_ascii=False,sort_keys=True))
