"""Paired history diagnostics; no cross-task or causal claim."""
import math
from collections import defaultdict
import random

def score(rows, *, repeats=2000, seed=42):
    """Rows: case_id, participant, mode, p_gold. Reject incomplete pairs."""
    by_case = defaultdict(dict)
    for row in rows:
        key = (row["participant"], row["case_id"])
        mode, p = row["mode"], row["p_gold"]
        if mode not in {"own", "other", "none"} or mode in by_case[key]:
            raise ValueError("unknown mode or duplicate case")
        if isinstance(p, bool) or not isinstance(p, (int,float)) or not math.isfinite(p) or not 0 < p <= 1:
            raise ValueError("invalid probability")
        by_case[key][mode] = -math.log(p)
    if not by_case or any(set(v) != {"own","other","none"} for v in by_case.values()):
        raise ValueError("incomplete matched frame")
    grouped = defaultdict(list)
    for (participant,_), v in by_case.items():
        grouped[participant].append(v)
    if len(grouped) < 2 or repeats < 100:
        raise ValueError("insufficient clusters or bootstrap repeats")
    means = {mode: sum(v[mode] for v in by_case.values())/len(by_case)
             for mode in ("own","other","none")}
    contrasts = {}
    for comparator in ("other","none"):
        clusters = [(sum(v["own"]-v[comparator] for v in g),len(g))
                    for g in grouped.values()]
        rng = random.Random(seed)
        bs = []
        for _ in range(repeats):
            sampled = rng.choices(clusters,k=len(clusters))
            bs.append(sum(d for d,n in sampled)/sum(n for d,n in sampled))
        bs.sort()
        contrasts[comparator] = {"delta":means["own"]-means[comparator],
            "ci95":[bs[int(.025*repeats)],bs[min(repeats-1,int(.975*repeats))]]}
    return {"n_cases":len(by_case),"n_participants":len(grouped),
            "conditional_nll":means,"own_minus":contrasts}
