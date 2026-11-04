"""P04-1 educational causal confounding demonstration.

All numbers are invented; there are NO actual people or customer outcomes.
A=1 means showing extra notifications; Y=1 means completing an optional task.
U=1 means a high-intent user. U influences both A and Y.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import numpy as np

P_HIGH = 0.50
P_EXPOSURE_BY_INTENT = {0: 0.20, 1: 0.80}
P_OUTCOME = {(0, 0): 0.20, (0, 1): 0.10, (1, 0): 0.80, (1, 1): 0.70}
# Keys: (U, A). P_OUTCOME[u,a] is the outcome under a fixed setting of A.


def analytical() -> dict[str, Any]:
    """Ground-truth quantities known only in this invented world."""
    p_u = {0: 1-P_HIGH, 1:P_HIGH}
    p_a = sum(p_u[u] * P_EXPOSURE_BY_INTENT[u] for u in (0,1))
    a1_y1 = sum(p_u[u] * P_EXPOSURE_BY_INTENT[u] * P_OUTCOME[(u,1)] for u in (0,1))
    a0_y1 = sum(p_u[u] * (1-P_EXPOSURE_BY_INTENT[u]) * P_OUTCOME[(u,0)] for u in (0,1))
    observed_treated = a1_y1 / p_a
    observed_untreated = a0_y1 / (1-p_a)
    do_treated = sum(p_u[u]*P_OUTCOME[(u,1)] for u in (0,1))
    do_untreated = sum(p_u[u]*P_OUTCOME[(u,0)] for u in (0,1))
    return {
      'notice':'Completely invented educational world. No real users, providers or policy interventions.',
      'observation':{'treated_rate':observed_treated,'untreated_rate':observed_untreated,
                     'observational_difference':observed_treated-observed_untreated},
      'intervention':{'do_treated_rate':do_treated,'do_untreated_rate':do_untreated,
                      'average_causal_effect':do_treated-do_untreated},
      'by_intent':{str(u):{'p_treatment':P_EXPOSURE_BY_INTENT[u],
                            'outcome_no_treatment':P_OUTCOME[(u,0)],
                            'outcome_treatment':P_OUTCOME[(u,1)],
                            'causal_effect':P_OUTCOME[(u,1)]-P_OUTCOME[(u,0)]}
                    for u in (0,1)},
    }


def experiment(n=200_000, seed=20261104) -> dict[str,Any]:
    """Compare confounded observation, random allocation, and adjustment on the same artificial population."""
    if n<100 or not isinstance(n,int):
        raise ValueError('n must be a number of simulated people >= 100')
    rng = np.random.default_rng(seed)
    high = rng.binomial(1, P_HIGH, size=n)
    p_exposure = np.where(high==1, P_EXPOSURE_BY_INTENT[1], P_EXPOSURE_BY_INTENT[0])
    observed_exposure = rng.binomial(1, p_exposure, size=n)
    p0 = np.where(high==1, P_OUTCOME[(1,0)], P_OUTCOME[(0,0)])
    p1 = np.where(high==1, P_OUTCOME[(1,1)], P_OUTCOME[(0,1)])
    # Both potential outcomes are GENERATED FOR SIMULATION; in real observational data, only one is observed.
    y0 = rng.binomial(1, p0, size=n)
    y1 = rng.binomial(1, p1, size=n)
    factual_outcome = np.where(observed_exposure==1, y1, y0)
    obs_exposed = float(factual_outcome[observed_exposure==1].mean())
    obs_unexposed = float(factual_outcome[observed_exposure==0].mean())
    randomized_exposure = rng.binomial(1,0.5,size=n)
    random_outcome = np.where(randomized_exposure==1,y1,y0)
    rct_diff = float(random_outcome[randomized_exposure==1].mean() - random_outcome[randomized_exposure==0].mean())
    # Standardization using pre-treatment U; requires that all confounders are measured and positivity.
    group_deltas = {}
    for u in (0,1):
        subset=(high==u)
        treated=subset & (observed_exposure==1)
        control=subset & (observed_exposure==0)
        group_deltas[u] = float(factual_outcome[treated].mean()-factual_outcome[control].mean())
    standardized = float((1-high.mean())*group_deltas[0] + high.mean()*group_deltas[1])
    return {
       'n':n, 'seed':seed,
       'observational_difference':obs_exposed-obs_unexposed,
       'observed_treated_rate':obs_exposed,'observed_control_rate':obs_unexposed,
       'randomized_difference':rct_diff,
       'standardized_difference':standardized,
       'oracle_potential_outcome_difference_in_simulator':float((y1-y0).mean()),
       'p_high_in_sample':float(high.mean()),
       'n_obs_exposed':int(observed_exposure.sum()),
       'by_intent_observed_diff':{str(u):group_deltas[u] for u in (0,1)},
       'warning':'Oracle counterfactuals exist only inside this synthetic generator.'
    }


def make_result(save:bool=True):
    result={'analytic':analytical(),'synthetic':experiment()}
    if save:
        dest=Path(__file__).resolve().parents[1]/'evidence'/'p04_1_causal_result.json'
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    print(json.dumps(make_result(),indent=2,ensure_ascii=False))
