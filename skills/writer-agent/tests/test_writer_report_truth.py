import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from writer_report import _interpretation, render_message  # noqa: E402
from writer_report_worker import (  # noqa: E402
    REPORT_TEXT_SCHEMA_VERSION,
    _semantic_hash,
)


def _snapshot(*, receipts: int, public_count: int | None) -> dict:
    timeline = None
    if public_count is not None:
        timeline = {"publication_truth": {"public_count": public_count}}
    return {
        "money": {"today": {"verified_revenue_event_count": receipts}},
        "incident_timeline": timeline,
    }


def _hash_snapshot() -> dict:
    period = {
        "verified_revenue_event_count": 0,
        "verified_gross_by_currency": {},
        "verified_net_by_currency": {},
        "verified_gross_by_stream": {},
        "verified_refunds_by_currency": {},
        "verified_fees_by_currency": {},
        "paid_out_by_currency": {},
    }
    return {
        "money": {
            "today": period,
            "month": period,
            "week": period,
            "previous_week": period,
            "mrr": {},
            "available_balance": {},
            "pending_payout": {},
            "payout_receipts": [],
        },
        "articles": [],
        "report_articles_scope": "none",
        "opportunities": {"active": []},
        "commercial": {},
        "incident_timeline": None,
        "learning": {},
    }


def _render_snapshot(*, week_receipts: int = 0, report_scope: str = "latest_saved_run") -> dict:
    empty_period = {
        "verified_revenue_event_count": 0,
        "verified_gross_by_currency": {},
        "verified_net_by_currency": {},
        "verified_gross_by_stream": {},
        "verified_refunds_by_currency": {},
        "verified_fees_by_currency": {},
        "paid_out_by_currency": {},
    }
    week = {**empty_period, "verified_revenue_event_count": week_receipts}
    if week_receipts:
        week["verified_gross_by_currency"] = {"USD": 10.0}
        week["verified_net_by_currency"] = {"USD": 10.0}
    return {
        "generated_at": "2026-08-21T12:00:00+09:00",
        "money": {
            "today": empty_period,
            "month": empty_period,
            "week": week,
            "previous_week": empty_period,
            "mrr": {},
            "available_balance": {"status": "unknown"},
            "payout_receipts": [],
        },
        "articles": [],
        "report_articles": [{
            "platform": "substack", "title": "過去記事", "live_url": "https://example.com/old",
            "metrics": {}, "money": {"gross": {}}, "revenue_capable": False,
        }],
        "report_articles_scope": report_scope,
        "opportunities": {"active": []},
        "commercial": {"active": []},
        "incident_timeline": None,
        "learning": {"day_diff": {}, "latest_experiment": None},
    }


def test_report_separates_historical_publication_from_current_tick():
    snapshot = _snapshot(receipts=0, public_count=5)
    text = _interpretation(snapshot, snapshot["money"]["today"])
    assert "保存済みの最新観測runには公開URLが5件あります" in text
    assert "今回のtickで新規公開したreceiptとは別" in text
    assert "公開は動いています" not in text


def test_report_says_when_publication_receipt_is_missing():
    snapshot = _snapshot(receipts=0, public_count=0)
    text = _interpretation(snapshot, snapshot["money"]["today"])
    assert "公開URLを確認していません" in text


def test_verified_revenue_keeps_receipt_wording():
    snapshot = _snapshot(receipts=1, public_count=0)
    text = _interpretation(snapshot, snapshot["money"]["today"])
    assert "外部receiptで確認できた受取だけを収益として集計しました" in text


def test_weekly_render_uses_weekly_receipt_for_interpretation():
    text = render_message(_render_snapshot(week_receipts=1), cadence="weekly")
    interpretation = text.split("解釈: ", 1)[1]
    assert "当社が受取済み: $10.00" in text
    assert "外部receiptで確認できた受取だけを収益として集計しました" in interpretation
    assert "外部receipt付きの受取はまだ0" not in interpretation


def test_render_labels_historical_article_fallback():
    text = render_message(_render_snapshot(), cadence="immediate")
    assert "保存済みの過去runのreceiptです" in text
    assert "今回tickの新規公開ではありません" in text


def test_report_text_version_is_part_of_dedupe_hash(monkeypatch):
    snapshot = _hash_snapshot()
    before = _semantic_hash(snapshot)
    monkeypatch.setattr(
        "writer_report_worker.REPORT_TEXT_SCHEMA_VERSION",
        REPORT_TEXT_SCHEMA_VERSION + 1,
    )
    assert _semantic_hash(snapshot) != before
