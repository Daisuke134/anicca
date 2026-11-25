"""Read-only offline adapter for a fixed Manager candidate generator and OBP.
No raw user context or text is returned. Not a policy deployment gate.
"""
import math
import numpy as np


def prepare(decisions):
    """Each row: id, candidates (id/probability/kind), chosen_id, pscore,
    target (id -> probability), reward (explicit observed 0/1 or None).
    Target probabilities must be computed before seeing the chosen action/outcome.
    Missing outcomes block estimation; they are never treated as zero.
    """
    rows = list(decisions)
    if not rows:
        raise ValueError('empty evaluation cohort')
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('duplicate decision')
    n = len(rows)
    k = max(len(r['candidates']) for r in rows)
    pi = np.zeros((n, k, 1))
    action = np.zeros(n, dtype=int)
    pscore = np.zeros(n)
    reward = np.zeros(n)
    missing = 0
    def prob(x):
        return type(x) in (float, int) and math.isfinite(x) and 0 <= x <= 1
    for i, r in enumerate(rows):
        cs = r['candidates']
        ids = [c['id'] for c in cs]
        mu = [c['probability'] for c in cs]
        t = r['target']
        if len(cs) < 2 or len(set(ids)) != len(ids) or sum(c['kind']=='none' for c in cs)!=1:
            raise ValueError('invalid candidate pool')
        if set(t)!=set(ids) or not all(prob(p) for p in mu+list(t.values())):
            raise ValueError('invalid policy distribution')
        if not math.isclose(math.fsum(mu),1,abs_tol=1e-12,rel_tol=0) or not math.isclose(math.fsum(t.values()),1,abs_tol=1e-12,rel_tol=0):
            raise ValueError('probabilities must sum to one')
        if any(t[c]>0 and p==0 for c,p in zip(ids,mu)):
            raise ValueError('target lacks logging support')
        j = ids.index(r['chosen_id'])
        p = r['pscore']
        if not prob(p) or p<=0 or not math.isclose(p,mu[j],abs_tol=1e-12,rel_tol=0):
            raise ValueError('propensity mismatch')
        action[i], pscore[i] = j,p
        pi[i,:len(cs),0] = [t[c] for c in ids]
        y = r['reward']
        if y is None:
            missing += 1
        elif type(y) in (bool,int,float) and y in (0,1):
            reward[i] = y
        else:
            raise ValueError('invalid binary outcome')
    w = pi[np.arange(n),action,0]/pscore
    if not np.isfinite(w).all():
        raise ValueError('nonfinite weights')
    ess = float(w.sum()**2/np.dot(w,w)) if np.any(w) else 0.0
    diagnostics = dict(attempted=n, observed=n-missing, missing=missing,
                       ess=ess, max_weight=float(w.max()), mean_weight=float(w.mean()))
    if missing or ess == 0:
        return None, diagnostics
    return dict(reward=reward,action=action,pscore=pscore,action_dist=pi), diagnostics


def evaluate(decisions):
    """Call official OBP, not a duplicate estimator. No DR without heldout q-hat."""
    data, diagnostics = prepare(decisions)
    if data is None:
        return dict(status='UNMEASURED', diagnostics=diagnostics, ipw=None, snipw=None)
    from obp.ope import InverseProbabilityWeighting, SelfNormalizedInverseProbabilityWeighting
    return dict(status='OFFLINE_ESTIMATE', diagnostics=diagnostics,
                ipw=float(InverseProbabilityWeighting().estimate_policy_value(**data)),
                snipw=float(SelfNormalizedInverseProbabilityWeighting().estimate_policy_value(**data)))
