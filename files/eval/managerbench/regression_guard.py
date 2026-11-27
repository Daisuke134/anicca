"""Pinned TODO38 external factual-prediction regression diagnostic.

A failure vetoes this candidate for this scope; a pass is never approval.
Historical evidence is not a current production or safety attestation.
"""
import hashlib
import json
import math
from pathlib import Path

HOLDOUT_SHA = "ac7706c9078b88d5c221d71d1aa6e8ca362a9e9a48c0c298d43b19ff188c2032"
SOURCE = "https://github.com/Daisuke134/anicca-ops/blob/7e07a1aa538dd8b6871b035f3ceddc4417e212af/files/research-artifacts/holdout-standalone38-2026-11-27/receipt.json"
ARMS = ("sft_42", "sft_43", "dpo_42", "dpo_43")


def evaluate(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != HOLDOUT_SHA:
        raise ValueError("pinned holdout receipt digest mismatch")
    d = json.loads(raw)
    if d["n"] != 512 or len(d["y"]) != 512 or sum(d["y"]) != 93:
        raise ValueError("unexpected holdout denominator")
    if any(type(y) is not int or y not in (0, 1) for y in d["y"]):
        raise ValueError("invalid labels")
    results = {}
    for arm in ("base", "source_prior", *ARMS):
        p = d["results"][arm]["p"]
        if len(p) != len(d["y"]) or any(type(v) not in (int,float) or not math.isfinite(v) or not 0 <= v <= 1 for v in p):
            raise ValueError("invalid prediction frame")
        loss = math.fsum((v-y)**2 for v,y in zip(p,d["y"]))/len(p)
        pos = [v for v,y in zip(p,d["y"]) if y==1]
        neg = [v for v,y in zip(p,d["y"]) if y==0]
        auc = math.fsum((a>b)+.5*(a==b) for a in pos for b in neg)/(len(pos)*len(neg))
        for metric,val in (("brier",loss),("auc",auc)):
            if not math.isclose(val,d["results"][arm]["metrics"][metric],rel_tol=0,abs_tol=1e-10):
                raise ValueError("metric mismatch")
        results[arm] = {"brier":loss,"auc":auc}
    candidates = {}
    for arm in ARMS:
        m = results[arm]
        checks = {"brier_no_worse_than_base":m["brier"]<=results["base"]["brier"],
                  "brier_no_worse_than_prior":m["brier"]<=results["source_prior"]["brier"],
                  "auc_at_least_chance":m["auc"]>=.5}
        candidates[arm] = {"checkpoint_sha256":d["adapters"][arm], "metrics":m, "checks":checks,
                           "status":"SCREEN_PASS_NOT_APPROVED" if all(checks.values()) else "BLOCKED_REGRESSION"}
    return {"schema":"managerbench.holdout-regression.v1","source":SOURCE,"sha256":HOLDOUT_SHA,
            "n":512,"positive":93,"base":results["base"],"prior":results["source_prior"],
            "candidates":candidates,"promotion_eligible":False,
            "limitation":"Retrospective point-estimate screen, not preregistered noninferiority, blind test, safety or product benefit."}


def candidate_preflight(report, candidate, checkpoint_sha256):
    """Veto only; independent release gates remain mandatory."""
    row = report["candidates"].get(candidate)
    if row is None or row["checkpoint_sha256"] != checkpoint_sha256:
        return "BLOCKED_UNKNOWN_CANDIDATE"
    return row["status"]
