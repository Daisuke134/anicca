"""P04-3: observational causal inference on synthetic persons only.

Fixed artificial DGP:
 P(U=1)=0.5; P(A=1|U=1)=0.8, P(A=1|U=0)=0.2
 P(Y(0)=1|U=1)=0.8; P(Y(0)=1|U=0)=0.2
 P(Y(1)=1|U=1)=0.7; P(Y(1)=1|U=0)=0.1
 Theoretical observational difference: +.26; theoretical ATE: -.10.
 No real users or interventions; Y(0) and Y(1) known only in simulator.
"""

from dataclasses import dataclass
import argparse
import json
import numpy as np


@dataclass(frozen=True)
class SyntheticData:
    u: np.ndarray
    a: np.ndarray
    y: np.ndarray
    y0: np.ndarray
    y1: np.ndarray


def simulate(n: int = 30_000, seed: int = 20261104) -> SyntheticData:
    """Generate observational treatment confounded by pre-treatment intent U."""
    if n < 20:
        raise ValueError("n should be at least 20 for this demonstration")
    rng = np.random.default_rng(seed)
    u = rng.binomial(1, 0.5, size=n)
    propensity = np.where(u == 1, 0.8, 0.2)
    a = rng.binomial(1, propensity)
    p0 = np.where(u == 1, 0.8, 0.2)
    p1 = np.where(u == 1, 0.7, 0.1)
    common_uniform = rng.random(n)
    y0 = (common_uniform < p0).astype(int)
    y1 = (common_uniform < p1).astype(int)
    y = np.where(a == 1, y1, y0)
    return SyntheticData(u=u, a=a, y=y, y0=y0, y1=y1)


def naive_difference(y: np.ndarray, a: np.ndarray) -> float:
    """Associational difference: not generally a causal effect."""
    if not np.any(a == 1) or not np.any(a == 0):
        raise ValueError("both treatment groups are needed")
    return float(y[a == 1].mean() - y[a == 0].mean())


def stratum_means(y: np.ndarray, a: np.ndarray, u: np.ndarray):
    """Fit saturated P(Y=1 | A=a, U=u) in two observed strata."""
    means = {}
    for level in (0, 1):
        for action in (0, 1):
            cell = (u == level) & (a == action)
            if not np.any(cell):
                raise ValueError("positivity violation: empty stratum x action cell")
            means[(level, action)] = float(y[cell].mean())
    return means


def standardize(y: np.ndarray, a: np.ndarray, u: np.ndarray) -> float:
    """g-formula over the target population's empirical P(U)."""
    m = stratum_means(y, a, u)
    return float(sum(np.mean(u == level) * (m[(level, 1)] - m[(level, 0)])
                     for level in (0, 1)))


def outcome_regression(y: np.ndarray, a: np.ndarray, u: np.ndarray) -> float:
    """OLS g-computation with saturated 1, A, U, A*U regressors."""
    x = np.column_stack((np.ones(len(y)), a, u, a * u)).astype(float)
    beta, *_ = np.linalg.lstsq(x, y.astype(float), rcond=None)
    x1 = np.column_stack((np.ones(len(y)), np.ones(len(y)), u, u))
    x0 = np.column_stack((np.ones(len(y)), np.zeros(len(y)), u, np.zeros(len(y))))
    return float(np.mean(x1 @ beta - x0 @ beta))


def estimate_propensity(a: np.ndarray, u: np.ndarray) -> np.ndarray:
    """Estimate P(A=1|U) by stratum frequency; do not peek at Y."""
    prop = np.zeros(len(u), dtype=float)
    for level in (0, 1):
        cell = u == level
        if not np.any(cell):
            raise ValueError("empty U stratum")
        prop[cell] = a[cell].mean()
    return prop


def validate_overlap(e: np.ndarray, threshold: float = 0.0) -> None:
    """Detect absent overlap and optional near-deterministic treatment."""
    if not np.all(np.isfinite(e)) or np.any(e <= threshold) or np.any(e >= 1 - threshold):
        raise ValueError("positivity/overlap violation: some propensities too close to 0 or 1")


def ipw_hajek(y: np.ndarray, a: np.ndarray, e: np.ndarray) -> float:
    """Normalized inverse-propensity weighting, often called Hájek IPW."""
    validate_overlap(e)
    treated = (a == 1).astype(float) / e
    control = (a == 0).astype(float) / (1 - e)
    if treated.sum() == 0 or control.sum() == 0:
        raise ValueError("missing treatment group")
    return float(np.sum(treated * y) / np.sum(treated) -
                 np.sum(control * y) / np.sum(control))


