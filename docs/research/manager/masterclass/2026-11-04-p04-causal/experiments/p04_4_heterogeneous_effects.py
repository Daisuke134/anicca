"""P04-4: Heterogeneous causal effects and a mediation illustration.

ALL observations are synthetic. No actual notification or user action occurs.
Python 3.11+; NumPy. Run from the experiments directory.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

SEED = 20261144
N = 24_000


def simulate_population(n: int = N, seed: int = SEED) -> dict[str, np.ndarray]:
    """Generate a randomized trial with known subgroup-specific effects."""
    if n < 100:
        raise ValueError("n must be at least 100")
    rng = np.random.default_rng(seed)
    motivation = rng.integers(0, 2, size=n)
    fatigue = rng.integers(0, 2, size=n)
    p0 = 0.22 + 0.18 * motivation - 0.05 * fatigue
    tau = 0.16 - 0.20 * motivation - 0.06 * fatigue
    p1 = p0 + tau
    assert np.all((p0 > 0) & (p0 < 1))
    assert np.all((p1 > 0) & (p1 < 1))
    # Shared latent rank couples the two potential outcomes in this toy world.
    u = rng.random(n)
    y0 = (u < p0).astype(int)
    y1 = (u < p1).astype(int)
    assignment = rng.integers(0, 2, size=n)
    observed = np.where(assignment == 1, y1, y0)
    train = rng.random(n) < 0.6
    return dict(
        motivation=motivation, fatigue=fatigue, p0=p0, p1=p1, tau=tau,
        assignment=assignment, outcome=observed, oracle_y0=y0,
        oracle_y1=y1, train=train,
    )


def compare_means(y: np.ndarray, a: np.ndarray) -> dict[str, float]:
    """Difference of randomized group means and a Wald 95% interval."""
    treated = y[a == 1]
    control = y[a == 0]
    if len(treated) < 2 or len(control) < 2:
        raise ValueError("Both randomized groups need at least two observations")
    diff = float(np.mean(treated) - np.mean(control))
    se = float(np.sqrt(np.var(treated, ddof=1) / len(treated)
                       + np.var(control, ddof=1) / len(control)))
    return dict(effect=diff, se=se, ci95=[diff - 1.96 * se, diff + 1.96 * se],
                n_treated=len(treated), n_control=len(control))


def subgroup_table(data: dict[str, np.ndarray], select: np.ndarray | None = None) -> list[dict]:
    """Prespecified 2x2 subgroup CATE estimates, not individual causal effects."""
    n = len(data["outcome"])
    include = np.ones(n, dtype=bool) if select is None else select
    rows = []
    for m in (0, 1):
        for f in (0, 1):
            mask = include & (data["motivation"] == m) & (data["fatigue"] == f)
            row = compare_means(data["outcome"][mask], data["assignment"][mask])
            row.update(
                motivation=m, fatigue=f, n=int(np.sum(mask)),
                oracle_cate=float(np.mean(data["tau"][mask])),
            )
            rows.append(row)
    return rows


def learn_policy(data: dict[str, np.ndarray]) -> dict[tuple[int, int], int]:
    """Build a prespecified four-cell rule using training observations only."""
    return {
        (r["motivation"], r["fatigue"]): int(r["effect"] > 0)
        for r in subgroup_table(data, data["train"])
    }


def evaluate_policy(data: dict[str, np.ndarray], policy: dict[tuple[int, int], int]) -> dict:
    """Use only fresh held-out randomized outcomes for IPW policy evaluation."""
    holdout = ~data["train"]
    a = data["assignment"][holdout]
    y = data["outcome"][holdout]
    keys = zip(data["motivation"][holdout], data["fatigue"][holdout])
    chosen = np.fromiter((policy[(int(m), int(f))] for m, f in keys),
                         dtype=int, count=len(a))
    # Assignment probability is 1/2 by construction.
    z_policy = 2 * (a == chosen) * y
    z_none = 2 * (a == 0) * y
    gain = z_policy - z_none
    se = float(np.std(gain, ddof=1) / np.sqrt(len(gain)))
    tau = data["tau"][holdout]
    oracle_gain = float(np.mean(tau * chosen))
    return {
        "n_holdout": int(np.sum(holdout)),
        "selection_rule": {f"motivation={m},fatigue={f}": int(v)
                           for (m, f), v in policy.items()},
        "heldout_ipw_policy_value": float(np.mean(z_policy)),
        "heldout_ipw_never_notify_value": float(np.mean(z_none)),
        "heldout_ipw_gain": float(np.mean(gain)),
        "heldout_gain_se": se,
        "heldout_gain_ci95": [float(np.mean(gain) - 1.96 * se),
                              float(np.mean(gain) + 1.96 * se)],
        "synthetic_oracle_policy_gain": oracle_gain,
        "synthetic_oracle_always_notify_gain": float(np.mean(tau)),
        "synthetic_oracle_best_four_cell_gain": float(np.mean(np.maximum(tau, 0))),
    }


def mediation_example(n: int = 20_000, seed: int = SEED + 1) -> dict:
    """A linear structural model illustration; not proof of real-world mediation."""
    rng = np.random.default_rng(seed)
    x = rng.integers(0, 2, size=n)
    a = rng.integers(0, 2, size=n)
    # M = alpha0 + alpha_A*A + alpha_X*X + independent error
    m = 0.15 + 0.30 * a + 0.08 * x + rng.normal(0, 0.15, n)
    # Y = beta0 + beta_A*A + beta_M*M + beta_X*X + independent error
    y = 1.0 + 0.12 * a + 0.40 * m + 0.07 * x + rng.normal(0, 0.25, n)
    alpha = np.linalg.lstsq(np.column_stack([np.ones(n), a, x]), m, rcond=None)[0]
    beta = np.linalg.lstsq(np.column_stack([np.ones(n), a, m, x]), y, rcond=None)[0]
    indirect = float(alpha[1] * beta[2])
    direct = float(beta[1])
    return {
        "n": n, "true_direct_effect": 0.12, "true_indirect_effect": 0.12,
        "true_total_effect": 0.24,
        "estimated_direct_effect": direct,
        "estimated_indirect_effect": indirect,
        "estimated_total_effect": direct + indirect,
        "caution": "Randomized A alone does not identify natural mediation without further assumptions.",
    }


def run(n: int = N, seed: int = SEED) -> dict:
    data = simulate_population(n, seed)
    ate = compare_means(data["outcome"], data["assignment"])
    policy = learn_policy(data)
    return {
        "study": "P04-4 synthetic CATE / mediation only",
        "n": n,
        "seed": seed,
        "estimand": "CATE by two pre-intervention binary variables; ATE over population",
        "true_population_ate": float(np.mean(data["tau"])),
        "estimated_ate": ate,
        "subgroups": subgroup_table(data),
        "heldout_policy": evaluate_policy(data, policy),
        "mediation": mediation_example(),
    }


def export(out_dir: str | Path) -> dict:
    base = Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)
    report = run()
    (base / "P04-4_SYNTHETIC_RESULTS.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    data = simulate_population()
    path = base / "P04-4_SYNTHETIC_DATA.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["synthetic_person_id", "motivation_pre", "fatigue_pre",
                         "random_assignment", "observed_outcome", "train_split",
                         "oracle_probability_no_treatment",
                         "oracle_probability_treatment", "oracle_cate"])
        for i in range(len(data["outcome"])):
            writer.writerow([i + 1, int(data["motivation"][i]),
                             int(data["fatigue"][i]), int(data["assignment"][i]),
                             int(data["outcome"][i]), int(data["train"][i]),
                             f'{data["p0"][i]:.4f}', f'{data["p1"][i]:.4f}',
                             f'{data["tau"][i]:.4f}'])
    return report


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent.parent / "evidence"
    result = export(folder)
    print(json.dumps(result, ensure_ascii=False, indent=2))
