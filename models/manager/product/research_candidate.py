"""Portable factual research specialist. Never an intervention policy."""
import hashlib
import json
import math
from pathlib import Path

SCOPE = "uci_shopper_factual_research"
SHA = "7734f8a879c375b97438784f829fb7be103ad9de96edc94fbe776b29d952f619"

def load_candidate(path):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != SHA:
        raise ValueError("candidate bytes do not match pinned research checkpoint")
    return json.loads(raw)

def predict(candidate, context, *, scope):
    if scope != SCOPE:
        raise PermissionError("research specialist cannot serve mobile or intervention decisions")
    cats = candidate["feature_categories"]
    if set(context) != set(cats) | {"SpecialDay"}:
        raise ValueError("invalid feature set")
    # Training order is explicit: JSON serialization sorts object keys.
    order = ("Month", "VisitorType", "Weekend")
    if any(context[k] not in cats[k] for k in order):
        raise ValueError("unknown category")
    day = context["SpecialDay"]
    if type(day) not in (float, int) or not math.isfinite(day) or not 0 <= day <= 1:
        raise ValueError("invalid SpecialDay")
    x = [float(context[k] == v) for k in order for v in cats[k]] + [float(day)]
    state = candidate["state"]
    z = math.fsum(w*v for w,v in zip(state["weight"][0],x,strict=True)) + state["bias"][0]
    return 1/(1+math.exp(-z))

def mobile_preflight(path):
    # This checkpoint has no mobile evidence, irrespective of factual score.
    load_candidate(path)
    return {"status":"BLOCKED_OUT_OF_SCOPE", "release_approved":False,
            "evaluated_scope":SCOPE}
