from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path


# The reason no application has been recorded in 70 hours.
#
# After clicking 応募する the parent slept a fixed 0.75 seconds and read the page once. A
# submit that takes longer than that to navigate was therefore scored as "still on the form",
# so click_submit retried — and by then the browser had arrived at
# /mypage/job_matching/applied/offers, where there is correctly no 応募する button. That
# produced application_応募する_button_missing on a submit that had actually worked.
#
# Both shapes are visible in one pass, 1785933016-8154. Request 91000100 has a control-missing
# record whose URL is the applied-offers list, showing our live applications — it landed.
# Request 91000095 has a submit-attempt screenshot still showing the confirmation modal after
# three tries, with an 80,000円 proposal filled in.
#
# So the wait has to be a poll with a deadline, not a guess. 0.75s was a guess about how fast
# Coconala navigates.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "application_parent.py"


def load_module():
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("application_parent", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


APPLIED = "https://coconala.com/mypage/job_matching/applied/offers"
FORM = "https://coconala.com/offers/add/91000095?&_t=1"


def reader(sequence: list[str]):
    """A page whose URL becomes each value in turn, one reading at a time."""
    state = {"i": 0}

    async def read():
        i = min(state["i"], len(sequence) - 1)
        state["i"] += 1
        return {"url": sequence[i], "body": ""}

    return read


def settle(m, sequence, seconds=2.0):
    return asyncio.run(
        m.settle_after_click(reader(sequence), m.submit_landed, deadline_seconds=seconds, interval=0.01)
    )


def test_a_navigation_that_arrives_late_is_still_seen() -> None:
    # Three readings on the form, then the applied list. Under the old fixed sleep this was a
    # failed submit; it is a successful one.
    m = load_module()
    assert settle(m, [FORM, FORM, FORM, APPLIED])["url"] == APPLIED


def test_an_immediate_navigation_returns_at_once() -> None:
    m = load_module()
    assert settle(m, [APPLIED])["url"] == APPLIED


def test_a_page_that_never_navigates_returns_what_it_saw() -> None:
    # The confirmation modal case: the click did nothing. The caller still needs the last
    # observation so it can screenshot it and decide, rather than getting an exception.
    m = load_module()
    assert settle(m, [FORM], seconds=0.05)["url"] == FORM


def test_it_does_not_wait_forever() -> None:
    m = load_module()
    started = asyncio.get_event_loop_policy().new_event_loop().time()
    result = settle(m, [FORM], seconds=0.05)
    assert result["url"] == FORM  # returned rather than hung
