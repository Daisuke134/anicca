#!/usr/bin/env python3
"""P09-1 Nature 2026 Figure 1 aggregate-effect reanalysis.

READ ONLY. This is NOT a re-run of the authors' saved individual-level RDS
responses, R package meta-analysis or complete Figure 1 computation.
Input: a CSV transcribed from the official Fig. 1 source-data XLSX panelA.
Source: https://doi.org/10.1038/s41586-026-10742-x
CodeOcean original: https://codeocean.com/capsule/9843791/tree/v1

Input CSV required columns:
 study,reference_condition,outcome,condition,human,prediction,group
The author's published panelA contains directional contrasts (including reverses),
NOT independent participant rows or the original 469 trial effect estimates.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path
from statistics import fmean

SOURCE = (
    "https://media.springernature.com/original/springer-static/esm/"
    "art%3A10.1038%2Fs41586-026-10742-x/MediaObjects/"
    "41586_2026_10742_MOESM4_ESM.xlsx"
)
PUBLISHED_PANELB = {
    "gpt4_raw_correlation": 0.850789501576886,
    "gpt4_adjusted_correlation_estimate": 0.915126645908733,
}
REQUIRED = (
    "study", "reference_condition", "outcome", "condition",
    "human", "prediction", "group",
)


def read_contrasts(path: Path) -> list[dict]:
    """Load only the published aggregate effects; refuse invalid identifiers."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not set(REQUIRED).issubset(reader.fieldnames or []):
            raise ValueError(f"Missing CSV columns: {set(REQUIRED) - set(reader.fieldnames or [])}")
        records = []
        for row in reader:
            if any(not row.get(name) for name in ("study", "reference_condition", "outcome", "condition")):
                raise ValueError("Missing identifying field in source contrast")
            try:
                row["human"] = float(row["human"])
                row["prediction"] = float(row["prediction"])
            except (ValueError, TypeError) as exc:
                raise ValueError("Non-numeric contrast estimate") from exc
            if not all(math.isfinite(row[name]) for name in ("human", "prediction")):
                raise ValueError("Non-finite contrast estimate")
            records.append(row)
    if not records:
        raise ValueError("Empty source file")
    return records


def summarize(records: list[dict]) -> dict:
    """Compute pooled *descriptive* correlations, not an adjusted causal estimand."""
    n = len(records)
    if n < 3:
        raise ValueError("At least 3 contrasts required")
    y = [x["human"] for x in records]
    p = [x["prediction"] for x in records]
    my, mp = fmean(y), fmean(p)
    yc = [v - my for v in y]
    pc = [v - mp for v in p]
    cross = sum(x * z for x, z in zip(yc, pc))
    yy = sum(x * x for x in yc)
    pp = sum(x * x for x in pc)
    if not yy or not pp:
        raise ValueError("Correlation undefined: constant input")
    slope = cross / pp
    return {
        "n": n,
        "pearson_r": cross / math.sqrt(yy * pp),
        "rmse": math.sqrt(fmean((a - b) ** 2 for a, b in zip(y, p))),
        "mae": fmean(abs(a - b) for a, b in zip(y, p)),
        "slope_human_on_prediction": slope,
        "intercept_human_on_prediction": my - slope * mp,
    }


def mirror_coverage(records: list[dict]) -> dict:
    """Check whether the source contains every reversed pair."""
    idx = {
        (r["study"], r["outcome"], r["reference_condition"], r["condition"]): r
        for r in records
    }
    matched = 0
    for row in records:
        reverse = idx.get((
            row["study"], row["outcome"], row["condition"], row["reference_condition"]
        ))
        if reverse is None:
            continue
        if abs(row["human"] + reverse["human"]) > 1e-9:
            raise ValueError("Inconsistent mirrored human contrast")
        if abs(row["prediction"] + reverse["prediction"]) > 1e-9:
            raise ValueError("Inconsistent mirrored prediction")
        matched += 1
    return {
        "directional_rows_with_reverse": matched,
        "unordered_pair_estimate_if_all_mirrored": matched // 2 if matched == len(records) else None,
        "share_rows_with_reverse": matched / len(records),
    }


def percentile(sorted_values: list[float], p: float) -> float:
    """Linear-interpolation percentile for descriptive bootstrap diagnostics."""
    z = (len(sorted_values) - 1) * p
    lo = math.floor(z)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] * (hi - z) + sorted_values[hi] * (z - lo) if hi != lo else sorted_values[lo]


