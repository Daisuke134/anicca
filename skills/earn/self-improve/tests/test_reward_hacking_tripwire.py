"""Required test 4 (delegated task spec): an implausible fitness jump (>3x the population's
best-ever score) is flagged for adversary review, not silently auto-promoted. Reward-hacking
`combined_score` is also always reward-capped so a single outlier can never dominate selection.

Traces to behavioral-spec.md REQ-RH1 (Lilian Weng, "Reward Hacking in Reinforcement Learning" —
reward capping) and REQ-RH2 (Anthropic, "Sycophancy to Subterfuge" — implausible self-reported
jumps must be routed to adversary review before any promotion). verification-architecture.md
PROP-SI-RH1/RH2.
"""
import evaluator
from lib import gate_math


def test_implausible_jump_over_3x_population_best_is_flagged():
    population_best = 100.0
    candidate_score = 350.0  # 3.5x population_best

    result = evaluator.tripwire_check(candidate_score, population_best)

    assert result["flagged"] is True


def test_score_within_3x_population_best_is_not_flagged():
    population_best = 100.0
    candidate_score = 250.0  # 2.5x population_best — a genuine improvement, not implausible

    result = evaluator.tripwire_check(candidate_score, population_best)

    assert result["flagged"] is False


def test_flagged_candidate_is_never_silently_promoted_even_if_other_gates_pass():
    # A candidate that trips the reward-hacking wire must fail the promotion gate regardless of
    # how good its stage1/stage2 numbers otherwise look — tripwire_clear=False blocks it alone.
    tripwire_result = evaluator.tripwire_check(candidate_score=1000.0, population_best=50.0)
    assert tripwire_result["flagged"] is True

    promotable = gate_math.stage_gate(
        stage1_pass=True,
        stage2_pass=True,
        tripwire_clear=not tripwire_result["flagged"],
        adversary_verdict="PASS",
    )
    assert promotable is False


def test_combined_score_is_never_reported_above_the_configured_ceiling():
    result = evaluator.tripwire_check(candidate_score=10_000.0, population_best=1.0)

    assert result["capped_score"] == evaluator.COMBINED_SCORE_CEILING


def test_apply_score_cap_never_exceeds_ceiling_for_any_raw_score():
    for raw_score in (-500.0, -1.0, 0.0, 1.0, 499.9, 500.0, 500.1, 999999.0):
        capped = gate_math.apply_score_cap(raw_score, ceiling=500.0)
        assert capped <= 500.0


def test_is_implausible_jump_boundary_is_strict_greater_than():
    # exactly 3x is NOT implausible (strict > per gate_math.is_implausible_jump); a hair above is.
    assert gate_math.is_implausible_jump(300.0, 100.0, multiple=3.0) is False
    assert gate_math.is_implausible_jump(300.01, 100.0, multiple=3.0) is True


def test_non_positive_population_best_never_fires_this_specific_tripwire():
    # No meaningful positive multiple of a non-positive baseline exists; this predicate simply
    # does not fire in that case (other gates still apply independently at the orchestration
    # layer — this is scoped to the ">3x population-best" jump check only).
    assert gate_math.is_implausible_jump(1000.0, 0.0) is False
    assert gate_math.is_implausible_jump(1000.0, -5.0) is False