def aipw(y: np.ndarray, a: np.ndarray, e: np.ndarray,
         m0: np.ndarray, m1: np.ndarray) -> float:
    """Augmented IPW. Double robustness needs at least one correct nuisance model.

    AIPW also requires causal identification, overlap, and appropriate inference;
    this educational version does not implement cross-fitting.
    """
    validate_overlap(e)
    scores = (m1 - m0 + a * (y - m1) / e - (1 - a) * (y - m0) / (1 - e))
    return float(scores.mean())


def predict_outcomes(y: np.ndarray, a: np.ndarray, u: np.ndarray):
    """Return fitted potential outcome means m0(U), m1(U) from strata."""
    m = stratum_means(y, a, u)
    return (np.where(u == 1, m[(1, 0)], m[(0, 0)]),
            np.where(u == 1, m[(1, 1)], m[(0, 1)]))


def exact_match_att(y: np.ndarray, a: np.ndarray, u: np.ndarray,
                    seed: int = 700) -> float:
    """Nearest exact-match (U) with replacement; this estimates ATT, not ATE."""
    rng = np.random.default_rng(seed)
    treated_ids = np.where(a == 1)[0]
    matched_controls = []
    for level in (0, 1):
        treated = treated_ids[u[treated_ids] == level]
        controls = np.where((a == 0) & (u == level))[0]
        if len(treated) and not len(controls):
            raise ValueError("no matching controls for this treated stratum")
        matched_controls.extend(zip(treated.tolist(), rng.choice(controls, size=len(treated), replace=True).tolist()))
    if not matched_controls:
        raise ValueError("no treated units")
    pairs = np.asarray(matched_controls, dtype=int)
    return float(np.mean(y[pairs[:, 0]] - y[pairs[:, 1]]))


def did(pre_treat: float, post_treat: float,
        pre_control: float, post_control: float) -> float:
    """Two-group, two-period DiD; causal only under identification assumptions."""
    vals = (pre_treat, post_treat, pre_control, post_control)
    if any(not (0 <= v <= 1) for v in vals):
        raise ValueError("rates must lie between 0 and 1")
    return (post_treat - pre_treat) - (post_control - pre_control)


def bootstrap_standardized_ci(d: SyntheticData, replicates: int = 250,
                              seed: int = 20261105):
    """Naive iid individual resampling; cluster/time dependence needs other SE."""
    if replicates < 50:
        raise ValueError("at least 50 replications for a teaching percentile interval")
    rng = np.random.default_rng(seed)
    samples = []
    n = len(d.y)
    for _ in range(replicates):
        idx = rng.integers(0, n, size=n)
        samples.append(standardize(d.y[idx], d.a[idx], d.u[idx]))
    return tuple(float(v) for v in np.quantile(samples, [0.025, 0.975]))


def report(n: int = 30_000, seed: int = 20261104, bootstrap_reps: int = 250) -> dict:
    d = simulate(n=n, seed=seed)
    e = estimate_propensity(d.a, d.u)
    m0, m1 = predict_outcomes(d.y, d.a, d.u)
    # Imperfect proxy for U: 75% agreement, hence residual confounding.
    rng = np.random.default_rng(seed + 1)
    proxy = np.where(rng.random(n) < 0.75, d.u, 1 - d.u)
    result = {
        "dataset": "fully synthetic observations, no real interventions",
        "n": n, "seed": seed,
        "theoretical_naive_difference": 0.26,
        "theoretical_ATE": -0.10,
        "sample_oracle_ATE_simulator_only": float(np.mean(d.y1 - d.y0)),
        "naive_observational_difference": naive_difference(d.y, d.a),
        "g_formula_standardization": standardize(d.y, d.a, d.u),
        "saturated_ols_g_computation": outcome_regression(d.y, d.a, d.u),
        "ipw_hajek": ipw_hajek(d.y, d.a, e),
        "aipw_no_crossfitting": aipw(d.y, d.a, e, m0, m1),
        "exact_match_ATT": exact_match_att(d.y, d.a, d.u),
        "imperfect_proxy_adjustment_NOT_IDENTIFIED": standardize(d.y, d.a, proxy),
        "propensity_min": float(e.min()), "propensity_max": float(e.max()),
        "iid_bootstrap_gformula_95pct_CI": bootstrap_standardized_ci(d, bootstrap_reps),
        "separate_did_toy_example": did(0.30, 0.38, 0.20, 0.25),
    }
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=30_000)
    parser.add_argument("--seed", type=int, default=20261104)
    parser.add_argument("--bootstrap-reps", type=int, default=250)
    parser.add_argument("--output", default=None)
    opts = parser.parse_args()
    results = report(n=opts.n, seed=opts.seed, bootstrap_reps=opts.bootstrap_reps)
    result_json = json.dumps(results, ensure_ascii=False, indent=2)
    print(result_json)
    if opts.output:
        from pathlib import Path
        Path(opts.output).write_text(result_json + "\n", encoding="utf-8")
