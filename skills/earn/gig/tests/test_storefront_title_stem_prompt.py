"""The create prompt must name every way a title stem is refused, not just one of them.

The guard rejects a stem whose last character is not a verb continuative. The prompt warned
about one shape -- a bare noun like `...アプリ` -- and production then produced
`...FAQ自動応答Botを` and `...予約・自動応答Botを` on two separate wakes: noun phrases whose
verb was simply missing. A rule the model is never told is a rule it will keep breaking.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import storefront_direct as direct  # noqa: E402

SOURCE = (SCRIPTS / "storefront_direct.py").read_text(encoding="utf-8")


# The guard is a character check, so it can only refuse the particles that are not also a
# verb's continuative form. に, で and へ are both -- 死に, 出で -- so they are legal endings
# and the prompt must not claim otherwise.
REFUSED = ["を", "の", "が", "は", "と"]
AMBIGUOUS = ["に", "で", "へ"]


@pytest.mark.parametrize("particle", REFUSED)
def test_the_prompt_names_every_particle_the_guard_refuses(particle):
    assert f"`{particle}`" in SOURCE


def test_the_prompt_shows_the_stem_production_actually_produced():
    assert "FAQ自動応答Botを" in SOURCE
    assert "Botを構築し" in SOURCE


def test_the_prompt_still_covers_the_bare_noun_case():
    assert "...アプリ" in SOURCE
    assert "アプリます" in SOURCE


@pytest.mark.parametrize("particle", REFUSED)
def test_the_refused_particles_really_are_refused_by_the_guard(particle):
    # Tie prompt and guard together: a particle the prompt calls refused must actually be
    # absent from the constant, or the prompt is teaching the model something false.
    assert particle not in direct.TITLE_STEM_CONTINUATIVE_ENDINGS


@pytest.mark.parametrize("particle", AMBIGUOUS)
def test_the_ambiguous_particles_are_legal_and_the_prompt_says_why(particle):
    assert particle in direct.TITLE_STEM_CONTINUATIVE_ENDINGS
    assert "死に" in SOURCE and "出で" in SOURCE


def test_the_examples_the_prompt_offers_would_actually_pass_the_guard():
    for stem in ("Botを構築し", "応答を自動化し", "設定を代行し", "アプリを開発し", "システムを構築し"):
        assert stem[-1] in direct.TITLE_STEM_CONTINUATIVE_ENDINGS, stem