def study_cluster_bootstrap(by_study: dict[str, list[dict]], *, seed: int, reps: int) -> dict:
    """Resample whole studies, not individual directional contrasts."""
    if reps < 100:
        raise ValueError(">=100 repetitions required")
    ids = sorted(by_study)
    if len(ids) < 3:
        raise ValueError(">=3 studies required")
    rng = random.Random(seed)
    boot = []
    for _ in range(reps):
        sample = [
            contrast
            for _ in ids
            for contrast in by_study[rng.choice(ids)]
        ]
        try:
            boot.append(summarize(sample))
        except ValueError:
            continue
    if len(boot) < .95 * reps:
        raise ValueError("Insufficient bootstrap replicates")
    return {
        "repetitions_requested": reps,
        "repetitions_valid": len(boot),
        "seed": seed,
        "percentile_95_intervals": {
            name: [
                percentile(sorted(b[name] for b in boot), .025),
                percentile(sorted(b[name] for b in boot), .975),
            ]
            for name in ("pearson_r", "rmse", "slope_human_on_prediction")
        },
    }



def study_heldout_calibration(by_study: dict[str, list[dict]]) -> dict:
    """Fit a one-parameter linear calibration on 69 studies; test on the 70th.

    The comparison is descriptive for *existing published contrasts*.
    It does not prove the GPT-4 model itself was trained on unseen studies.
    """
    ids = sorted(by_study)
    if len(ids) < 3:
        raise ValueError("At least three independent study groups required")
    all_raw = []
    all_calibrated = []
    macro = []
    for heldout in ids:
        train = [
            row for name, data in by_study.items()
            if name != heldout for row in data
        ]
        test = by_study[heldout]
        fit = summarize(train)
        b = fit["slope_human_on_prediction"]
        a = fit["intercept_human_on_prediction"]
        before = [(row["prediction"] - row["human"]) ** 2 for row in test]
        after = [(a + b * row["prediction"] - row["human"]) ** 2 for row in test]
        all_raw.extend(before)
        all_calibrated.extend(after)
        macro.append({
            "study": heldout, "n_contrasts": len(test),
            "rmse_raw": math.sqrt(fmean(before)),
            "rmse_calibrated": math.sqrt(fmean(after)),
        })
    rmse_raw = math.sqrt(fmean(all_raw))
    rmse_cal = math.sqrt(fmean(all_calibrated))
    return {
        "method": "leave-one-study-out cross-fitted linear calibration",
        "n_heldout_studies": len(ids),
        "micro_rmse_raw": rmse_raw,
        "micro_rmse_calibrated": rmse_cal,
        "micro_rmse_improvement": rmse_raw - rmse_cal,
        "macro_rmse_raw": fmean(row["rmse_raw"] for row in macro),
        "macro_rmse_calibrated": fmean(row["rmse_calibrated"] for row in macro),
        "studies_improved": sum(row["rmse_calibrated"] < row["rmse_raw"] for row in macro),
        "studies_harmed": sum(row["rmse_calibrated"] > row["rmse_raw"] for row in macro),
        "not_prospective_model_generalization": True,
    }


def evaluate(path: Path, *, seed: int = 20261107, reps: int = 2000) -> dict:
    records = read_contrasts(path)
    by_study = defaultdict(list)
    for rec in records:
        by_study[rec["study"]].append(rec)
    leave_one_out = {}
    for sid in sorted(by_study):
        sample = [r for name, group in by_study.items() if name != sid for r in group]
        leave_one_out[sid] = summarize(sample)["pearson_r"]
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "status": "FIGURE_SOURCE_REANALYSIS_ONLY",
        "study_count": len(by_study),
        "source": SOURCE,
        "normalized_csv_sha256": digest,
        "source_sheet": "panelA",
        "analysis_scope": "All directional plot contrasts, not official adjusted 469-effect estimate",
        "summary": summarize(records),
        "mirror_check": mirror_coverage(records),
        "by_group": {
            group: summarize([r for r in records if r["group"] == group])
            for group in sorted({r["group"] for r in records})
        },
        "bootstrap": study_cluster_bootstrap(by_study, seed=seed, reps=reps),
        "study_heldout_linear_calibration": study_heldout_calibration(by_study),
        "leave_one_study_out_pearson_range": [
            min(leave_one_out.values()), max(leave_one_out.values())
        ],
        "published_author_panelB_reference_not_recalculated": PUBLISHED_PANELB,
        "original_codeocean_RDS_rerun": False,
        "reason_not_full_original_replication":
            "CodeOcean public file export requires authentication; Rscript is absent on local Mac.",
        "new_LLM_inference_or_human_experiment": False,
    }


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--input", required=True, type=Path, help="CSV of official Fig1 panelA aggregates")
    cli.add_argument("--output", type=Path, help="Where to write JSON report")
    cli.add_argument("--seed", type=int, default=20261107)
    cli.add_argument("--reps", type=int, default=2000)
    opt = cli.parse_args()
    report = evaluate(opt.input, seed=opt.seed, reps=opt.reps)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if opt.output:
        opt.output.parent.mkdir(parents=True, exist_ok=True)
        opt.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
