"""Matched binary evaluation, separate from the frozen ManagerBench replay.

Missing case IDs are rejected; invalid/abstained outputs stay in denominator.
Exact McNemar assumes independent pairs; do not infer clustered significance.
"""
from math import comb


def compare_binary(expected_ids, baseline, candidate):
    ids = list(expected_ids)
    if not ids or any(type(k) is not str or not k for k in ids) or len(set(ids)) != len(ids):
        raise ValueError("expected IDs must be unique nonempty strings")
    frame = set(ids)
    for arm in (baseline, candidate):
        if type(arm) is not dict or set(arm) != frame:
            raise ValueError("matched case frame mismatch")
        if any(type(v) is not str or v not in ("correct", "incorrect", "invalid", "abstain") for v in arm.values()):
            raise ValueError("invalid outcome status")
    n = len(ids)
    a = sum(baseline[k] == candidate[k] == "correct" for k in ids)
    b = sum(baseline[k] != "correct" and candidate[k] == "correct" for k in ids)
    c = sum(baseline[k] == "correct" and candidate[k] != "correct" for k in ids)
    d = n-a-b-c
    discordant = b+c
    p = min(1.0, 2*sum(comb(discordant, i) for i in range(min(b,c)+1))/(1 << discordant))
    def summary(arm):
        return {"correct": sum(v == "correct" for v in arm.values()),
                "incorrect": sum(v == "incorrect" for v in arm.values()),
                "invalid": sum(v == "invalid" for v in arm.values()),
                "abstain": sum(v == "abstain" for v in arm.values()),
                "strict_accuracy": sum(v == "correct" for v in arm.values())/n}
    return {"n": n, "baseline": summary(baseline), "candidate": summary(candidate),
            "both_correct": a, "improved": b, "regressed": c, "both_not_correct": d,
            "delta_strict_accuracy": (b-c)/n, "mcnemar_exact_two_sided_unadjusted": p,
            "limitation": "Independent pairs assumed; no cluster or multiplicity adjustment. Not a causal effect or promotion gate."}


def compare_matched_runs(expected_ids, baseline_run, candidate_run):
    """Strict external model-to-model protocol equality before scoring.
    
    Model identity is deliberately separate. Missing metadata is not a match.
    This checks declared metadata; an independent runner must verify provenance.
    """
    fields = {"dataset_revision", "split", "case_manifest_sha256",
              "evaluator_revision", "prompt_sha256", "inference_protocol_sha256"}
    for run in (baseline_run, candidate_run):
        if type(run) is not dict or set(run) != {"condition", "model_id", "outcomes"}:
            raise ValueError("run metadata incomplete")
        if type(run["model_id"]) is not str or not run["model_id"].strip():
            raise ValueError("model identity missing")
        condition = run["condition"]
        if type(condition) is not dict or set(condition) != fields:
            raise ValueError("condition fields incomplete")
        for k,v in condition.items():
            if type(v) is not str or not v.strip():
                raise ValueError("condition value missing")
            if k.endswith("_sha256") and (len(v) != 64 or any(ch not in "0123456789abcdef" for ch in v)):
                raise ValueError("condition digest invalid")
    if baseline_run["condition"] != candidate_run["condition"]:
        raise ValueError("comparison condition mismatch")
    result = compare_binary(expected_ids, baseline_run["outcomes"], candidate_run["outcomes"])
    return {**result, "condition": baseline_run["condition"],
            "baseline_model": baseline_run["model_id"], "candidate_model": candidate_run["model_id"]}
