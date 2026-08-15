"""A5-① the parser: the market IS printed on the page, so read it off the page.

Every string these tests parse is verbatim rendered `innerText` from coconala 募集
detail pages this loop actually opened (see fixtures/coconala_request_detail.py for
provenance). The parser is exercised against the real shapes, including the two that
break a naive reading: the value-above-label client stat card, and 見積り希望.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {name}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


market_snapshot = _load(ROOT / "scripts" / "market_snapshot.py", "market_snapshot")
pages = _load(
    Path(__file__).resolve().parent / "fixtures" / "coconala_request_detail.py",
    "coconala_request_detail",
)


# 2026-07-29 12:00 JST, so `minutes_since_posted` is checkable arithmetic rather
# than a moving number.
NOW = datetime(2026, 7, 29, 3, 0, tzinfo=timezone.utc).timestamp()


def test_range_budget_and_a_brand_new_client_are_read_whole() -> None:
    market = market_snapshot.parse_market(
        pages.RANGE_BUDGET_NEW_CLIENT,
        now=NOW,
    )

    assert market["budget_lo_jpy"] == 10_000
    assert market["budget_hi_jpy"] == 30_000
    assert market["budget_is_quote_request"] is False
    assert market["applicants_at_bid"] == 26
    assert market["contracted_count"] == 0
    assert market["views"] == 348
    # A client who has never ordered is printed as 0, not omitted.
    assert market["client_order_rate"] == 0
    assert market["client_order_count"] == 0
    # Only our own bid is unstated here: this is the page as read, before the form
    # was filled. Everything the page prints was read, and the one thing it cannot
    # print says so.
    assert market["missing"] == {"bid_jpy": "field_absent_from_page"}


def test_the_client_stat_card_is_read_value_above_label() -> None:
    """37% is 発注率; 50% is 取引完了率. Reading label-then-value swaps them.

    This is the single most consequential line in the parser: the swapped reading
    turns a 37% client (refused) into a 50% client (allowed), and no match count
    would ever reveal it.
    """
    market = market_snapshot.parse_market(
        pages.RANGE_BUDGET_ESTABLISHED_CLIENT,
        now=NOW,
    )

    assert market["client_order_rate"] == 37
    assert market["client_order_count"] == 10
    assert market["applicants_at_bid"] == 44
    assert market["contracted_count"] == 1
    assert market["budget_lo_jpy"] == 80_000
    assert market["budget_hi_jpy"] == 100_000


def test_quote_request_records_an_explicit_null_with_its_reason() -> None:
    """見積り希望 has no number. The absence is stated, never omitted."""
    market = market_snapshot.parse_market(
        pages.QUOTE_REQUEST_HIGH_RATE_CLIENT,
        now=NOW,
    )

    assert market["budget_is_quote_request"] is True
    assert market["budget_lo_jpy"] is None
    assert market["budget_hi_jpy"] is None
    assert market["missing"]["budget_lo_jpy"] == "budget_is_quote_request"
    assert market["missing"]["budget_hi_jpy"] == "budget_is_quote_request"
    assert market["budget_text"] == "見積り希望"
    assert market["client_order_rate"] == 69
    assert market["client_order_count"] == 162


def test_an_open_lower_bound_budget_keeps_the_bound_it_has() -> None:
    """5千円未満 states a ceiling and no floor. Only the floor is null."""
    market = market_snapshot.parse_market(
        pages.UNDER_BUDGET_OPEN_LISTING,
        now=NOW,
    )

    assert market["budget_hi_jpy"] == 5_000
    assert market["budget_lo_jpy"] is None
    assert market["missing"]["budget_lo_jpy"] == "budget_open_lower_bound"
    assert market["budget_is_quote_request"] is False


def test_a_single_exact_budget_is_both_bounds() -> None:
    market = market_snapshot.parse_market(
        pages.EXACT_BUDGET_LISTING,
        now=NOW,
    )

    assert market["budget_lo_jpy"] == 3_000
    assert market["budget_hi_jpy"] == 3_000
    assert market["missing"] == {"bid_jpy": "field_absent_from_page"}


def test_other_jobs_advertised_on_the_same_page_are_never_read() -> None:
    """Every detail page ends with 「この募集内容に似ている仕事」 cards carrying their
    OWN 予算 and 応募者数. Reading past that line silently attributes another job's
    market to this application."""
    market = market_snapshot.parse_market(
        pages.UNDER_BUDGET_OPEN_LISTING,
        now=NOW,
    )

    # The trailing card advertises 40万円〜50万円 and 応募者数 1.
    assert market["budget_hi_jpy"] == 5_000
    assert market["applicants_at_bid"] == 3


def test_posted_date_is_reported_at_the_precision_the_page_prints() -> None:
    """掲載日 is a DATE. The parser may not pretend to minute precision it never saw."""
    market = market_snapshot.parse_market(
        pages.RANGE_BUDGET_NEW_CLIENT,
        now=NOW,
    )

    assert market["posted_date"] == "2026-07-28"
    assert market["posted_at_precision"] == "date"
    # 2026-07-28 00:00 JST -> 2026-07-29 12:00 JST is 36 hours.
    assert market["minutes_since_posted"] == 36 * 60


def test_a_missing_client_stat_card_is_an_explicit_null_with_a_reason() -> None:
    """The 継続 client card prints two names and no stats at all.

    34 of 310 complete client cards in this loop's own logs look like this, and every
    one of them is on the retainer side. The parser says so instead of guessing a rate.
    """
    market = market_snapshot.parse_market(
        pages.RETAINER_CLIENT_CARD_NO_STATS,
        now=NOW,
    )

    assert market["client_order_rate"] is None
    assert market["client_order_count"] is None
    assert market["missing"]["client_order_rate"] == "field_absent_from_page"
    assert market["missing"]["client_order_count"] == "field_absent_from_page"


def test_every_field_is_present_as_a_key_even_when_the_page_is_empty() -> None:
    """Absence is recorded, never omitted: the keys exist or the row is unreadable."""
    market = market_snapshot.parse_market("", now=NOW)

    for field in market_snapshot.MARKET_FIELDS:
        assert field in market, field
        assert market[field] is None or field == "budget_is_quote_request"
    assert market["missing"]["client_order_rate"] == "page_text_empty"
    assert set(market["missing"]) == set(market_snapshot.MARKET_FIELDS)


def test_an_unparseable_number_is_a_null_with_value_unparseable() -> None:
    """A rendered-but-nonsense value is a different failure from an absent one."""
    text = (
        "予算\n応相談\n募集期限\n締切日 2026年8月9日 / 掲載日 2026年7月29日\n"
        "応募状況\n応募人数 たくさん\n契約人数 0\n閲覧数 155\n"
        "募集者情報\nnobody\n発注実績\n2\n発注件数\n50%\n発注率\n100%\n取引完了率\n認証状況\n"
    )

    market = market_snapshot.parse_market(text, now=NOW)

    assert market["budget_hi_jpy"] is None
    assert market["missing"]["budget_hi_jpy"] == "value_unparseable"
    assert market["applicants_at_bid"] is None
    assert market["missing"]["applicants_at_bid"] == "value_unparseable"
    assert market["contracted_count"] == 0
    assert market["client_order_rate"] == 50
