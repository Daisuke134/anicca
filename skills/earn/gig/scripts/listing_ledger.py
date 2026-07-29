#!/usr/bin/env python3
"""listing_ledger.py -- the single source of truth for "how many listings do we have".

Why this exists: on 2026-07-27 one JST day had three answers -- 日報=7, funnel=4,
台帳=11 -- because three systems each invented their own projection over the same
file, ~/gig/shuppin.jsonl:

  日報   len([row for row in shuppin if action == "shuppin_published"])   -> 7
         publish *rows*, no dedup. Service 4312985 was republished four times, so
         one listing was reported as four.
  funnel len({service_id where action == "shuppin_published"})            -> 4
         distinct published ids -- correct, but with a silent fallback to
         "distinct id ever seen" when nothing was published, so the same field
         could mean two different things on different days.
  台帳   distinct service_id tokens anywhere in the file                  -> 11
         includes drafts, blocked attempts, the literal string "N/A", and one
         cell holding six comma-joined ids.

strategy.json keep/revert and the X8 bandit consume these numbers as a learning
signal, so three answers means the loop optimises against a quantity that does not
exist. This module owns the taxonomy; the three systems import it and are forbidden
from re-deriving counts themselves.

TAXONOMY (explicit, shared, and the only place these decisions are made)

  identity   A listing is identified by its coconala service_id. The ledger is
             agent-written free text, so an id cell may be a placeholder ("N/A"),
             or several ids joined by commas. Placeholders are not listings;
             a comma-joined cell is several listings, not one.

  kind       published  shuppin_published  -- the listing is publicly live
             created    shuppin_created    -- draft exists, NOT live
             blocked    shuppin_blocked    -- the attempt failed, nothing exists
             touched    everything else (edited/reviewed/checked/audit/...) --
                        proves the listing exists, proves nothing about state

  dedup      Counts of *listings* are over distinct service_id. Counts of *events*
             are over rows. Both are exposed under names that say which they are, so
             no caller can pick up one while meaning the other -- that confusion is
             precisely the 7-vs-4 gap.

  identity-gated
             A publish row with no usable service_id cannot be deduplicated, so it
             is never folded into published_listings. It is surfaced as
             unidentified_publish_events so the ambiguity stays visible instead of
             inflating the total. This is the evidence gate: an agent's unverifiable
             self-report must not be able to raise the headline number.

  time       ts is agent-written and appears as epoch int, epoch float, numeric
             string, or ISO 8601 (with Z, with offset, or naive). All are parsed.
             (The old 台帳 counter used isinstance(ts, (int, float)) and silently
             dropped 26 of 104 live rows.) A row whose ts cannot be parsed is
             counted only in unbounded queries and reported as undated_events.

  day        Natural day = JST calendar day, [00:00:00, next 00:00:00) at UTC+9.
             The daily report fires at 09:07 JST and reports the day it names in
             its header, not a rolling 24h window off wall-clock UTC.

Contract: read-only, never fatal. A missing or corrupt ledger yields zeros. This is
a counter; it must never fail a pass that did customer work.
"""

# NOTE: deliberately no `from __future__ import annotations`. This repo loads modules
# through importlib spec loaders that do not register them in sys.modules, and
# dataclasses resolving *string* annotations look the module up there and crash. Eager
# annotations keep the module loadable by every caller in this tree.

import json
import os
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

JST = timezone(timedelta(hours=9))

LEDGER_FILENAME = "shuppin.jsonl"

# --- taxonomy: action -> kind -------------------------------------------------
KIND_PUBLISHED = "published"
KIND_CREATED = "created"
KIND_BLOCKED = "blocked"
KIND_UPDATED = "updated"
KIND_TOUCHED = "touched"

ACTION_KIND = {
    "shuppin_published": KIND_PUBLISHED,
    "shuppin_created": KIND_CREATED,
    "shuppin_blocked": KIND_BLOCKED,
    "shuppin_edited": KIND_UPDATED,
}

# Tokens the agent writes when it does not actually know the id. Not listings.
PLACEHOLDER_SERVICE_IDS = frozenset({
    "", "-", "--", "?", "n/a", "na", "none", "null", "nil",
    "unknown", "tbd", "pending", "todo",
})


def state_dir() -> Path:
    return Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))


def default_ledger_path() -> Path:
    return state_dir() / LEDGER_FILENAME


def classify(action) -> str:
    """Map a raw ledger action string onto the taxonomy. Unknown actions are touches."""
    return ACTION_KIND.get(str(action or "").strip().lower(), KIND_TOUCHED)


