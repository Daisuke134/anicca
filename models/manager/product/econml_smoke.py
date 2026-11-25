"""Synthetic CATE audit; no actual user or deployment evidence."""
import argparse
import json
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import HistGradientBoostingRegressor


def run(backend, seed):
    rng = np.random.default_rng(seed)
    x = rng.normal(size=(6000, 3))
    t = rng.binomial(1, .5, len(x))
    tau = .3 + .8*x[:, 0] - .6*x[:, 1]**2
    mu = 1 + x[:, 0] + .5*x[:, 2]
    y = mu + t*tau + rng.normal(size=len(x))
    a, b = slice(0, 4000), slice(4000, None)
    xx, tt, yy = x[a], t[a], y[a]
    test, truth = x[b], tau[b]
    models = {'linear': LinearRegression(), 'hgb': HistGradientBoostingRegressor(max_iter=100, max_leaf_nodes=15, random_state=seed)}
    scores = {'ate': np.full(len(test), yy[tt==1].mean()-yy[tt==0].mean())}
    for name, model in models.items():
        if backend == 'econml':
            from econml.metalearners import TLearner
            scores[name] = TLearner(models=model).fit(yy, tt, X=xx).effect(test)
        elif backend == 'reference':
            from sklearn.base import clone
            m0 = clone(model).fit(xx[tt==0], yy[tt==0])
            m1 = clone(model).fit(xx[tt==1], yy[tt==1])
            scores[name] = m1.predict(test)-m0.predict(test)
        else:
            raise ValueError('unknown backend')
    cost = .1
    oracle = np.maximum(truth-cost, 0).mean()
    return {name: {'pehe': float(np.sqrt(np.mean((s-truth)**2))), 'policy_regret': float(oracle-np.mean((s>cost)*(truth-cost))), 'treat_rate': float(np.mean(s>cost))} for name,s in scores.items()}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--backend', choices=['reference','econml'], required=True)
    a = p.parse_args()
    runs = [run(a.backend, seed) for seed in range(5)]
    summary = {arm: {m: float(np.mean([r[arm][m] for r in runs])) for m in runs[0][arm]} for arm in runs[0]}
    print(json.dumps({'backend':a.backend,'scope':'synthetic only','seeds':list(range(5)),'train_per_seed':4000,'test_per_seed':2000,'runs':runs,'mean':summary}, indent=2))
