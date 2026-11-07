"""Research-only HeartSteps V1 2019 randomized-selection audit.

The public 'is.randomized' flag means a decision time was randomly selected
(GitHub study wiki), whereas 'send' is post-decision corrected delivery.
We compare binary selected vs not selected conditional on availability.

IMPORTANT: source Fig./paper cohort=6061; accessible strict public-index cohort
is not identical. Three-arm randomized subtype is not reconstructed, so this
is NOT an exact reproduction of published causal effects or original GEE/WCLS.

Only aggregate results are emitted; no raw participant rows are saved.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Mapping


from heartsteps_v1_real_mrt import (
    SOURCE_SHA256, SOURCE_URL, load_pinned_source,
)

SOURCE_WIKI = "https://github.com/klasnja/HeartStepsV1/wiki/Documentation-for-suggestions.csv"
ORIGINAL_PAPER = "https://doi.org/10.1093/abm/kay067"
P_ASSIGNED = 0.6
PAPER_AVAILABLE = 6061
FIELD_NAMES = (
    "user.index", "decision.index.nogap", "avail", "is.randomized",
    "send", "jbsteps30.zero", "jbsteps30pre.zero",
)


def _flag(value: str) -> bool:
    if value in ("True", "TRUE", "true", "1"):
        return True
    if value in ("False", "FALSE", "false", "0"):
        return False
    raise ValueError("missing or invalid randomized-selection/delivery flag")


def _number(value: str) -> float:
    try:
        ans = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("missing or nonnumeric zero-imputed step outcome") from exc
    if not math.isfinite(ans) or ans < 0:
        raise ValueError("nonfinite or negative step count")
    return ans


def reconstruct_author_cohort(rows: list[Mapping[str, str]]) -> tuple[list[dict], dict]:
    """Rebuild the paper's reported 7,540 decision-point cohort from public CSV.

    Primary authors excluded 390 corrupt/travel decisions, 340 beyond their
    first 42 *local study days* (excluding gap days), and four anomalous
    records. Published source code documents the anomaly conditions:
    (avail == FALSE & send == TRUE) or missing send.active.
    An undated first unavailable decision is preserved by its non-gap index.
    The final *counts* can be audited against the original paper without
    claiming exact original GEE/WCLS rows or adjusted treatment effects.
    """
    if not rows:
        raise ValueError("no rows")
    needed = {
        "user.index", "decision.index.nogap", "sugg.select.utime",
        "sugg.gmtoff", "avail", "send", "send.active",
        "send.sedentary", "is.randomized",
    }
    if not needed.issubset(rows[0]):
        raise ValueError("missing original HeartSteps source columns")
    by_user: dict[str, list[tuple[object, dict]]] = defaultdict(list)
    unindexed = 0
    startup = []
    for source in rows:
        row = dict(source)
        uid = row["user.index"]
        if not uid:
            raise ValueError("missing participant identity")
        index = row["decision.index.nogap"]
        if not index:
            unindexed += 1
            continue
        try:
            j = float(index)
        except ValueError as exc:
            raise ValueError("invalid non-gap index") from exc
        if not j.is_integer() or j < 0:
            raise ValueError("invalid non-gap index")
        stamp = row["sugg.select.utime"]
        if not stamp:
            if j == 0 and row["avail"] == "False" and row["send"] == "":
                startup.append(row)
                continue
            raise ValueError("cannot establish study day for indexed row")
        try:
            local_day = (datetime.fromisoformat(stamp) +
                         timedelta(seconds=float(row["sugg.gmtoff"]))).date()
        except (ValueError, OverflowError) as exc:
            raise ValueError("invalid UTC stamp or original UTC offset") from exc
        by_user[uid].append((local_day, row))
    kept = list(startup)
    beyond = 0
    for uid, entries in by_user.items():
        study_days = set(sorted({day for day, _ in entries})[:42])
        for day, row in entries:
            if day in study_days:
                kept.append(row)
            else:
                beyond += 1
    anomalous = [
        row for row in kept
        if (row["avail"] == "False" and row["send"] == "True")
        or not row["send.active"]
    ]
    cohort = [
        row for row in kept
        if not ((row["avail"] == "False" and row["send"] == "True")
                or not row["send.active"])
    ]
    eligible = [row for row in cohort if row["avail"] == "True"]
    receipt = {
        "source_records": len(rows),
        "travel_or_technical_unindexed": unindexed,
        "after_study_day_42": beyond,
        "anomaly_rows": len(anomalous),
        "startup_undated_rows": len(startup),
        "cohort_included": len(cohort),
        "cohort_available": len(eligible),
        "cohort_unavailable": len(cohort) - len(eligible),
        "send_true_available": sum(r["send"] == "True" for r in eligible),
        "walking_suggestion": sum(r["send.active"] == "True" for r in eligible),
        "antisedentary_suggestion": sum(r["send.sedentary"] == "True" for r in eligible),
        "cohort_counts_match_paper": (
            len(rows) == 8274 and unindexed == 390 and beyond == 340
            and len(anomalous) == 4 and len(cohort) == 7540
            and len(eligible) == 6061
            and sum(r["send"] == "True" for r in eligible) == 3594
            and sum(r["send.active"] == "True" for r in eligible) == 2015
            and sum(r["send.sedentary"] == "True" for r in eligible) == 1579
        ),
        "scope": "exact published aggregate inclusion counts reconstructed; original individual row identities and GEE estimates not independently verified",
    }
    return cohort, receipt


def make_eligible_rows(rows: list[Mapping[str, str]]) -> list[dict]:
    """Subset to available, numbered <=209; never invent paper exclusions."""
    if not rows or not set(FIELD_NAMES).issubset(rows[0]):
        raise ValueError("incomplete or absent HeartSteps input schema")
    result = []
    seen = set()
    for row in rows:
        uid = row.get("user.index", "")
        if not uid:
            raise ValueError("participant identifier missing")
        index = row.get("decision.index.nogap", "")
        if not index:
            continue  # travel/not-indexed row, excluded before assignment analysis
        try:
            j = float(index)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid decision index") from exc
        if not math.isfinite(j) or not j.is_integer() or j < 0:
            raise ValueError("invalid decision index")
        if j > 209:
            continue
        avail = row.get("avail")
        if avail not in ("True", "False"):
            raise ValueError("missing availability field")
        if avail != "True":
            continue
        key = (uid, int(j))
        if key in seen:
            raise ValueError("duplicate participant-decision index")
        seen.add(key)
        result.append({
            "uid": uid,
            "index": int(j),
            "assignment": int(_flag(row.get("is.randomized", ""))),
            "delivered": int(_flag(row.get("send", ""))),
            "steps": _number(row.get("jbsteps30.zero", "")),
            "steps_pre": _number(row.get("jbsteps30pre.zero", "")),
            "day_scaled": (j / 5.0) / 42.0,
        })
    if not result:
        raise ValueError("no available decision points")
    return result


def _solve_normal_equations(features: list[list[float]], responses: list[float]) -> list[float]:
    """Fixed-dimension dependency-free least squares using pivoted elimination."""
    if not features or len(features) != len(responses):
        raise ValueError("missing aligned design")
    width = len(features[0])
    if width not in (4, 5) or any(len(x) != width for x in features):
        raise ValueError("unexpected design dimension")
    mat = [[0.0] * (width + 1) for _ in range(width)]
    for row, y in zip(features, responses):
        for i in range(width):
            mat[i][-1] += row[i] * y
            for j in range(width):
                mat[i][j] += row[i] * row[j]
    for col in range(width):
        pivot_row = max(range(col, width), key=lambda k: abs(mat[k][col]))
        if abs(mat[pivot_row][col]) < 1e-10:
            raise ValueError("insufficient full-rank treatment and time variation")
        mat[col], mat[pivot_row] = mat[pivot_row], mat[col]
        pivot = mat[col][col]
        for j in range(col, width+1):
            mat[col][j] /= pivot
        for row_idx in range(width):
            if row_idx == col:
                continue
            factor = mat[row_idx][col]
            for j in range(col, width+1):
                mat[row_idx][j] -= factor * mat[col][j]
    return [mat[i][-1] for i in range(width)]



def fit_average_assignment_model(records: list[dict]) -> dict:
    """Secondary study-day-adjusted binary assignment contrast without interaction.

    This is a *linearized analogue* of the paper's primary WCLS model,
    without its robust GEE covariance and full randomization protocol.
    """
    if len(records) < 6:
        raise ValueError("insufficient records")
    design = [
        [1.0, math.log(r["steps_pre"] + .5), r["day_scaled"],
         r["assignment"] - P_ASSIGNED]
        for r in records
    ]
    response = [math.log(r["steps"] + .5) for r in records]
    beta = _solve_normal_equations(design, response)
    return {
        "log_beta": beta[3],
        "average_log_ratio": math.exp(beta[3]),
        "method": "four-variable centered OLS; not exact original GEE/WCLS",
    }


def fit_assignment_model(records: list[dict]) -> dict:
    """Centered OLS of log steps; not original 6061-decision GEE/WCLS."""
    if len(records) < 6:
        raise ValueError("insufficient available decisions for fit")
    design = [
        [1.0, math.log(r["steps_pre"] + .5), r["day_scaled"],
         r["assignment"] - P_ASSIGNED,
         (r["assignment"] - P_ASSIGNED) * r["day_scaled"]]
        for r in records
    ]
    response = [math.log(r["steps"] + .5) for r in records]
    betas = _solve_normal_equations(design, response)
    b = float(betas[3])
    interaction = float(betas[4])
    return {
        "n_decisions": len(records),
        "beta_assignment_day0": b,
        "beta_assignment_day_interaction": interaction,
        "log_pre_coefficient": float(betas[1]),
        "log_steps_ratio_day0": math.exp(b),
        "log_steps_ratio_day21": math.exp(b + interaction * .5),
        "per_study_day_ratio_change": math.exp(interaction / 42.0),
        "estimation": "centered OLS on log(jbsteps30.zero+.5), 0.6 assignment",
    }


def _quantile(sorted_values: list[float], probability: float) -> float:
    pos = (len(sorted_values)-1)*probability
    lo = int(pos)
    hi = min(lo+1,len(sorted_values)-1)
    return sorted_values[lo] + (sorted_values[hi]-sorted_values[lo])*(pos-lo)


def aggregate_report(rows: list[Mapping[str, str]], *,
                     bootstrap_reps: int = 1000,
                     seed: int = 20261107) -> dict:
    """Report only participant-cluster statistics, not individual observations."""
    if bootstrap_reps < 100:
        raise ValueError("at least 100 bootstrap replicates required")
    selected = make_eligible_rows(rows)
    participant_map: dict[str, list[dict]] = defaultdict(list)
    assign_groups: dict[int, list[float]] = defaultdict(list)
    missing_pre = 0
    for r in selected:
        participant_map[r["uid"]].append(r)
        assign_groups[r["assignment"]].append(r["steps"])
    if len(participant_map) < 3 or set(assign_groups) != {0, 1}:
        raise ValueError("need multiple randomized persons and both arms")
    fit = fit_assignment_model(selected)
    rng = random.Random(seed)
    people = sorted(participant_map)
    bootstrap = []
    for _ in range(bootstrap_reps):
        resample = [
            r for _k in people
            for r in participant_map[people[rng.randrange(len(people))]]
        ]
        try:
            model = fit_assignment_model(resample)
            bootstrap.append((
                model["log_steps_ratio_day0"],
                model["log_steps_ratio_day21"],
                model["per_study_day_ratio_change"]
            ))
        except ValueError:
            continue
    if len(bootstrap) < bootstrap_reps * .95:
        raise ValueError("bootstrap support/fit insufficient")
    c0 = sorted(x[0] for x in bootstrap)
    c21 = sorted(x[1] for x in bootstrap)
    daily = sorted(x[2] for x in bootstrap)
    disagreement = sum(r["assignment"] != r["delivered"] for r in selected)
    return {
        "source": SOURCE_URL,
        "source_sha256": SOURCE_SHA256,
        "original_source_documentation": SOURCE_WIKI,
        "original_paper": ORIGINAL_PAPER,
        "source_n_rows": len(rows),
        "strict_available_indexed_0_to_209_decisions": len(selected),
        "original_paper_available_decisions": PAPER_AVAILABLE,
        "cohort_difference_vs_paper": len(selected) - PAPER_AVAILABLE,
        "participants": len(participant_map),
        "eligible_decision_count": len(selected),
        "n_binary_assigned_no_suggestion": len(assign_groups[0]),
        "n_binary_assigned_suggestion": len(assign_groups[1]),
        "empirical_assignment_rate": len(assign_groups[1]) / len(selected),
        "assignment_probability_used": P_ASSIGNED,
        "assignment_delivery_disagreement": disagreement,
        "assignment_mean_steps_no": (sum(assign_groups[0]) / len(assign_groups[0])),
        "assignment_mean_steps_yes": (sum(assign_groups[1]) / len(assign_groups[1])),
        "unadjusted_assigned_mean_difference_steps": (
            (sum(assign_groups[1]) / len(assign_groups[1])) - (sum(assign_groups[0]) / len(assign_groups[0]))
        ),
        "fit": fit,
        "average_binary_assignment_no_interaction": fit_average_assignment_model(selected),
        "cluster_bootstrap_95ci_ratio_day0": [
            _quantile(c0,.025),_quantile(c0,.975)],
        "cluster_bootstrap_95ci_ratio_day21": [
            _quantile(c21,.025),_quantile(c21,.975)],
        "cluster_bootstrap_95ci_daily_ratio": [
            _quantile(daily,.025),_quantile(daily,.975)],
        "bootstrap_reps": bootstrap_reps,
        "bootstrap_valid": len(bootstrap),
        "bootstrap_resampling_unit": "participant",
        "bootstrap_seed": seed,
        "causal_status": "ASSIGNMENT_ANALYSIS_NOT_ORIGINAL_PAPER_REPLICATION",
        "original_6061_cohort_exactly_reproduced": False,
        "published_35_steps_causally_reproduced": False,
        "original_three_arm_assignment_recovered": False,
        "published_35_steps_original_reference": 35,
        "published_day0_ratio_original_reference": 1.66,
        "published_day_decay_original_reference": .98,
        "limitations": (
            "The public is.randomized flag records randomized selection and is "
            "distinct from corrected delivery send. The 0.6 binary selection is "
            "not the original three-arm 0.4/0.3/0.3 assignment record. The "
            "accessible 0..209 index/availability cohort differs from the "
            "paper's 6061; author exclusions and GEE/WCLS covariance are not "
            "fully reconstructed. Historical assignment data support a "
            "limited comparison only conditional on documented randomization."
        ),
        "participant_rows_exported": False,
        "manager_policy_effect_measured": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--bootstrap-reps", type=int, default=1000)
    args = parser.parse_args()
    rows, sha = load_pinned_source()
    if sha != SOURCE_SHA256 or len(rows) != 8274:
        raise ValueError("source hash or record count mismatch")
    author_cohort, author_counts = reconstruct_author_cohort(rows)
    if not author_counts["cohort_counts_match_paper"]:
        raise ValueError("source cohort totals do not reconcile to original HeartSteps report")
    report = aggregate_report(author_cohort, bootstrap_reps=args.bootstrap_reps)
    report["source_n_rows"] = len(rows)
    report["author_cohort_count_reconstruction"] = author_counts
    report["author_protocol_reported_numbers_reconciled"] = True
    with open(args.output,"w",encoding="utf-8") as f:
        json.dump(report,f,ensure_ascii=False,indent=2)
        f.write("\n")
    print(json.dumps({
        "status": report["causal_status"],
        "decisions":report["eligible_decision_count"],
        "paper_decisions":PAPER_AVAILABLE,
        "assignment_delivery_disagreements":report["assignment_delivery_disagreement"],
        "average_binary_assignment_ratio": report["average_binary_assignment_no_interaction"]["average_log_ratio"],
        "day0_ratio":report["fit"]["log_steps_ratio_day0"],
        "day21_ratio":report["fit"]["log_steps_ratio_day21"],
        "daily_ratio":report["fit"]["per_study_day_ratio_change"],
        "confidence_day0":report["cluster_bootstrap_95ci_ratio_day0"],
    },ensure_ascii=False))


if __name__=="__main__":
    main()
