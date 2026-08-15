#!/usr/bin/env python3
"""The five stages -- 応募 → 契約 → 納品 → 入金 → レビュー -- joined on keys that survive.

WHY THIS EXISTS
---------------
On 2026-08-07 the question "how do we get from here to $10k/month" could not be
answered, and the reason was not missing data. It was missing *joins*. Both ends were
recorded and nothing linked them:

    ~/gig/applied.jsonl    keys applications by 募集 id  (7 digits, e.g. 91000027)
    ~/gig/earnings.jsonl   keys payments     by talkroom id (8 digits, e.g. 90000006)
                           -- and stores that talkroom id in a field NAMED "requestId",
                           because the revenue page never shows a 募集 id at all.

So the obvious join, applied.requestId == earnings.requestId, matches exactly ONE of the
six paid orders, and that one only by coincidence (90000000 is a direct offer whose
project is keyed by its own talkroom id). Anyone who computes a conversion rate off that
join gets 1/6 of the truth and does not know it.

★ This module does not create a second ledger. ★ The bridge already exists:
``~/gig/identity_chain.jsonl``, built by ``application_ledger.py --harvest`` from offer
pages and queue snapshots that show both ids on the same DOM. This module imports that
chain and joins through it. The only thing added here is the *funnel*: the stage lattice,
the two entry paths, the revenue classification, and the refusal to divide across
mismatched windows.

THE TWO ENTRY PATHS -- do not merge them
----------------------------------------
Revenue arrives through two doors, and averaging them corrupts the conversion rate:

  application  a 募集 we applied to. Enters at stage 1. Has a 募集 id, an application
               row, and (once won) a chain link to its talkroom.
  direct_offer a buyer who came to us. ★Never had an application.★ Enters at stage 2.
               Its offer page has no "No.<digits>" 募集 reference, so
               ``links_from_offer_evidence`` deliberately returns no link and the
               project falls back to keying on the talkroom id
               (``delivery_identity.stable_identity``). That is not a broken join --
               it is a different door, and it must not sit in the denominator of
               "revenue per application".

Signalled by ``source_contract_id`` in ``~/gig/projects/<id>/state.json``:
``offer:<n>`` = 募集-backed, ``direct-offer:<n>`` = buyer-initiated.

WINDOWS
-------
Every count carries the window it was counted over. ``revenue_per_application`` REFUSES
to divide when the numerator and denominator windows differ, because that is exactly the
error that produced a wrong number on 2026-08-07: applications span 2026-07-01..08-08
(39 days) while settled revenue spans 2026-07-25..08-05 (12 days), and dividing one by
the other understates cost-per-win by roughly 3x. A wrong number is worse than none.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# Stage names, in order. Kept in Japanese because that is how Dais asked for them and how
# the marketplace itself labels the states.
STAGE_APPLIED = "応募"
STAGE_CONTRACTED = "契約"
STAGE_DELIVERED = "納品"
STAGE_PAID = "入金"
STAGE_REVIEWED = "レビュー"
STAGES = (STAGE_APPLIED, STAGE_CONTRACTED, STAGE_DELIVERED, STAGE_PAID, STAGE_REVIEWED)

ENTRY_APPLICATION = "application"
ENTRY_DIRECT_OFFER = "direct_offer"

# earnings.jsonl statuses that mean the money is actually settled. Same set the existing
# gig_funnel.py uses, kept identical on purpose so the two never disagree about "paid".
SETTLED = {"検収", "支払", "検収完了", "completed", "paid"}

# work_state / talkroom_state values that mean the buyer can see a delivered artifact.
DELIVERED_STATES = {"DELIVERED", "納品確認待ち", "検収完了", "評価依頼"}


def _load_application_ledger():
    """Import application_ledger.py as a sibling, however this file was invoked."""
    here = Path(__file__).resolve().parent
    if str(here) not in sys.path:
        sys.path.insert(0, str(here))
    import application_ledger  # noqa: PLC0415

    return application_ledger


def state_dir_default() -> Path:
    import os

    return Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def jst_date(value: Any) -> datetime.date | None:
    """Every timestamp shape these files actually use, and nothing invented."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and value > 0:
        try:
            return datetime.datetime.fromtimestamp(float(value), JST).date()
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str) and value.strip():
        text = value.strip()
        # earnings.jsonl: "2026/08/03 10:42" (already JST)
        for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(text, fmt).date()
            except ValueError:
                pass
        try:  # ISO-8601, possibly with offset
            parsed = datetime.datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=JST)
        return parsed.astimezone(JST).date()
    return None