def normalize_service_ids(value) -> tuple[str, ...]:
    """Split a free-text service_id cell into the distinct real listing ids it names."""
    if value is None:
        return ()
    out: list[str] = []
    for token in str(value).split(","):
        token = token.strip()
        if not token or token.lower() in PLACEHOLDER_SERVICE_IDS:
            continue
        if token not in out:
            out.append(token)
    return tuple(out)


def parse_ts(value) -> float | None:
    """Epoch seconds from an int, float, numeric string, or ISO 8601 string."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.timestamp()


def jst_day_bounds(day) -> tuple[float, float]:
    """[start, end) epoch seconds of a JST natural day. Accepts date or 'YYYY-MM-DD'."""
    if isinstance(day, datetime):
        day = day.astimezone(JST).date()
    elif isinstance(day, str):
        day = date.fromisoformat(day)
    start = datetime(day.year, day.month, day.day, tzinfo=JST)
    return start.timestamp(), (start + timedelta(days=1)).timestamp()


def jst_day_bounds_for(now: datetime) -> tuple[float, float]:
    """The JST natural day that `now` falls in -- the day the 09:07 report names."""
    return jst_day_bounds(now.astimezone(JST).date())


@dataclass(frozen=True)
class ListingEvent:
    kind: str
    service_ids: tuple[str, ...]
    ts: float | None
    raw_action: str


@dataclass(frozen=True)
class ListingCounts:
    """Every field says whether it counts listings (deduped) or events (rows)."""
    published_listings: int = 0
    published_events: int = 0
    unidentified_publish_events: int = 0
    created_listings: int = 0
    created_events: int = 0
    blocked_events: int = 0
    known_listings: int = 0
    undated_events: int = 0

    @property
    def productive_events(self) -> int:
        """Listing-lane work with a real-world effect: a draft made or a listing published."""
        return self.published_events + self.created_events


def load_events(path: Path | str | None = None) -> list[ListingEvent]:
    path = Path(path) if path is not None else default_ledger_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    events: list[ListingEvent] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if not isinstance(row, dict):
            continue
        action = str(row.get("action") or "")
        events.append(ListingEvent(
            kind=classify(action),
            service_ids=normalize_service_ids(row.get("service_id")),
            ts=parse_ts(row.get("ts")),
            raw_action=action,
        ))
    return events


def _in_window(ts: float | None, since: float | None, until: float | None) -> bool:
    if since is None and until is None:
        return True          # unbounded: undated rows still count
    if ts is None:
        return False         # a windowed question cannot be answered without a date
    if since is not None and ts < since:
        return False
    if until is not None and ts >= until:
        return False
    return True


def count(
    events: Iterable[ListingEvent],
    *,
    since: float | None = None,
    until: float | None = None,
) -> ListingCounts:
    published: set[str] = set()
    created: set[str] = set()
    known: set[str] = set()
    published_events = created_events = blocked_events = 0
    unidentified = undated = 0

    for event in events:
        if not _in_window(event.ts, since, until):
            if event.ts is None:
                undated += 1
            continue
        known.update(event.service_ids)
        if event.kind == KIND_PUBLISHED:
            published_events += 1
            if event.service_ids:
                published.update(event.service_ids)
            else:
                unidentified += 1
        elif event.kind == KIND_CREATED:
            created_events += 1
            created.update(event.service_ids)
        elif event.kind == KIND_BLOCKED:
            blocked_events += 1
        if event.ts is None:
            undated += 1

    return ListingCounts(
        published_listings=len(published),
        published_events=published_events,
        unidentified_publish_events=unidentified,
        created_listings=len(created),
        created_events=created_events,
        blocked_events=blocked_events,
        known_listings=len(known),
        undated_events=undated,
    )


def count_ledger(
    path: Path | str | None = None,
    *,
    since: float | None = None,
    until: float | None = None,
) -> ListingCounts:
    return count(load_events(path), since=since, until=until)


def _main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ledger", default=None)
    parser.add_argument("--day", default=None, help="JST natural day, YYYY-MM-DD")
    args = parser.parse_args(argv)

    path = Path(args.ledger) if args.ledger else default_ledger_path()
    if args.day:
        start, end = jst_day_bounds(args.day)
        counts = count_ledger(path, since=start, until=end)
    else:
        counts = count_ledger(path)
    print(json.dumps(counts.__dict__, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
