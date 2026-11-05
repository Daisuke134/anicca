"""P04-2: randomized controlled trials and intention-to-treat.

All participants and outcomes are synthetic. No user data, external API, or live experiment.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
import numpy as np
from scipy.stats import norm


@dataclass(frozen=True)
class Estimate:
    n_treatment: int
    n_control: int
    treatment_mean: float
    control_mean: float
    risk_difference: float
    standard_error: float
    ci_95_low: float
    ci_95_high: float


def make_population(n: int, rng: np.random.Generator):
    """Define BOTH potential outcomes only because this is an imaginary world.

    High-interest users: P(Y0=1)=0.8, P(Y1=1)=0.7
    Low-interest users:  P(Y0=1)=0.2, P(Y1=1)=0.1
    U and Y0/Y1 are not simultaneously observable in real-world trials.
    """
    interest = rng.binomial(1, 0.5, size=n)
    p0 = np.where(interest == 1, 0.8, 0.2)
    p1 = p0 - 0.1
    shock = rng.random(n)
    y0 = (shock < p0).astype(int)
    y1 = (shock < p1).astype(int)
    return interest, y0, y1


def complete_random_assignment(n: int, rng: np.random.Generator) -> np.ndarray:
    """Exactly half assigned to treatment, independently from any user feature."""
    if n % 2:
        raise ValueError('n must be even')
    z = np.zeros(n, dtype=int)
    z[:n // 2] = 1
    rng.shuffle(z)
    return z


def difference_of_means(assignment: np.ndarray, observed: np.ndarray) -> Estimate:
    """A simple unadjusted difference and illustrative independent-arm Wald CI."""
    z = np.asarray(assignment)
    y = np.asarray(observed, dtype=float)
    if len(z) != len(y) or not len(y):
        raise ValueError('assignment and results must have equal nonzero length')
    if not np.all(np.isin(z, [0, 1])) or not np.all(np.isfinite(y)):
        raise ValueError('binary assignment and finite outcomes required')
    y1 = y[z == 1]
    y0 = y[z == 0]
    if len(y1) < 2 or len(y0) < 2:
        raise ValueError('each group must have at least two observations')
    m1, m0 = y1.mean(), y0.mean()
    se = np.sqrt(y1.var(ddof=1) / len(y1) + y0.var(ddof=1) / len(y0))
    d = float(m1 - m0)
    q = norm.ppf(0.975)
    return Estimate(len(y1), len(y0), float(m1), float(m0), d, float(se),
                    float(d - q * se), float(d + q * se))


def normal_approx_per_arm_n(p0: float, p1: float, power: float = 0.80,
                            alpha: float = 0.05) -> int:
    """Normal approximation for two independent binary proportions with equal groups.

    An educational planning formula, not an audited sample-size calculator for a trial.
    """
    if not 0 < p0 < 1 or not 0 < p1 < 1 or p0 == p1:
        raise ValueError('two different probabilities strictly between 0 and 1 required')
    if not 0 < power < 1 or not 0 < alpha < 1:
        raise ValueError('invalid power or alpha')
    pbar = (p0 + p1) / 2
    numerator = (norm.ppf(1 - alpha / 2) * np.sqrt(2 * pbar * (1 - pbar)) +
                 norm.ppf(power) * np.sqrt(p0 * (1 - p0) + p1 * (1 - p1))) ** 2
    return int(np.ceil(numerator / (p1 - p0) ** 2))


def run(n: int = 20_000, seed: int = 20261104, monte_carlo_reps: int = 600,
        rep_n: int = 2000) -> dict:
    rng = np.random.default_rng(seed)
    interest, y0, y1 = make_population(n, rng)
    oracle = float((y1 - y0).mean())

    # Selection bias: motivated people are more likely to opt in to a message.
    p_notification = np.where(interest == 1, 0.8, 0.2)
    a_obs = rng.binomial(1, p_notification)
    naive_observed = np.where(a_obs == 1, y1, y0)
    observational = difference_of_means(a_obs, naive_observed)

    # Random assignment is unrelated to interest; analyze by assignment.
    z = complete_random_assignment(n, rng)
    y_rct = np.where(z == 1, y1, y0)
    rct = difference_of_means(z, y_rct)

    # Some people assigned an offer don't receive it; adherence depends on interest.
    uptake_probability = np.where(interest == 1, 0.95, 0.75)
    received = z * (rng.random(n) < uptake_probability)
    y_with_noncompliance = np.where(received == 1, y1, y0)
    itt = difference_of_means(z, y_with_noncompliance)
    as_treated = difference_of_means(received, y_with_noncompliance)

    # Replicate entire hypothetical experiments to show sampling variability.
    effects, covered = [], 0
    for _ in range(monte_carlo_reps):
        _, ry0, ry1 = make_population(rep_n, rng)
        rz = complete_random_assignment(rep_n, rng)
        ry = np.where(rz == 1, ry1, ry0)
        est = difference_of_means(rz, ry)
        effects.append(est.risk_difference)
        if est.ci_95_low <= -0.10 <= est.ci_95_high:
            covered += 1

    effects_arr = np.asarray(effects)
    report = dict(
        note='Everything in this file is a synthetic pedagogical experiment; not real human A/B results.',
        scenario='Both groups are 50% high-interest/50% low-interest. Treatment reduces success probability by 10 pp.',
        n=n, seed=seed,
        true_ate_by_construction=-0.1,
        oracle_realized_ate=oracle,
        observational=asdict(observational),
        randomized=asdict(rct),
        noncompliance={
            'uptake_among_assigned': float(received[z == 1].mean()),
            'itt_by_assignment': asdict(itt),
            'as_treated_selection_biased': asdict(as_treated)
        },
        repeated_rcts={
            'repetitions': monte_carlo_reps,
            'people_per_rep': rep_n,
            'estimated_ate_mean': float(effects_arr.mean()),
            'estimated_ate_sd': float(effects_arr.std(ddof=1)),
            'illustrative_95pct_interval_coverage_for_true_minus_0_1': covered / monte_carlo_reps,
            'quantiles_025_50_975': [float(q) for q in np.quantile(effects_arr, [.025, .5, .975])],
            'raw_estimates': effects,
        },
        sample_size_planning={
            'effect_50_to_40_percent': normal_approx_per_arm_n(.5, .4),
            'effect_4_to_6_percent': normal_approx_per_arm_n(.04, .06),
            'alpha': .05, 'nominal_power': .8, 'note': 'Approximate, assumes independent units, 1:1 allocation and no attrition/interference.'
        }
    )
    return report


if __name__ == '__main__':
    output = Path(__file__).resolve().parents[1] / 'evidence' / 'p04_2_rct_ate_result.json'
    data = run()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    short = {k: (v if k != 'repeated_rcts' else {kk: vv for kk, vv in v.items() if kk != 'raw_estimates'}) for k, v in data.items()}
    print(json.dumps(short, ensure_ascii=False, indent=2))