@dataclass(frozen=True)
class Window:
    """A closed JST date interval. ``None`` on either side means unbounded."""

    since: datetime.date | None = None
    until: datetime.date | None = None

    def contains(self, day: datetime.date | None) -> bool:
        if day is None:
            return False
        if self.since is not None and day < self.since:
            return False
        if self.until is not None and day > self.until:
            return False
        return True

    def label(self) -> str:
        lo = self.since.isoformat() if self.since else "開始"
        hi = self.until.isoformat() if self.until else "現在"
        return f"{lo}..{hi}"

    def days(self) -> int | None:
        if self.since is None or self.until is None:
            return None
        return (self.until - self.since).days + 1


@dataclass
class Order:
    """One unit of work, however it entered. Keyed by whatever survives every stage."""

    entry_path: str
    request_id: str = ""          # 募集 id, empty for a direct offer
    talkroom_id: str = ""         # the id money is recorded against
    contract_id: str = ""         # offer:<n> / direct-offer:<n>
    buyer: str = ""
    title: str = ""
    applied_on: datetime.date | None = None
    contracted_on: datetime.date | None = None
    delivered_on: datetime.date | None = None
    paid_on: datetime.date | None = None
    jpy: float = 0.0
    contract_price_jpy: float = 0.0
    revenue_class: str = ""
    trace_break: str = ""         # empty means it traces end to end

    @property
    def key(self) -> str:
        return self.talkroom_id or self.request_id


