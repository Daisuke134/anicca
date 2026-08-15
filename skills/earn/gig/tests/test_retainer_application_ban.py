"""A3 (2026-07-30): the loop may never open a NEW retainer (継続) application.

Measured cause: every 継続 listing on Coconala escalates to a synchronous 三者面談
before money moves. The live example that forced this rule was
【長期・在宅】SNS投稿・更新サポートスタッフ募集 (希望報酬 ¥1,500/時), which sat in the
queue showing 「三者面談の候補日時が届きました」. A retainer application therefore buys
a human-in-the-loop on every deal, which is the one thing this system exists to
remove.

The refusal lives in code at the submit boundary, not in a prompt and not in a
quota of zero, because a prompt is negotiable and a quota is arithmetic the model
reports on itself. `application_eligibility.evaluate_application` already
fail-closes on synchronous-presence work, so the retainer ban is that same gate
with one more deterministic reason code: exactly one place can say no.

The scope boundary pinned here too: applications ALREADY submitted and threads
ALREADY open must keep being handled. Stopping NEW retainer applications must
never become abandoning an existing retainer buyer.

The submit-boundary proof itself lives beside the CDP fake it needs, in
test_cdp_nav_snapshot_observe.py.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

# A5-③ (2026-07-31): the same gate now also refuses clients who hire nobody, and
# `market` is required rather than defaulted. A retainer must be refused for BEING a
# retainer, so every call here passes a market that would otherwise be allowed --
# that is what keeps these tests a proof about the bucket.
HEALTHY_MARKET = {"client_order_rate": 61}
RETAINER_ULID = "01KYKDECET9WAY0CKRBCKH81RC"

# The live listing that produced this rule reads as clean asynchronous chat work.
# Used here so the test proves the refusal is bucket-driven and not an accident of
# the synchronous-presence text patterns happening to fire.
CLEAN_RETAINER_BRIEF = """
【長期・在宅】SNS投稿・更新サポートスタッフ募集
連絡はココナラのチャット形式で、隙間時間に非同期で対応いただけます。
InstagramとXの定期投稿、投稿カレンダーの更新、月次レポートをお願いします。
希望報酬は時給1,500円です。
"""
CLEAN_RETAINER_PROPOSAL = """
接続済みアカウントを用いて定期投稿と投稿カレンダーを運用し、
月次レポートを納品します。連絡はトークルームで非同期に行います。
"""


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# --- the gate itself ------------------------------------------------------------


def test_retainer_bucket_is_refused_however_clean_the_listing_reads() -> None:
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        CLEAN_RETAINER_BRIEF,
        CLEAN_RETAINER_PROPOSAL,
        bucket="retainer",
        market=HEALTHY_MARKET,
    )

    assert verdict["allowed"] is False
    assert verdict["reason_codes"] == ["retainer_applications_disabled"]
    assert verdict["signals"]["bucket"] == "retainer"


def test_the_same_listing_text_is_still_allowed_in_the_single_bucket() -> None:
    """The ban is on the contract shape, not on the words: 単発 is untouched."""
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        CLEAN_RETAINER_BRIEF,
        CLEAN_RETAINER_PROPOSAL,
        bucket="single",
        market=HEALTHY_MARKET,
    )

    assert verdict["allowed"] is True
    assert verdict["reason_codes"] == []


def test_single_remains_the_default_bucket_for_callers_that_do_not_say() -> None:
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        CLEAN_RETAINER_BRIEF,
        CLEAN_RETAINER_PROPOSAL,
        market=HEALTHY_MARKET,
    )

    assert verdict["allowed"] is True


def test_an_unknown_bucket_fails_closed_rather_than_defaulting_to_allowed() -> None:
    eligibility = load("application_eligibility")

    verdict = eligibility.evaluate_application(
        CLEAN_RETAINER_BRIEF,
        CLEAN_RETAINER_PROPOSAL,
        bucket="whatever-the-model-called-it",
        market=HEALTHY_MARKET,
    )

    assert verdict["allowed"] is False
    assert "application_bucket_unrecognized" in verdict["reason_codes"]


# --- A4 must not regress: work already in flight keeps being worked --------------


def test_an_already_submitted_retainer_application_still_becomes_a_ledger_row():
    """Stopping NEW applications must not erase the ones already submitted."""
    report = load("application_report")

    rows, _stats = report.plan(
        report=[{
            "request_id": RETAINER_ULID,
            "bucket": "retainer",
            "category": "SNS運用代行",
            "title": "【長期・在宅】SNS投稿・更新サポートスタッフ募集",
            "price_jpy": None,
            "deliver_date": None,
            "url": (
                "https://coconala.com/job_matching/outsources/"
                f"{RETAINER_ULID}"
            ),
            "compensation_type": "hourly",
            "weekly_days": 3,
            "weekly_hours_min": 1,
            "weekly_hours_max": 10,
        }],
        existing_rows=[],
        proven={RETAINER_ULID},
        dom_categories={},
        now=1_785_120_000.0,
        pass_id="1785119405-48257",
    )

    assert len(rows) == 1, rows
    assert rows[0]["requestId"] == RETAINER_ULID
    assert rows[0]["bucket"] == "retainer"


def test_an_open_retainer_thread_still_reaches_the_reply_queue():
    """The reply lane is talkroom-keyed and must stay blind to the bucket."""
    reply_queue = load("reply_queue")

    result = reply_queue.build_queue(
        {
            "captured_at": "2026-07-30T00:04:00+00:00",
            "orders": [],
            "inquiries": [{
                "talkroom_id": "4207",
                "talkroom_url": (
                    "https://coconala.com/mypage/direct_message/4207"
                ),
                "last_message_side": "buyer",
                "reply_required": True,
                "buyer_sent_at": "2026-07-30T00:00:00+00:00",
                "message_id": "msg-retainer-1",
            }],
        },
        now=datetime(2026, 7, 30, 0, 4, tzinfo=timezone.utc),
    )

    assert result["status"] == "ready"
    assert result["errors"] == []
    assert [item["talkroom_id"] for item in result["items"]] == ["4207"]
    assert result["items"][0]["priority"] == "P1"
    assert result["items"][0]["next_action"] == "reply"
