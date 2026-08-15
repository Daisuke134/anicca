from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "domain_skills.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("domain_skills", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# §CC' (2026-08-09, C3): the capability-fit rule (no-go on 実写素材の編集を募集する出品)
# must gate NEW listing creation. B0 is the lane that publishes/creates/updates listings
# (gig_pass.sh: action must be published/created/updated/verified_noop). The rule text
# already lives in domain-skills/coconala.md's ## 出品 section (seeded by C2); this is a
# characterization test for the wiring that makes B0's prompt actually carry it -- mirrors
# the same pattern C2 used for PAID_WORK/納品の制約 (test_domain_skills_google_docs.py).
# If the heading or the BY_STEP inclusion for B0 ever drift apart, B0 silently stops
# knowing the rule exists and can republish the same ★1-causing listing.


def test_b0_fragment_includes_the_capability_fit_no_go_line() -> None:
    m = load_module()
    fragment = m.fragment("B0", limit=0)
    assert "実写素材の編集を募集する出品を公開しない" in fragment
    assert "application_planner.py" in fragment


def test_the_no_go_line_lives_under_shuppin_not_a_dropped_section() -> None:
    m = load_module()
    body = m.load("coconala")
    listing_section = m.sections(body, ("出品",))
    assert "実写素材の編集を募集する出品を公開しない" in listing_section


def test_b2_does_not_get_the_shuppin_section() -> None:
    # B2 (応募/apply) never publishes a listing, so it must not pay the prompt cost for a
    # listing-creation capability it cannot use -- same split C2 already established.
    m = load_module()
    fragment = m.fragment("B2", limit=0)
    assert "実写素材の編集を募集する出品を公開しない" not in fragment