@dataclass
class Funnel:
    window: Window
    orders: list[Order] = field(default_factory=list)
    applications_in_window: int = 0
    applications_window: Window = field(default_factory=Window)
    revenue_window: Window = field(default_factory=Window)
    notes: list[str] = field(default_factory=list)
    unmeasurable: dict[str, str] = field(default_factory=dict)

    def stage_counts(self) -> dict[str, dict[str, int]]:
        """Per stage: total, and a breakdown by entry path.

        ★ Every stage is filtered by the SAME window. ★ An earlier revision counted the
        later stages all-time while 応募 honoured ``--since/--until``, which made a
        12-day window report 117 applications against all six lifetime payments -- a
        conversion rate inflated by every order won before the window opened.
        """
        out: dict[str, dict[str, int]] = {}
        buckets = {
            STAGE_CONTRACTED: lambda o: self.window.contains(o.contracted_on),
            STAGE_DELIVERED: lambda o: self.window.contains(o.delivered_on),
            STAGE_PAID: lambda o: self.window.contains(o.paid_on),
        }
        for stage, predicate in buckets.items():
            hit = [o for o in self.orders if predicate(o)]
            out[stage] = {
                "total": len(hit),
                ENTRY_APPLICATION: sum(1 for o in hit if o.entry_path == ENTRY_APPLICATION),
                ENTRY_DIRECT_OFFER: sum(1 for o in hit if o.entry_path == ENTRY_DIRECT_OFFER),
                "jpy": round(sum(o.jpy for o in hit), 2),
            }
        # 応募 is the only stage whose population is the whole application log, not the
        # subset that reached a contract. Overwrite it with the real denominator.
        out[STAGE_APPLIED] = {
            "total": self.applications_in_window,
            ENTRY_APPLICATION: self.applications_in_window,
            ENTRY_DIRECT_OFFER: 0,
            "jpy": 0.0,
        }
        out[STAGE_REVIEWED] = {
            "total": 0,
            ENTRY_APPLICATION: 0,
            ENTRY_DIRECT_OFFER: 0,
            "jpy": 0.0,
            "unmeasurable": self.unmeasurable.get(STAGE_REVIEWED, ""),
        }
        return out

    def revenue_by_class(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for order in self.paid_orders():
            out[order.revenue_class] = round(out.get(order.revenue_class, 0.0) + order.jpy, 2)
        return out

    def paid_orders(self) -> list[Order]:
        return sorted(
            (o for o in self.orders if self.window.contains(o.paid_on)),
            key=lambda o: -o.jpy,
        )

    def cohort(self) -> list[Order]:
        """Orders whose APPLICATION falls in the window -- the only honest denominator."""
        return [
            o
            for o in self.orders
            if o.entry_path == ENTRY_APPLICATION and self.window.contains(o.applied_on)
        ]

    def cohort_still_open(self) -> list[Order]:
        return [o for o in self.cohort() if o.paid_on is None]


def build_funnel(
    state_dir: Path,
    *,
    since: datetime.date | None = None,
    until: datetime.date | None = None,
) -> Funnel:
    application_ledger = _load_application_ledger()
    window = Window(since, until)
    funnel = Funnel(window=window)

    chain = application_ledger.IdentityChain.load(state_dir / "identity_chain.jsonl")
    applied_rows = read_rows(state_dir / "applied.jsonl")
    earnings_rows = read_rows(state_dir / "earnings.jsonl")

    # ---- stage 1: 応募 -------------------------------------------------------------
    # Only status=="applied" rows are applications. applied.jsonl is a mixed append log:
    # it also carries dm-*/directmessage-* reply records, b1 nurture sweeps and talkroom
    # progress notes, so len(file) is NOT the application count.
    application_days: dict[str, datetime.date] = {}
    applied_dates: list[datetime.date] = []
    for row in applied_rows:
        if row.get("status") != "applied":
            continue
        day = jst_date(row.get("ts")) or jst_date(row.get("applied_at"))
        if day is None:
            continue
        applied_dates.append(day)
        request_id = str(row.get("requestId") or "").strip()
        if request_id and request_id not in application_days:
            application_days[request_id] = day
    if applied_dates:
        funnel.applications_window = Window(min(applied_dates), max(applied_dates))
    funnel.applications_in_window = sum(1 for d in applied_dates if window.contains(d))

    # ---- projects: the contract + delivery facts ------------------------------------
    orders: dict[str, Order] = {}
    projects_dir = state_dir / "projects"
    if projects_dir.is_dir():
        for project in sorted(projects_dir.iterdir()):
            state_file = project / "state.json"
            if not project.is_dir() or not state_file.exists():
                continue
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                continue
            if not isinstance(state, dict):
                continue
            talkroom_id = str(state.get("talkroom_id") or "").strip()
            request_id = str(state.get("request_id") or "").strip()
            contract_id = str(state.get("source_contract_id") or "").strip()
            # ★ The contract INSTRUMENT is not the entry DOOR. ★ Measured 2026-08-08:
            # project 91000018 (buyer_handle_c) carries source_contract_id "direct-offer:92000006"
            # and yet has a real 募集 id (91000018 != talkroom 90000010), a chain link and
            # application rows -- we applied to the 募集 and the deal was merely *closed*
            # with a direct-offer instrument. Keying the door off the "direct-offer:"
            # prefix moved a ¥13,260 application-won order into the buyer-initiated
            # bucket and understated the application funnel. The door is decided by
            # whether a 募集 exists at all, i.e. whether request_id is a distinct id.
            entry = (
                ENTRY_DIRECT_OFFER
                if not request_id or request_id == talkroom_id
                else ENTRY_APPLICATION
            )
            order = Order(
                entry_path=entry,
                request_id="" if entry == ENTRY_DIRECT_OFFER else request_id,
                talkroom_id=talkroom_id or request_id,
                contract_id=contract_id,
                buyer=str(state.get("buyer") or "").strip(),
                title=str(state.get("title") or "").strip(),
                contract_price_jpy=float(state.get("price_jpy") or 0.0),
            )
            if contract_id:
                order.contracted_on = jst_date(state.get("updated_at")) or jst_date(
                    state.get("observed_at")
                )
            if (
                state.get("work_state") in DELIVERED_STATES
                or state.get("transaction_state") in DELIVERED_STATES
                or state.get("talkroom_state") in DELIVERED_STATES
                or state.get("formal_delivery") is True
            ):
                order.delivered_on = jst_date(state.get("observed_at")) or jst_date(
                    state.get("updated_at")
                )
            if order.request_id:
                order.applied_on = application_days.get(order.request_id)
            orders[order.key] = order

    # ---- stage 4: 入金 ---------------------------------------------------------------
    # earnings.jsonl's "requestId" is a talkroom id. Resolve it back to a 募集 id THROUGH
    # THE CHAIN, never by trusting the field name.
    revenue_days: list[datetime.date] = []
    for row in earnings_rows:
        if row.get("status") not in SETTLED:
            continue
        jpy = float(row.get("jpy") or 0.0)
        if jpy <= 0 or not row.get("evidence"):
            continue
        talkroom_id = str(row.get("talkroom_id") or row.get("requestId") or "").strip()
        day = jst_date(row.get("ts"))
        if day is not None:
            revenue_days.append(day)
        order = orders.get(talkroom_id)
        if order is None:
            # Money with no project directory. Still real money -- recover what identity
            # we can from the chain rather than dropping the row.
            resolved = chain.request_for(talkroom_id) or ""
            order = Order(
                entry_path=ENTRY_APPLICATION if resolved else ENTRY_DIRECT_OFFER,
                request_id=resolved,
                talkroom_id=talkroom_id,
                buyer=str(row.get("buyer") or "").strip(),
            )
            if resolved:
                order.applied_on = application_days.get(resolved)
            orders[talkroom_id] = order
        order.jpy += jpy
        order.paid_on = day
        order.buyer = order.buyer or str(row.get("buyer") or "").strip()
        order.title = str(row.get("title") or "").strip() or order.title
        # Backfill the 募集 id from the chain when the project did not carry one.
        if order.entry_path == ENTRY_APPLICATION and not order.request_id:
            order.request_id = chain.request_for(talkroom_id) or ""
            if order.request_id:
                order.applied_on = application_days.get(order.request_id)
        order.revenue_class = classify_revenue(order)
    if revenue_days:
        funnel.revenue_window = Window(min(revenue_days), max(revenue_days))

    # ---- traceability: name every break, do not silently drop it --------------------
    for order in orders.values():
        if order.paid_on is None:
            continue
        if order.entry_path == ENTRY_DIRECT_OFFER:
            order.trace_break = (
                "direct offer -- never had an application; its offer page carries no "
                "募集 No., so no chain link exists to build"
            )
        elif not order.request_id:
            order.trace_break = (
                f"talkroom {order.talkroom_id} is absent from identity_chain.jsonl, so "
                "the payment cannot be resolved to a 募集"
            )
        elif order.applied_on is None:
            order.trace_break = (
                f"募集 {order.request_id} resolves through the chain, but applied.jsonl "
                'has no status=="applied" row for it -- only later progress rows, so the '
                "application date is unrecorded"
            )

    funnel.orders = list(orders.values())
    funnel.unmeasurable[STAGE_REVIEWED] = (
        "no source: work-events.jsonl emits kinds "
        "payment/contract/application/delivery/reply/incident/recovery and no review "
        "kind; nothing under ~/gig records a buyer rating or its date"
    )
    return funnel


def classify_revenue(order: Order) -> str:
    """Listing revenue vs contract revenue.

    ★ What the data can and cannot tell apart. ★ Every settled row so far carries a
    ``source_contract_id`` of ``offer:`` or ``direct-offer:``, i.e. a negotiated
    transaction opened from a talkroom. A 出品 (listing) sale is a different product --
    a buyer purchases a published service without an offer being drafted -- and it would
    reach earnings.jsonl with NO contract id behind it. So the split is derivable today
    only because the listing side is empty; the moment a listing sells, the row will be
    indistinguishable from a contract row unless the revenue page's own transaction type
    is captured. That gap is reported, not guessed.
    """
    if order.contract_id.startswith("direct-offer:"):
        return "contract:direct-offer"
    if order.contract_id.startswith("offer:"):
        return "contract:offer"
    # Money whose project directory is missing or has no state.json. It is NOT listing
    # revenue -- it is revenue whose instrument was never written down. Saying
    # "listing" here would be a guess; this label says exactly what is unknown.
    return "contract:instrument-unrecorded"


@dataclass
class Ratio:
    """A number that knows its window, or a refusal that knows why."""

    value: float | None
    window: str
    reason: str = ""

    @property
    def refused(self) -> bool:
        return self.value is None


def revenue_per_application(funnel: Funnel) -> Ratio:
    """The PERIOD ratio: yen settled in the window / applications sent in the window.

    ★ Refuses on an unbounded window. ★ With no --since/--until the numerator and the
    denominator silently take their extent from different files -- applications run
    2026-07-01..08-08 (39 days), settled revenue 2026-07-25..08-05 (12 days) -- and
    dividing a 12-day numerator by a 39-day denominator understates the yield by ~3x.
    That is the exact error made on 2026-08-07. A stated window is not optional here.

    Even when bounded this number mixes cohorts: the revenue that lands in a window was
    largely earned by applications sent BEFORE it. It answers "what did this period
    yield", not "what is an application worth". For the latter use
    ``cohort_revenue_per_application``.
    """
    if funnel.window.since is None or funnel.window.until is None:
        apps, rev = funnel.applications_window, funnel.revenue_window
        return Ratio(
            None,
            funnel.window.label(),
            "REFUSED: no window given, so the numerator and denominator would come from "
            "different spans -- applications %s (%s days) vs settled revenue %s (%s "
            "days). Dividing them invents a unit economic no period produced. Pass "
            "--since/--until."
            % (apps.label(), apps.days(), rev.label(), rev.days()),
        )
    if funnel.applications_in_window == 0:
        return Ratio(None, funnel.window.label(), "no applications in the window")
    total = sum(o.jpy for o in funnel.paid_orders())
    return Ratio(round(total / funnel.applications_in_window, 1), funnel.window.label())


def cohort_revenue_per_application(funnel: Funnel) -> Ratio:
    """What an application is actually worth: follow ONE cohort forward.

    Take the applications submitted inside the window and count only the money THOSE
    applications went on to earn, whenever it landed. Both sides of the division name the
    same set of applications by construction, so no window mismatch is possible.

    The caveat that remains is maturation, and it is reported rather than hidden: a
    recent cohort still has open contracts, so its yield is a floor, not a final value.
    """
    if funnel.applications_in_window == 0:
        return Ratio(None, funnel.window.label(), "no applications in the window")
    cohort = funnel.cohort()
    earned = sum(o.jpy for o in cohort if o.paid_on is not None)
    still_open = len(funnel.cohort_still_open())
    note = ""
    if still_open:
        note = (
            f"floor only: {still_open} contract(s) from this cohort are still open and "
            "may still settle"
        )
    return Ratio(
        round(earned / funnel.applications_in_window, 1), funnel.window.label(), note
    )


def render_telegram(funnel: Funnel) -> str:
    """Who, what they ordered verbatim, and what moved. Not generic counts.

    Built to be enqueued through the existing durable ``TelegramOutbox`` -- this function
    only renders. Nothing here sends.
    """
    counts = funnel.stage_counts()
    lines: list[str] = []
    lines.append(f"Claude::: gig funnel {funnel.window.label()}")
    lines.append("")
    order = [STAGE_APPLIED, STAGE_CONTRACTED, STAGE_DELIVERED, STAGE_PAID, STAGE_REVIEWED]
    for stage in order:
        row = counts[stage]
        if stage == STAGE_REVIEWED:
            lines.append(f"{stage}: 計測不能 ({row.get('unmeasurable', '')[:60]}…)")
            continue
        extra = ""
        if row.get("jpy"):
            extra = f"  ¥{row['jpy']:,.0f}"
        direct = row.get(ENTRY_DIRECT_OFFER, 0)
        via = f" (応募経由{row.get(ENTRY_APPLICATION, 0)} / 直接オファー{direct})" if stage != STAGE_APPLIED else ""
        lines.append(f"{stage}: {row['total']}{via}{extra}")

    paid = funnel.paid_orders()
    if paid:
        lines.append("")
        lines.append("入金した相手と、その人が頼んだこと:")
        for o in paid:
            who = o.buyer or "(買い手不明)"
            what = o.title or "(件名なし)"
            if len(what) > 46:
                what = what[:45] + "…"
            door = "直接オファー" if o.entry_path == ENTRY_DIRECT_OFFER else f"募集{o.request_id}"
            lines.append(f"・{who} ¥{o.jpy:,.0f} — 「{what}」 [{door}]")

    broken = [o for o in paid if o.trace_break]
    if broken:
        lines.append("")
        lines.append("応募まで遡れない入金:")
        for o in broken:
            lines.append(f"・{o.buyer or o.talkroom_id}: {o.trace_break[:96]}")

    by_class = funnel.revenue_by_class()
    if by_class:
        lines.append("")
        parts = [f"{k} ¥{v:,.0f}" for k, v in sorted(by_class.items(), key=lambda x: -x[1])]
        lines.append("売上の内訳: " + " / ".join(parts))

    lines.append("")
    cohort = cohort_revenue_per_application(funnel)
    if cohort.refused:
        lines.append(f"応募1件あたり売上: 算出拒否 — {cohort.reason}")
    else:
        tail = f" ※{cohort.reason}" if cohort.reason else ""
        lines.append(
            f"応募1件あたり売上(コホート): ¥{cohort.value:,.1f} ({cohort.window}){tail}"
        )
    ratio = revenue_per_application(funnel)
    if ratio.refused:
        lines.append(f"期間比(入金÷応募): 算出拒否 — {ratio.reason}")
    else:
        lines.append(
            f"期間比(入金÷応募): ¥{ratio.value:,.1f} ({ratio.window}) ※コホート混在"
        )

    message = "\n".join(lines)
    return message[:4096]


def to_json(funnel: Funnel) -> dict[str, Any]:
    ratio = revenue_per_application(funnel)
    cohort = cohort_revenue_per_application(funnel)
    return {
        "window": funnel.window.label(),
        "stages": funnel.stage_counts(),
        "revenue_by_class": funnel.revenue_by_class(),
        "applications_window": funnel.applications_window.label(),
        "revenue_window": funnel.revenue_window.label(),
        "revenue_per_application": {
            "value": ratio.value,
            "window": ratio.window,
            "reason": ratio.reason,
        },
        "cohort_revenue_per_application": {
            "value": cohort.value,
            "window": cohort.window,
            "reason": cohort.reason,
        },
        "paid_orders": [
            {
                "buyer": o.buyer,
                "title": o.title,
                "jpy": o.jpy,
                "entry_path": o.entry_path,
                "request_id": o.request_id,
                "talkroom_id": o.talkroom_id,
                "contract_id": o.contract_id,
                "applied_on": o.applied_on.isoformat() if o.applied_on else None,
                "paid_on": o.paid_on.isoformat() if o.paid_on else None,
                "revenue_class": o.revenue_class,
                "traces_end_to_end": not o.trace_break,
                "trace_break": o.trace_break,
            }
            for o in funnel.paid_orders()
        ],
        "unmeasurable": funnel.unmeasurable,
    }


def _parse_day(text: str | None) -> datetime.date | None:
    if not text:
        return None
    return datetime.date.fromisoformat(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, default=state_dir_default())
    parser.add_argument("--since", type=str, default=None, help="JST date, YYYY-MM-DD")
    parser.add_argument("--until", type=str, default=None, help="JST date, YYYY-MM-DD")
    parser.add_argument("--json", action="store_true", help="emit the funnel as JSON")
    parser.add_argument(
        "--telegram", action="store_true", help="render the Telegram body to stdout"
    )
    parser.add_argument(
        "--enqueue",
        action="store_true",
        help="enqueue the rendered body on the durable outbox (does NOT send; a "
        "dispatcher drains it)",
    )
    parser.add_argument("--outbox", type=Path, default=None)
    args = parser.parse_args(argv)

    funnel = build_funnel(
        args.state_dir, since=_parse_day(args.since), until=_parse_day(args.until)
    )
    if args.telegram or args.enqueue:
        body = render_telegram(funnel)
        if args.enqueue:
            import time

            here = Path(__file__).resolve().parent
            if str(here) not in sys.path:
                sys.path.insert(0, str(here))
            from telegram_outbox import TelegramOutbox  # noqa: PLC0415

            database = args.outbox or (args.state_dir / "telegram-outbox.sqlite3")
            outbox = TelegramOutbox(database)
            now = int(time.time())
            outbox.enqueue(
                event_key=f"gig:funnel:{funnel.window.label()}:{now}",
                kind="gig-funnel",
                message=body,
                created_at=now,
            )
        print(body)
        return 0
    if args.json:
        print(json.dumps(to_json(funnel), ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(to_json(funnel), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
