"""ManagerBench v0.1: leak-conscious metrics only, no fitted foundation model.

Scoring contract: binary choices and continuous outcomes are separately evaluated.
All example rows in unit tests are synthetic SOFTWARE FIXTURES, not human results.
"""
from __future__ import annotations

from collections import defaultdict
from math import log, sqrt
from statistics import mean
from typing import Iterable, Mapping, Sequence


def verify_disjoint(train: Sequence[Mapping], valid: Sequence[Mapping],
                    test: Sequence[Mapping], key: str = "participant_id") -> None:
    """Reject repeated subject/study IDs across prescribed splits."""
    if not key:
        raise ValueError("split key is required")
    sets = []
    for records in (train, valid, test):
        values = []
        for row in records:
            value = row.get(key)
            if value is None or value == "":
                raise ValueError("missing split identity")
            values.append(str(value))
        sets.append(set(values))
    for i in range(3):
        for j in range(i + 1, 3):
            if sets[i].intersection(sets[j]):
                raise ValueError(f"leakage: {key} overlaps across splits {i},{j}")


def verify_prediction_cutoff(rows: Iterable[Mapping]) -> None:
    """Never score a prediction that uses data after the observation cutoff."""
    for row in rows:
        needed = ("available_until", "target_at", "prediction")
        if any(k not in row for k in needed):
            raise ValueError("timestamp/probability fields required")
        # ISO8601 timestamps must use a consistent timezone representation.
        if not isinstance(row["available_until"], str) or not isinstance(row["target_at"], str):
            raise ValueError("timestamps must be ISO8601 strings")
        if row["available_until"] >= row["target_at"]:
            raise ValueError("feature lookahead or same-time target leakage")


def binary_metrics(actual: Sequence[int], predicted: Sequence[float],
                   ece_bins: int = 10) -> dict[str, float]:
    """Compute proper scores (lower is better) for paired Bernoulli forecasts."""
    if len(actual) != len(predicted) or not actual:
        raise ValueError("nonempty aligned predictions required")
    if ece_bins < 2:
        raise ValueError("need >=2 calibration bins")
    y, p = list(actual), list(predicted)
    if any(v not in (0, 1) for v in y):
        raise ValueError("binary ground truth must be 0 or 1")
    if any(not isinstance(v, (int, float)) or not (0 <= v <= 1) for v in p):
        raise ValueError("predicted probability outside [0,1]")
    tiny = 1e-15
    ll = -mean(v * log(max(tiny, min(1-tiny, x))) +
               (1-v) * log(max(tiny, min(1-tiny, 1-x))) for v, x in zip(y, p))
    brier = mean((v-x)**2 for v, x in zip(y, p))
    bins: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for v, x in zip(y, p):
        bins[min(int(x * ece_bins), ece_bins - 1)].append((v, x))
    ece = sum((len(b) / len(y)) *
              abs(mean(item[0] for item in b) - mean(item[1] for item in b))
              for b in bins.values())
    return {"n": len(y), "log_loss": ll, "brier": brier, "ece": ece}


def continuous_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict:
    """Compute MAE and RMSE on the same outcome scale; forbid nan/inf."""
    if len(actual) != len(predicted) or not actual:
        raise ValueError("nonempty aligned predictions required")
    from math import isfinite
    if any(not isfinite(float(v)) for pair in zip(actual, predicted) for v in pair):
        raise ValueError("nonfinite outcome/prediction")
    diffs = [float(a)-float(p) for a,p in zip(actual,predicted)]
    return {"n": len(diffs), "mae": mean(abs(d) for d in diffs),
            "rmse": sqrt(mean(d*d for d in diffs))}


def randomized_itt(rows: Sequence[Mapping]) -> dict:
    """Unadjusted intention-to-treat difference for an explicitly randomized sample.

    IMPORTANT: this routine does not itself verify that an RCT truly randomized;
    provenance and assignment-integrity audits are mandatory before causal claims.
    """
    if not rows:
        raise ValueError("empty trial")
    if any(r.get("design") != "randomized" for r in rows):
        raise ValueError("refusing ITT label for nonrandomized/unknown designs")
    groups: dict[int, list[float]] = {0: [], 1: []}
    from math import isfinite
    for r in rows:
        a, y = r.get("assigned"), r.get("outcome")
        if a not in (0, 1) or y is None or not isfinite(float(y)):
            raise ValueError("invalid assignment or outcome")
        groups[a].append(float(y))
    if not groups[0] or not groups[1]:
        raise ValueError("both assignment arms must be represented")
    return {"n_control": len(groups[0]), "n_treated": len(groups[1]),
            "mean_control": mean(groups[0]), "mean_treated": mean(groups[1]),
            "itt_difference": mean(groups[1]) - mean(groups[0])}


def model_card(model_name: str, data_rights: str, split: str,
               scored: Mapping[str, float], empirical: bool = False) -> dict:
    """Write an unambiguous research card; do not invent foundation-model success."""
    if not all((model_name, data_rights, split)):
        raise ValueError("model, rights and split required")
    return {"model": model_name, "data_rights": data_rights,
            "split": split, "metrics": dict(scored),
            "source": "actual_observations" if empirical else "software_fixture",
            "causal_effect_established": False}
