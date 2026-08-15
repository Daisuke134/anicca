"""A5-③: rank low-order-rate clients without blocking digital work.

Measured over the 37 closed 単発 jobs this loop applied to: 14 had someone hired
(median 発注率 61%), 23 had 契約人数 0 (median 発注率 7%). Filtering on 発注率 > 40
moves P(anyone is hired at all) from 0.14 [0.04, 0.33] to 0.69 [0.44, 0.87] --
Fisher exact OR=13.2, p=0.0016. No model, no bandit: 62% of the losses were not
lost to a rival, they were jobs where the client hired nobody.

Missing market observations still fail closed. A valid low rate is a commercial
signal, not evidence that the seller cannot fulfill the work.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

ASYNC_BRIEF = "資料作成をチャットで、非同期でお願いします。"
ASYNC_PROPOSAL = "構成案と資料一式を作成し、納品します。"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def market(rate: object) -> dict:
    snapshot = load("market_snapshot").empty_market("test_fixture")
    snapshot["client_order_rate"] = rate
    if rate is None:
        snapshot["missing"]["client_order_rate"] = "field_absent_from_page"
    else:
        snapshot["missing"].pop("client_order_rate", None)
    return snapshot


# --- the rule itself ------------------------------------------------------------


def test_a_client_below_the_threshold_is_ranked_but_allowed() -> None:
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        ASYNC_BRIEF,
        ASYNC_PROPOSAL,
        market=market(35),
    )

    assert verdict["allowed"] is True
    assert verdict["reason_codes"] == []
    assert verdict["ranking_codes"] == ["client_order_rate_below_threshold"]
    assert verdict["signals"]["client_order_rate"] == 35
    assert verdict["signals"]["min_client_order_rate"] == 40


def test_a_client_above_the_threshold_is_allowed() -> None:
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        ASYNC_BRIEF,
        ASYNC_PROPOSAL,
        market=market(61),
    )

    assert verdict["allowed"] is True
    assert verdict["reason_codes"] == []
    assert verdict["ranking_codes"] == []


def test_the_threshold_itself_is_ranked_not_refused() -> None:
    """The measured ranking rule is 発注率 > 40, without blocking submit."""
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        ASYNC_BRIEF,
        ASYNC_PROPOSAL,
        market=market(40),
    )

    assert verdict["allowed"] is True
    assert verdict["reason_codes"] == []
    assert verdict["ranking_codes"] == ["client_order_rate_below_threshold"]


def test_the_threshold_is_an_empirical_starting_point_not_a_law(monkeypatch) -> None:
    """40 came from n=37. It is configurable so the next 37 can move it."""
    monkeypatch.setenv("GIG_MIN_CLIENT_ORDER_RATE", "20")
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        ASYNC_BRIEF,
        ASYNC_PROPOSAL,
        market=market(35),
    )

    assert verdict["allowed"] is True
    assert verdict["ranking_codes"] == []
    assert verdict["signals"]["min_client_order_rate"] == 20


def test_a_nonsense_threshold_falls_back_to_the_measured_default(monkeypatch) -> None:
    monkeypatch.setenv("GIG_MIN_CLIENT_ORDER_RATE", "not-a-number")
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        ASYNC_BRIEF,
        ASYNC_PROPOSAL,
        market=market(35),
    )

    assert verdict["allowed"] is True
    assert verdict["ranking_codes"] == ["client_order_rate_below_threshold"]
    assert verdict["signals"]["min_client_order_rate"] == 40


# --- the missing case: fail-closed, and why -------------------------------------


def test_a_missing_client_order_rate_fails_closed() -> None:
    """Absence is a failed read, not a new client.

    Coconala prints a client with no history as `0%`, not as nothing (observed on
    tyogvii, Mooty, kiki_1115, pdnob_jp). So a page with no 発注率 at all is one we
    could not read -- and every such card observed in this loop's logs (34/310) is
    the two-name 継続 client card, a bucket A3 already refuses. Fail-closed therefore
    costs approximately zero real 単発 opportunities, and it makes a parser
    regression loud and countable instead of silently restoring the pre-A5 loop.
    """
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        ASYNC_BRIEF,
        ASYNC_PROPOSAL,
        market=market(None),
    )

    assert verdict["allowed"] is False
    assert "client_order_rate_missing" in verdict["reason_codes"]


def test_no_market_snapshot_at_all_fails_closed() -> None:
    """A caller that reaches the gate with nothing observed does not get a yes."""
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        ASYNC_BRIEF,
        ASYNC_PROPOSAL,
        market=None,
    )

    assert verdict["allowed"] is False
    assert "market_snapshot_missing" in verdict["reason_codes"]


def test_the_market_argument_cannot_be_forgotten() -> None:
    """Omitting the observation is a crash, not a silent allow.

    A default would mean the gate could be bypassed by writing less code, which is
    exactly how `bid_jpy` ended up on 0 of 311 ledger rows.
    """
    eligibility = load("application_eligibility")

    try:
        eligibility.evaluate_application(ASYNC_BRIEF, ASYNC_PROPOSAL)
    except TypeError as error:
        assert "market" in str(error)
    else:
        raise AssertionError("evaluate_application accepted a missing market")


# --- the gate proven where it matters: at the irreversible submit ----------------


def _run_submit(rate: object, evidence_dir: Path):
    """Drive the real submit path with a page whose 発注率 is `rate`."""
    import test_cdp_nav_snapshot_observe as harness  # noqa: PLC0415

    brief = (
        "予算\n1万円\n〜\n3万円\n"
        "募集期限\n締切日 2026年8月7日 / 掲載日 2026年7月28日\n"
        "応募状況\n応募人数 26\n契約人数 0\n閲覧数 348\n"
        "募集内容\n資料作成をチャットでお願いします。\n"
        "募集者情報\nsomebody\n発注実績\n10\n発注件数\n"
        + ("" if rate is None else f"{rate}%\n発注率\n100%\n取引完了率\n")
        + "認証状況\n"
    )
    request_id = "91000026"
    form_url = f"https://coconala.com/offers/add/{request_id}"
    page = harness.FakeSocket(form_url, application_submission=True)
    from unittest import mock  # noqa: PLC0415
    import asyncio  # noqa: PLC0415

    with mock.patch.object(
        harness.module.websockets,
        "connect",
        return_value=harness.FakeConnection(page),
    ):
        error: Exception | None = None
        try:
            asyncio.run(harness.module.submit_application(
                "ws://127.0.0.1:9223/devtools/page/leased-target",
                request_id,
                evidence_dir / "submitted.png",
                evidence_dir / "submitted.json",
                wait_seconds=0,
                opportunity_brief=brief,
            ))
        except Exception as caught:  # noqa: BLE001 -- the refusal is the subject
            error = caught
    clicks = [
        row for row in page.requests
        if row["method"] == "Input.dispatchMouseEvent"
        and row["params"]["type"] == "mouseReleased"
    ]
    return error, clicks


def test_submit_boundary_allows_and_ranks_a_thirty_five_percent_client() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        error, clicks = _run_submit(35, root)

        assert error is None, error
        assert len(clicks) == 3
        verdict = json.loads((root / "submitted.eligibility.json").read_text())
        assert verdict["allowed"] is True
        assert verdict["reason_codes"] == []
        assert verdict["ranking_codes"] == ["client_order_rate_below_threshold"]
        assert verdict["market"]["client_order_rate"] == 35
        assert verdict["market"]["applicants_at_bid"] == 26


def test_submit_boundary_allows_a_sixty_one_percent_client() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        error, clicks = _run_submit(61, root)

        assert error is None, error
        assert len(clicks) == 3
        verdict = json.loads((root / "submitted.eligibility.json").read_text())
        assert verdict["allowed"] is True
        assert verdict["market"]["client_order_rate"] == 61


def test_submit_boundary_refuses_when_the_page_states_no_order_rate() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        error, clicks = _run_submit(None, root)

        assert isinstance(error, RuntimeError)
        assert "client_order_rate_missing" in str(error)
        assert clicks == []
        verdict = json.loads((root / "submitted.eligibility.json").read_text())
        assert verdict["market"]["client_order_rate"] is None
        assert (
            verdict["market"]["missing"]["client_order_rate"]
            == "field_absent_from_page"
        )


def test_production_incident_new_client_is_ranked_but_not_submit_blocked() -> None:
    """91000084 was digital work and was refused solely because a new client is 0%."""
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        error, clicks = _run_submit(0, root)

        assert error is None, error
        assert len(clicks) == 3
        verdict = json.loads((root / "submitted.eligibility.json").read_text())
        assert verdict["allowed"] is True
        assert verdict["reason_codes"] == []
        assert verdict["ranking_codes"] == ["client_order_rate_below_threshold"]
