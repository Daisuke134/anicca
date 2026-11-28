"""Research screening only, never grants production authorization."""
import math

def screen(receipt):
    reasons=[]
    n=receipt.get("test_n")
    if type(n) is not int or n<2:
        reasons.append("invalid_participant_count")
    contrasts=receipt.get("paired",{})
    for seed in (42,43,44):
        for mode in ("none","other"):
            key=f"own_{seed}-{mode}_{seed}"
            row=contrasts.get(key,{})
            d=row.get("delta");ci=row.get("ci95")
            if (not isinstance(ci,list) or len(ci)!=2 or
                any(type(v) not in (int,float) or not math.isfinite(v) for v in [d,*ci]) or
                not ci[0]<=d<=ci[1]):
                reasons.append(key+":invalid_evidence")
            elif ci[1]>=0:
                reasons.append(key+":no_clear_improvement")
    return {"screen_pass":not reasons,"reasons":reasons,
            "production_eligible":False,"scope":"retrospective_history_screen"}
