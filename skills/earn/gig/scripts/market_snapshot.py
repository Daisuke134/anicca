#!/usr/bin/env python3
"""Read the market off the 募集 page, in code, at the moment of the bid.

A5-① (2026-07-31). Measured: `bid_jpy` was on 0 of 311 rows of ~/gig/applied.jsonl,
`price_jpy` on 95 (30%), and all 90 loss rows carried no price at all. The eight
joinable (price, outcome) pairs were therefore all losses, which is not a weak
dataset -- it is a likelihood that is monotone in the parameter, so no pricing model
can be fitted at all. The bottleneck was never the model. It was that nothing wrote
down what we bid or what the client had budgeted.

The B2 step prompt has asked the model for `price_jpy` since X8b. Compliance is 30%.
Asking again in stronger words is the same intervention that already failed, so this
module exists so the code can read the numbers itself.

Nothing here is scraped from a new place: every field is already printed on the
募集 detail page whose `innerText` `cdp_nav_snapshot._load_opportunity_brief` loads
before every submit. This module is pure text -> numbers, so it is testable against
real captured pages and costs no extra page load.

Two shapes decide the correctness of the whole file:

1. THE CLIENT STAT CARD IS VALUE-ABOVE-LABEL.

       発注実績      <- a heading, not a labelled field
       36            <- 発注件数
       発注件数
       57%           <- 発注率
       発注率
       100%          <- 取引完了率
       取引完了率
       認証状況

   Reading it label-then-value is silently wrong: it returns 取引完了率 where 発注率
   was asked for, and 取引完了率 is systematically the larger number, so the error
   always fails OPEN on the gate that A5-③ builds on top. Across this loop's own
   logs both readings match 163 times, so nothing but the structure distinguishes
   them -- the tail does: label-then-value would have to give 取引完了率 the value
   「認証状況」.

2. ABSENCE HAS KINDS, AND THEY ARE NOT INTERCHANGEABLE. 見積り希望 is a budget the
   client deliberately did not state; 5千円未満 is a ceiling with no floor; a page
   with no client stat card at all is a page we could not read. Each is recorded as
   an explicit null WITH a reason code, never as a missing key, because a missing key
   is indistinguishable from a value of nothing and that is precisely how 90 loss
   rows came to carry no price.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from typing import Any


VERSION = 1

# The fields every application must state. A null here is a null WITH a reason; a
# key that is simply absent is a bug this module exists to make impossible.
MARKET_FIELDS: tuple[str, ...] = (
    "bid_jpy",
    "budget_lo_jpy",
    "budget_hi_jpy",
    "budget_is_quote_request",
    "applicants_at_bid",
    "contracted_count",
    "client_order_rate",
    "client_order_count",
    "views",
    "minutes_since_posted",
)

# Reason codes. Deliberately few and deliberately distinct: A6 has to be able to tell
# "the client did not say" from "we could not read the page".
PAGE_TEXT_EMPTY = "page_text_empty"
FIELD_ABSENT = "field_absent_from_page"
VALUE_UNPARSEABLE = "value_unparseable"
BUDGET_IS_QUOTE_REQUEST = "budget_is_quote_request"
BUDGET_OPEN_LOWER_BOUND = "budget_open_lower_bound"
BUDGET_OPEN_UPPER_BOUND = "budget_open_upper_bound"

JST = timezone(timedelta(hours=9))

# Every detail page ends with 「この募集内容に似ている仕事」 cards that carry their OWN
# 予算 and 応募者数. Reading past this line attributes another job's market to this
# application, which is worse than reading nothing.
_SIMILAR_JOBS_MARKERS = ("この募集内容に似ている仕事", "この募集内容に似ているお仕事")

_BUDGET_BLOCK = re.compile(r"(?:^|\n)予算\n(.*?)(?=\n(?:%s)\n|\Z)" % "|".join(
    ("納品希望日", "募集期限", "応募状況", "応募者数", "募集内容", "業種", "用途・種類")
), re.DOTALL)

# Value-above-label. See the module docstring: this direction is the whole point.
_ORDER_RATE = re.compile(r"([0-9]+)\s*%\s*\n\s*発注率")
_ORDER_COUNT = re.compile(r"([0-9,]+)\s*\n\s*発注件数")

_POSTED = re.compile(r"掲載日\s*([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日")

_RANGE_SEPARATOR = re.compile(r"[~〜～]")

_AMOUNT = re.compile(
    r"\A(?:([0-9,]+)万)?(?:([0-9,]+)千)?(?:([0-9,]+))?円\Z"
)


def _normalize(text: str | None) -> str:
    """NFKC so full-width digits, ％ and 〜 all reduce to one spelling."""
    return unicodedata.normalize("NFKC", text or "")


def _main_region(text: str) -> str:
    for marker in _SIMILAR_JOBS_MARKERS:
        index = text.find(marker)
        if index != -1:
            return text[:index]
    return text


def _int(token: str) -> int | None:
    token = token.replace(",", "").strip()
    return int(token) if token.isdigit() else None


def _jpy(token: str) -> int | None:
    """1万円 / 5千円 / 3,000円 / 1万5千円 -> yen. Anything else -> None."""
    match = _AMOUNT.match(token.replace(" ", ""))
    if match is None or not any(match.groups()):
        return None
    man, sen, plain = match.groups()
    total = 0
    for group, unit in ((man, 10_000), (sen, 1_000), (plain, 1)):
        if group is None:
            continue
        value = _int(group)
        if value is None:
            return None
        total += value * unit
    return total


def empty_market(reason: str) -> dict[str, Any]:
    """A fully-shaped snapshot that observed nothing, and says so for every field."""
    snapshot: dict[str, Any] = {
        "version": VERSION,
        "budget_text": None,
        "posted_date": None,
        "posted_at_precision": None,
        "missing": {field: reason for field in MARKET_FIELDS},
    }
    for field in MARKET_FIELDS:
        snapshot[field] = None
    # A boolean field whose value is unknown still has to be a boolean downstream;
    # its `missing` entry is what says the False was never observed.
    snapshot["budget_is_quote_request"] = False
    return snapshot


def _record(
    snapshot: dict[str, Any],
    field: str,
    value: Any,
    reason: str,
) -> None:
    if value is None:
        snapshot[field] = None
        snapshot["missing"][field] = reason
        return
    snapshot[field] = value
    snapshot["missing"].pop(field, None)


def _parse_budget(region: str, snapshot: dict[str, Any]) -> None:
    block = _BUDGET_BLOCK.search(region)
    if block is None:
        return
    budget_text = "".join(
        line.strip() for line in block.group(1).splitlines() if line.strip()
    )
    snapshot["budget_text"] = budget_text or None
    if not budget_text:
        return

    if "見積り希望" in budget_text or "見積もり希望" in budget_text:
        snapshot["budget_is_quote_request"] = True
        snapshot["missing"].pop("budget_is_quote_request", None)
        _record(snapshot, "budget_lo_jpy", None, BUDGET_IS_QUOTE_REQUEST)
        _record(snapshot, "budget_hi_jpy", None, BUDGET_IS_QUOTE_REQUEST)
        return

    snapshot["budget_is_quote_request"] = False
    snapshot["missing"].pop("budget_is_quote_request", None)

    if budget_text.endswith("未満"):
        ceiling = _jpy(budget_text[: -len("未満")])
        _record(
            snapshot,
            "budget_lo_jpy",
            None,
            BUDGET_OPEN_LOWER_BOUND if ceiling is not None else VALUE_UNPARSEABLE,
        )
        _record(snapshot, "budget_hi_jpy", ceiling, VALUE_UNPARSEABLE)
        return

    if budget_text.endswith("以上"):
        floor = _jpy(budget_text[: -len("以上")])
        _record(snapshot, "budget_lo_jpy", floor, VALUE_UNPARSEABLE)
        _record(
            snapshot,
            "budget_hi_jpy",
            None,
            BUDGET_OPEN_UPPER_BOUND if floor is not None else VALUE_UNPARSEABLE,
        )
        return

    # Coconala renders the range separator as U+301C WAVE DASH, which NFKC leaves
    # alone, and elsewhere as U+FF5E FULLWIDTH TILDE, which NFKC folds to ASCII "~".
    # Both spellings reach this line, so both are accepted.
    bounds = _RANGE_SEPARATOR.split(budget_text, maxsplit=1)
    if len(bounds) == 2:
        low_text, high_text = bounds
        _record(snapshot, "budget_lo_jpy", _jpy(low_text), VALUE_UNPARSEABLE)
        _record(snapshot, "budget_hi_jpy", _jpy(high_text), VALUE_UNPARSEABLE)
        return

    exact = _jpy(budget_text)
    _record(snapshot, "budget_lo_jpy", exact, VALUE_UNPARSEABLE)
    _record(snapshot, "budget_hi_jpy", exact, VALUE_UNPARSEABLE)


def _parse_labelled_count(
    region: str,
    snapshot: dict[str, Any],
    *,
    label: str,
    field: str,
) -> None:
    """応募人数 26 / 契約人数 0 / 閲覧数 348 -- label and value share one line."""
    match = re.search(rf"{label}\s*([^\s\n]+)", region)
    if match is None:
        _record(snapshot, field, None, FIELD_ABSENT)
        return
    _record(snapshot, field, _int(match.group(1)), VALUE_UNPARSEABLE)


def _parse_client_stats(region: str, snapshot: dict[str, Any]) -> None:
    for label, pattern, field in (
        ("発注率", _ORDER_RATE, "client_order_rate"),
        ("発注件数", _ORDER_COUNT, "client_order_count"),
    ):
        if label not in region:
            # The two-name (会社名 + 担当者名) client card prints no stat block at
            # all. 34 of 310 complete cards in this loop's logs look like that and
            # every one of them is on the 継続 side, which A3 already refuses.
            _record(snapshot, field, None, FIELD_ABSENT)
            continue
        match = pattern.search(region)
        _record(
            snapshot,
            field,
            _int(match.group(1)) if match else None,
            VALUE_UNPARSEABLE,
        )


def _parse_posted(region: str, snapshot: dict[str, Any], now: float) -> None:
    match = _POSTED.search(region)
    if match is None:
        _record(snapshot, "minutes_since_posted", None, FIELD_ABSENT)
        return
    year, month, day = (int(part) for part in match.groups())
    try:
        posted = datetime(year, month, day, tzinfo=JST)
    except ValueError:
        _record(snapshot, "minutes_since_posted", None, VALUE_UNPARSEABLE)
        return
    snapshot["posted_date"] = posted.date().isoformat()
    # 掲載日 is a DATE. Reporting minutes is useful for age bucketing, but the
    # precision it was read at is stated so no later reader mistakes it for a
    # timestamp. The applicant list is the only minute-precise clock on the page and
    # it measures other people's behaviour, not the posting.
    snapshot["posted_at_precision"] = "date"
    elapsed = int((now - posted.timestamp()) // 60)
    _record(snapshot, "minutes_since_posted", max(elapsed, 0), VALUE_UNPARSEABLE)


def parse_market(
    page_text: str,
    *,
    now: float,
    bid_jpy: object = None,
) -> dict[str, Any]:
    """Return the market this application is bidding into, with stated absences.

    `bid_jpy` is what WE typed into the application form; everything else is what the
    page states. They are recorded together because a price without the budget it was
    aimed at teaches nothing.
    """
    text = _normalize(page_text)
    if not text.strip():
        return empty_market(PAGE_TEXT_EMPTY)

    snapshot = empty_market(FIELD_ABSENT)
    region = _main_region(text)

    _record(snapshot, "bid_jpy", _coerce_bid(bid_jpy), FIELD_ABSENT)
    _parse_budget(region, snapshot)
    _parse_labelled_count(
        region, snapshot, label="応募人数", field="applicants_at_bid"
    )
    _parse_labelled_count(
        region, snapshot, label="契約人数", field="contracted_count"
    )
    _parse_labelled_count(region, snapshot, label="閲覧数", field="views")
    _parse_client_stats(region, snapshot)
    _parse_posted(region, snapshot, now)
    return snapshot


def _coerce_bid(value: object) -> int | None:
    """The form's price input arrives as a string, or as nothing at all."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        digits = _normalize(value).replace(",", "").replace("円", "").strip()
        return int(digits) if digits.isdigit() else None
    return None
