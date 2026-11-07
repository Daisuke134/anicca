"""P10-1: deterministic, zero-network, entirely synthetic unit-economics audit.

Not an accounting system, not a production billing connector.
No personal records, provider API calls, payments or real-world interventions.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from collections import defaultdict
import json

KINDS = {"revenue", "inference", "tool", "human", "fee", "assist_seconds"}
STATES = {"VERIFIED_SUCCESS", "VERIFIED_FAILURE", "NO_ACTION", "UNKNOWN"}
TIERS = {"SYNTHETIC", "OBSERVED", "RECONCILED", "ESTIMATED", "UNKNOWN"}
COST_KINDS = {"inference", "tool", "human", "fee"}


@dataclass(frozen=True)
class Work:
    work_item_id: str
    state: str
    outcome_source_ref: str | None
    cost_coverage_complete: bool
    revenue_coverage_complete: bool
    benefit_state: str = "NOT_MEASURED"


@dataclass(frozen=True)
class Event:
    event_id: str
    provider_event_id: str
    work_item_id: str
    kind: str
    amount_minor: int
    currency: str
    source_ref: str
    evidence_tier: str


def _valid_event(event: Event) -> None:
    if not event.event_id or not event.provider_event_id or not event.source_ref:
        raise ValueError("event id, provider id, and evidence source are required")
    if event.kind not in KINDS:
        raise ValueError("unknown kind")
    if event.evidence_tier not in TIERS or event.evidence_tier == "UNKNOWN":
        raise ValueError("UNKNOWN cannot be booked as money")
    if event.currency != "USD":
        raise ValueError("this synthetic demo requires USD; add explicit FX before mixing")
    if type(event.amount_minor) is not int or event.amount_minor < 0:
        raise ValueError("amount_minor must be a nonnegative integer")
    if event.kind == "revenue" and event.evidence_tier == "ESTIMATED":
        raise ValueError("estimated revenue cannot be recognized")


def summarize(works: list[Work], events: list[Event]) -> dict:
    """Aggregate only known events and expose incomplete coverage explicitly.

    All task costs, including failed and no-action tasks, enter the success-cost
    numerator. A missing coverage flag makes verified profit unavailable.
    """
    if len({w.work_item_id for w in works}) != len(works):
        raise ValueError("duplicate work_item_id")
    ids = {w.work_item_id for w in works}
    for w in works:
        if w.state not in STATES:
            raise ValueError("invalid work state")
        if w.state.startswith("VERIFIED_") and not w.outcome_source_ref:
            raise ValueError("verified outcome requires independent source")
    if len({e.event_id for e in events}) != len(events):
        raise ValueError("duplicate event_id")
    if len({e.provider_event_id for e in events}) != len(events):
        raise ValueError("duplicate provider_event_id")
    amounts = defaultdict(lambda: defaultdict(int))
    for e in events:
        _valid_event(e)
        if e.work_item_id not in ids:
            raise ValueError("unallocated source cost: must report separately")
        amounts[e.work_item_id][e.kind] += e.amount_minor

    all_complete = all(w.cost_coverage_complete and w.revenue_coverage_complete for w in works)
    totals = {k: sum(amounts[w.work_item_id][k] for w in works)
              for k in KINDS}
    total_cost = sum(totals[k] for k in COST_KINDS)
    successful = sum(w.state == "VERIFIED_SUCCESS" for w in works)
    assisted = sum(amounts[w.work_item_id]["assist_seconds"] > 0 for w in works)
    verified = {
        "revenue_minor": totals["revenue"] if all_complete else None,
        "cost_minor": total_cost if all_complete else None,
        "contribution_margin_minor": totals["revenue"] - total_cost if all_complete else None,
        "cost_per_verified_success_minor": str(Decimal(total_cost) / successful) if all_complete and successful else None,
    }
    per_work = []
    for w in works:
        a = amounts[w.work_item_id]
        cost = sum(a[k] for k in COST_KIN)
        complete = w.cost_coverage_complete and w.revenue_coverage_complete
        per_work.append({
            "id": w.work_item_id,
            "state": w.state,
            "revenue_minor": a["revenue"] if complete else None,
            "cost_minor": cost if complete else None,
            "margin_minor": a["revenue"] - cost if complete else None,
            "human_seconds": a["assist_seconds"],
            "benefit_state": w.benefit_state,
            "financial_status": "COMPLETE" if complete else "INCOMPLETE",
        })
    return {
        "data_kind": "SYNTHETIC_DEMONSTRATION_ONLY",
        "work_count": len(works),
        "verified_success_count": successful,
        "human_assisted_work_count": assisted,
        "human_seconds_total": totals["assist_seconds"],
        "all_financial_coverage_complete": all_complete,
        "known_event_total_revenue_minor": totals["revenue"],
        "known_event_total_cost_minor": total_cost,
        "verified_financials": verified,
        "per_work": per_work,
        "not_proven": ["real_revenue", "real_profit", "human_welfare", "causal_uplift", "zero_human_company"],
    }


def demo() -> tuple[list[Work], list[Event]]:
    works = [
        Work("A", "VERIFIED_SUCCESS", "synthetic:independent-readback:A", True, True),
        Work("B", "VERIFIED_FAILURE", "synthetic:independent-readback:B", True, True),
        Work("C", "NO_ACTION", "synthetic:safety-stop:C", True, True),
    ]
    def event(i: str, work: str, kind: str, cents: int) -> Event:
        return Event(i, "synthetic-provider:"+i, work, kind, cents, "USD",
                     "synthetic:source:"+i, "SYNTHETIC")
    events = [
        event("a-r", "A", "revenue", 500),
        event("a-i", "A", "inference", 30),
        event("a-t", "A", "tool", 40),
        event("a-f", "A", "fee", 20),
        event("b-i", "B", "inference", 80),
        event("b-t", "B", "tool", 50),
        event("b-h", "B", "human", 100),
        event("b-s", "B", "assist_seconds", 120),
        event("c-i", "C", "inference", 10),
    ]
    return works, events


if __name__ == "__main__":
    w, e = demo()
    print(json.dumps(summarize(w, e), ensure_ascii=False, indent=2, sort_keys=True))
