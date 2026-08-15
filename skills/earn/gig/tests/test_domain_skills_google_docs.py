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


# §EM' (2026-08-09): the Google-Docs-delivery capability is wired into the PAID_WORK
# builder prompt purely through domain-skills/coconala.md's 納品の制約 section --
# gig_pass.sh itself is untouched. This is a characterization test for that wiring: if
# the section heading, the script path, or the BY_STEP inclusion for PAID_WORK ever
# drift apart, the builder silently stops knowing this capability exists, exactly the
# "success with zero work is a wiring gap" failure mode.


def test_paid_work_fragment_includes_the_google_docs_publisher_usage_line() -> None:
    m = load_module()
    fragment = m.fragment("PAID_WORK", limit=0)
    assert "google_docs_publisher.py" in fragment
    assert "google_doc_link" in fragment
    assert "グーグルドキュメントで" in fragment


def test_the_capability_line_lives_under_delivery_constraints_not_a_dropped_section() -> None:
    m = load_module()
    body = m.load("coconala")
    delivery_section = m.sections(body, ("納品の制約",))
    assert "google_docs_publisher.py" in delivery_section


def test_b2_does_not_get_the_delivery_constraints_section(tmp_path) -> None:
    # B2 (応募/apply) never delivers, so it must not pay the prompt cost for a delivery
    # capability it cannot use -- same reasoning the module's own docstring gives for
    # every other section split.
    m = load_module()
    fragment = m.fragment("B2", limit=0)
    assert "google_docs_publisher.py" not in fragment
