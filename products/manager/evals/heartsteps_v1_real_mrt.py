"""HeartSteps V1: real-human micro-randomized notification effect audit.

Source CC BY 4.0, https://github.com/klasnja/HeartStepsV1.
Klasnja et al. (2019), DOI: 10.1093/abm/kay067.
Only aggregate statistics and software tests are committed; never upload rows.
This is a descriptive complete-case delivery-status audit, NOT a causal effect estimate.
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
from collections import defaultdict

SOURCE_COMMIT = "3016391de426116bdef41880d72bc8cd4b9b2477"
SOURCE_URL = (
    "https://raw.githubusercontent.com/klasnja/HeartStepsV1/"
    + SOURCE_COMMIT + "/data_files/suggestions.csv"
)
SOURCE_SHA256 = "60ee7896183d7084a084f9a6e8ef2d0afea2e7fecdb41d6b15382ce1745c5ddb"
PAPER = "https://doi.org/10.1093/abm/kay067"
MISSING = {"", "NA", "NaN", "nan", "null", "None"}
SEED = 20261106


def truth(value: object) -> bool | None:
    v = str(value).strip().lower()
    if v in {"true", "t", "1"}:
        return True
    if v in {"false", "f", "0"}:
        return False
    return None


def measure(value: str) -> float | None:
    if str(value).strip() in MISSING:
        return None
    try:
        x = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if not math.isfinite(x) or x < 0:
        return None
    return x


def load_pinned_source() -> tuple[list[dict[str, str]], str]:
    req = urllib.request.Request(
        SOURCE_URL, headers={"User-Agent": "Manager-Behavior-Impact/0.1"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = r.read(12_000_000)
    digest = hashlib.sha256(data).hexdigest()
    if digest != SOURCE_SHA256:
        raise ValueError("source bytes differ from pinned published data")
    records = list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))
    return records, digest


def summarize(rows: list[dict[str, str]], *, field: str = "jbsteps30",
              reps: int = 2000, seed: int = SEED) -> dict:
    """Audit post-assignment corrected notification DELIVERY, not randomized intent.

    The public 'send' variable reflects corrected delivery status; it is not an
    unmodified randomized assignment field. Our availability-only sample (6,590)
    differs from the original paper's 6,061 eligible decision points. Therefore
    this complete-case descriptive contrast is NOT an ITT nor a causal effect.
    """
    if reps < 100 or not rows:
        raise ValueError("nonempty real rows and >=100 bootstrap replicates required")
    keys = {"user.index", "avail", "send", field}
    if not keys.issubset(rows[0]):
        raise ValueError("required original study fields absent")
    by_id: dict[str, list[tuple[int, float]]] = defaultdict(list)
    count_by_arm = [0, 0]
    observed_by_arm = [0, 0]
    sum_by_arm = [0., 0.]
    original_count = len(rows)
    eligible = 0
    all_people: set[str] = set()
    for row in rows:
        uid = row.get("user.index", "")
        if not uid:
            raise ValueError("missing participant key")
        all_people.add(uid)
        if truth(row.get("avail")) is not True:
            continue
        # Do not use 'is.randomized' as treatment: the source's corrected
        # 'send' is delivery status, and neither is verified ITT assignment.
        delivered = truth(row.get("send"))
        if delivered is None:
            continue
        t = int(delivered)
        eligible += 1
        count_by_arm[t] += 1
        y = measure(row[field])
        if y is None:
            continue
        by_id[uid].append((t, y))
        observed_by_arm[t] += 1
        sum_by_arm[t] += y
    if min(observed_by_arm) == 0:
        raise ValueError("both eligible randomized arms require observed outcome")
    mean0 = sum_by_arm[0] / observed_by_arm[0]
    mean1 = sum_by_arm[1] / observed_by_arm[1]
    people = sorted(by_id)
    rng = random.Random(seed)
    boots: list[float] = []
    for _ in range(reps):
        bsum = [0., 0.]
        bn = [0, 0]
        for _k in range(len(people)):
            sampled = by_id[people[rng.randrange(len(people))]]
            for arm, value in sampled:
                bsum[arm] += value
                bn[arm] += 1
        if min(bn) > 0:
            boots.append(bsum[1] / bn[1] - bsum[0] / bn[0])
    boots.sort()
    if len(boots) < 0.95 * reps:
        raise ValueError("cluster bootstrap failed to cover both arms")
    def quantile(p):
        pos = (len(boots) - 1) * p
        lo = int(pos)
        hi = min(lo + 1, len(boots) - 1)
        return boots[lo] + (boots[hi] - boots[lo]) * (pos - lo)
    return {
        "total_source_decisions": original_count,
        "source_participants": len(all_people),
        "eligible_decisions": eligible,
        "observed_participants": len(people),
        "eligible_no_suggestion": count_by_arm[0],
        "eligible_suggestion": count_by_arm[1],
        "observed_no_suggestion": observed_by_arm[0],
        "observed_suggestion": observed_by_arm[1],
        "missing_no_suggestion": count_by_arm[0] - observed_by_arm[0],
        "missing_suggestion": count_by_arm[1] - observed_by_arm[1],
        "missing_rate_no_suggestion": 1 - observed_by_arm[0] / count_by_arm[0],
        "missing_rate_suggestion": 1 - observed_by_arm[1] / count_by_arm[1],
        "mean_no_suggestion": mean0,
        "mean_suggestion": mean1,
        "observed_difference_steps": mean1 - mean0,
        "bootstrap_95ci_cluster_participant": [quantile(.025), quantile(.975)],
        "bootstrap_repetitions": reps,
        "random_seed": seed,
        "outcome_field": field,
        "estimand": "descriptive_complete_case_steps_difference_by_corrected_delivery_status",
        "identification_status": "NOT_CAUSAL",
        "original_paper_available_decisions": 6061,
        "published_adjusted_reference_steps": 35,
        "published_adjusted_reference_pvalue": 0.06,
        "causal_claim": (
            "NOT_CAUSAL: 'send' is a corrected notification delivery-status variable, "
            "not the original randomized assignment; this is not an ITT or an "
            "identified treatment effect. This cohort has 6,590 available records "
            "versus the original paper's 6,061 analysis decision points. "
            "Missing outcomes and post-assignment delivery can bias contrasts."
        ),
        "quality_of_life_measured": False,
        "personalized_manager_policy_evaluated": False,
    }


def main() -> None:
    rows, sha = load_pinned_source()
    if len(rows) != 8274:
        raise ValueError("unexpected row count; do not silently change study cohort")
    report = {
        "date": "2026-11-06",
        "source": "klasnja/HeartStepsV1",
        "source_url": SOURCE_URL,
        "source_sha256": sha,
        "license": "CC BY 4.0 (repository metadata)",
        "published_paper": PAPER,
        "study_type": "real_human_micro_randomized_trial",
        "original_author_results_not_reproduced_exactly": True,
        "jawbone_30min": summarize(rows, field="jbsteps30"),
        "googlefit_30min_sensitivity": summarize(rows, field="gfsteps30"),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
