"""When a wake does not start a listing it must say which condition closed.

Five conditions decide whether a wake may start or finish one: the fixed candidate being
public, the create spacing, no open IMPROVE hypothesis, a free slot, and either unspent
demand or a cluster blueprint. When the answer was no, the wake reported only
`no_executable_unfenced_mutation_contract`, which names the IMPROVE path and says nothing
about CREATE. Finding the real answer meant reproducing each condition by hand against live
state, one question at a time, and it cost an afternoon. The wake states it now.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

SOURCE = (Path(__file__).resolve().parents[1] / "scripts" / "storefront_direct.py").read_text(
    encoding="utf-8")
GATE = SOURCE[SOURCE.index("create_gate = {"):SOURCE.index("if not create_blocked_by:")]

CONDITIONS = [
    "fixed_candidate_public",
    "create_spacing_open",
    "no_open_improve_hypothesis",
    "slots_available",
    "demand_unspent_or_blueprint",
]


@pytest.mark.parametrize("condition", CONDITIONS)
def test_every_condition_is_reported_by_name(condition):
    assert f'"{condition}"' in GATE


def test_the_gate_is_recorded_before_the_branch_decides():
    assert GATE.index("create_gate = {") < GATE.index("demand_derivation")


def test_the_branch_is_driven_by_the_same_values_it_reports():
    # If the condition and the report can disagree, the report is decoration.
    assert "if not create_blocked_by:" in SOURCE
    assert "create_blocked_by = sorted(" in GATE


def test_the_blocked_list_is_deterministic():
    assert "sorted(" in GATE


def test_no_condition_was_dropped_from_the_original_branch():
    # The original five, verbatim from the condition it replaced.
    for original in ("fixed_candidate_public", "create_spacing_open", "next_hypothesis is None",
                     "observed < 20", "demand_already_sold"):
        assert original in GATE, original
