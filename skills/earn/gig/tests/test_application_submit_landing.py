from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# The application lane was applying successfully and reporting failure.
#
# Measured 2026-08-05 from the loop's own evidence: 41 passes died with
# application_応募する_button_missing, and 37 of those were sitting on
# /mypage/job_matching/applied/offers — the page Coconala sends you to *after* a submit
# succeeds. The saved screenshot of that page shows our live applications: johnsuzuki
# 40,000円, Mei Onoda 3,000円, himawari19900707 50,000円, CATRADER 450,000円, and a
# WordPress job at 200,000円, each with an 編集する control because they are submitted.
#
# The cause is click_submit's success test: it required the string 応募しました in the body
# on top of the URL. That string is a toast, and a toast is gone by the time the page is
# read. So the submit was scored as failed, retried — and on the applied-offers page there
# is correctly no 応募する button, which produced button_missing, failed the pass, skipped
# the heartbeat, and left the auditor reporting a stopped cron for 42 hours.
#
# Relaxing this does not weaken the guarantee. The authoritative check is
# _official_readback_async, which loads the applied-offers page and requires the offer id to
# appear in a[href*="/mypage/offers/"]. Landing is the site's answer to the click; the
# readback is the proof. Verifying twice with one of the checks being a disappearing string
# is how a working lane got recorded as a dead one.

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "application_parent.py"


def load_module():
    # application_parent imports its siblings by bare name, so the scripts dir has to be on
    # the path before it is executed.
    scripts_dir = str(MODULE_PATH.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location("application_parent", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


APPLIED = "https://coconala.com/mypage/job_matching/applied/offers"


def test_landing_on_the_applied_list_counts_even_without_the_toast() -> None:
    m = load_module()
    assert m.submit_landed(APPLIED, "応募・スカウト管理\n募集への応募（単発）") is True


def test_the_toast_is_still_accepted_when_it_happens_to_be_there() -> None:
    m = load_module()
    assert m.submit_landed(APPLIED, "応募しました") is True


def test_a_query_string_does_not_break_the_match() -> None:
    m = load_module()
    assert m.submit_landed(APPLIED + "?tab=single", "") is True


def test_still_being_on_the_offer_form_is_not_a_landing() -> None:
    # The click did nothing, or the confirmation modal is still up. Retrying is correct here.
    m = load_module()
    assert m.submit_landed("https://coconala.com/offers/add/91000093?&_t=1", "応募する") is False


def test_a_lookalike_host_is_not_a_landing() -> None:
    # A submit is an irreversible external effect; the page that claims it happened has to be
    # the real one.
    m = load_module()
    assert m.submit_landed("https://coconala.com.evil.test/mypage/job_matching/applied/offers", "") is False


def test_an_empty_url_is_not_a_landing() -> None:
    m = load_module()
    assert m.submit_landed("", "") is False
    assert m.submit_landed(None, None) is False


def test_www_is_the_same_site() -> None:
    m = load_module()
    assert m.submit_landed("https://www.coconala.com/mypage/job_matching/applied/offers", "") is True
