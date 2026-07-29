#!/usr/bin/env python3
"""application_ledger.py -- what happened to the application, from the ledgers alone.

Why this exists: the gig loop applied 110 times and could not say what came of any of
them. Measured 2026-07-27 on the real files:

  ~/gig/applied.jsonl   224 rows, and NOT an application ledger. It is the apply lane's
                        AND the nurture lane's AND the pass bookkeeper's shared scratch
                        pad. status = applied 110 / replied 71 / no_action_all_current 24
                        / absent 10 / one-offs. requestId holds "b1-nurture-sweep-pass129"
                        and "talkroom-17943244" next to real 募集 ids. Of the 110
                        applications, 2 ever got a follow-up row under the same requestId.
  ~/gig/earnings.jsonl  2 rows whose requestId is a TALKROOM id (18011694), while
                        applied.jsonl's requestId is a 募集 id (5167108). The join
                        matched zero rows, so category_bandit.py joined on exact title
                        instead -- a string coincidence standing in for identity.

So no reward could be attributed to any application, and every downstream learner (the
X8 bandit, the 50/50 self-improve EVAL, strategy.json keep/revert) was optimising against
an outcome it could not observe. That is upstream of any choice of learning algorithm.

The missing link was already on disk and unused. coconala_queue_snapshot.py walks
talkroom -> offer page and reads the 募集 id off it (OFFER_EXPRESSION,
`No.(\\d+)` / `/requests/(\\d+)`), emitting orders[] = {talkroom_id, request_id}. This
module turns that into a durable, append-only chain and uses it to answer one question
per application: how far did it get?

TAXONOMY (decided here, imported by everyone else, never re-derived)

  event      application  status "applied" -- we submitted a proposal to a 募集
             engagement   status says the deal moved (replied/delivered/...) -- this is
                          progress on an EXISTING application, never a new one. Counting
                          these as applications is what made 224 rows look like 224
                          applications.
             sweep        pass-level bookkeeping ("no_action_all_current"): the lane ran
                          and found nothing to do. It is about the pass, not about any
                          one application.
             unknown      no status. 10 live rows. Silence is not evidence of anything.

  identity   A 募集 id is bare decimal digits. Scoped tokens ("talkroom-17943244",
             "dm-9954245") name a different object and are read as such. Everything else
             ("N/A", "b1-nurture-sweep-pass129") names nothing.
             A bare-digit id is AMBIGUOUS: gig_pass.sh's paid-progress writer falls back
             to the talkroom id in the requestId field. Only the chain disambiguates it.
             Digit length is NOT used -- that is a guess dressed up as a rule.

  chain      (募集 id, talkroom id) pairs, append-only in ~/gig/identity_chain.jsonl,
             each carrying the evidence file it was read from. EXACT MATCH ONLY. A
             talkroom that maps to two 募集 ids resolves to NOTHING and is reported in
             `conflicts`; a wrong attribution teaches a wrong lesson, which is strictly
             worse than an absent one.

  stage      applied < engaged < contracted < paid. A stage is a property of the
             APPLICATION -- the deepest point it ever reached -- not of whichever row was
             read last. Evidence for each:
               engaged     an engagement event under the same 募集 id
               contracted  an engagement event saying so, OR the chain links this 募集 to
                           a talkroom seen in the queue snapshot's ORDERS lane (a deal
                           exists, whatever the agent did or did not write down)
               paid        an earnings row whose identity resolves, THROUGH THE CHAIN, to
                           this 募集 id. Titles are never used.

  honesty    What cannot be attributed is counted, not invented:
               unlinked              applications with no talkroom link yet
               unrecoverable         application/engagement events whose id names nothing
               orphan_engagements    progress on a 募集 we have no application row for --
                                     the pre-history from before this ledger existed
               unattributed_earnings money we received that no application explains

Contract: read-only and never fatal, exactly like listing_ledger.py. Only record_links()
writes, and only ever appends. Nothing here performs or triggers customer-facing work.
"""

# NOTE: no `from __future__ import annotations` -- this repo loads modules through
# importlib spec loaders that never register them in sys.modules, and dataclasses
# resolving *string* annotations look the module up there and crash.

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

CHAIN_FILENAME = "identity_chain.jsonl"

# --- event taxonomy -----------------------------------------------------------
EVENT_APPLICATION = "application"
EVENT_ENGAGEMENT = "engagement"
EVENT_SWEEP = "sweep"
EVENT_UNKNOWN = "unknown"

# --- stage lattice ------------------------------------------------------------
STAGE_APPLIED = "applied"
STAGE_ENGAGED = "engaged"
STAGE_CONTRACTED = "contracted"
STAGE_PAID = "paid"

STAGE_ORDER = (STAGE_APPLIED, STAGE_ENGAGED, STAGE_CONTRACTED, STAGE_PAID)
_STAGE_RANK = {stage: index for index, stage in enumerate(STAGE_ORDER)}

APPLICATION_STATUSES = frozenset({"applied"})

# Statuses that are progress on an existing application, and how deep each one proves.
ENGAGEMENT_STATUS_STAGE = {
    "replied": STAGE_ENGAGED,
    "followed_up": STAGE_ENGAGED,
    "評価依頼": STAGE_CONTRACTED,
    "delivered": STAGE_CONTRACTED,
    "delivered_pending": STAGE_CONTRACTED,
}

# Statuses that report on a PASS, not on an application.
SWEEP_STATUSES = frozenset({
    "no_action_all_current",
    "no_new_client_reply",
    "needs_human",
    "systemic_blocker_0_applied",
    "attempted_not_confirmed_sent",
})

# --- identity kinds -----------------------------------------------------------
ID_REQUEST = "request"      # a coconala 募集 id
ID_TALKROOM = "talkroom"    # a coconala talkroom id
ID_DM = "dm"                # a direct-message thread; not a 募集
ID_NONE = "none"

# Prefixed tokens the ledger actually contains. Anything else scoped is unreadable.
SCOPE_PREFIXES = {
    "talkroom": ID_TALKROOM,
    "room": ID_TALKROOM,
    "dm": ID_DM,
}

# Tokens written when the id is not known. Not identities.
PLACEHOLDER_IDS = frozenset({
    "", "-", "--", "?", "n/a", "na", "none", "null", "nil",
    "unknown", "tbd", "pending", "todo",
})

# An earnings row only counts as money once coconala says it settled. Kept in step with
# gig_funnel.py's SETTLED so "paid" means the same thing in both places.
SETTLED_STATUSES = frozenset({"検収", "支払", "検収完了", "completed", "paid"})


def state_dir() -> Path:
    return Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))


def default_chain_path() -> Path:
    return state_dir() / CHAIN_FILENAME


def read_jsonl(path) -> list:
    """Every dict on its own line. Missing file or corrupt line yields nothing, never raises."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def parse_ts(value):
    """Epoch seconds from int/float/numeric string/ISO 8601. None when unreadable."""
    from datetime import datetime, timezone

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


# --- taxonomy -----------------------------------------------------------------

def classify_event(row: dict) -> str:
    """The one place that decides whether a ledger row is an application."""
    status = str((row or {}).get("status") or "").strip()
    if not status:
        return EVENT_UNKNOWN
    if status in APPLICATION_STATUSES:
        return EVENT_APPLICATION
    if status in ENGAGEMENT_STATUS_STAGE:
        return EVENT_ENGAGEMENT
    if status in SWEEP_STATUSES:
        return EVENT_SWEEP
    return EVENT_UNKNOWN


@dataclass(frozen=True)
class Identity:
    kind: str
    value: str


def identify(value, chain=None) -> Identity:
    """What object does this id token name? The chain is the only disambiguator."""
    text = str(value if value is not None else "").strip()
    if not text or text.lower() in PLACEHOLDER_IDS:
        return Identity(ID_NONE, "")
    if "-" in text:
        prefix, _, rest = text.partition("-")
        kind = SCOPE_PREFIXES.get(prefix.strip().lower())
        if kind and rest.strip().isdigit():
            return Identity(kind, rest.strip())
        return Identity(ID_NONE, "")
    if not text.isdigit():
        return Identity(ID_NONE, "")
    if chain is not None:
        # A bare-digit id may be either. Only recorded fact decides -- never digit count.
        if text in chain.talkroom_ids:
            return Identity(ID_TALKROOM, text)
        if text in chain.request_ids:
            return Identity(ID_REQUEST, text)
    return Identity(ID_REQUEST, text)


# --- identity chain -----------------------------------------------------------

@dataclass(frozen=True)
class IdentityLink:
    request_id: str
    talkroom_id: str
    lane: str = ""          # which queue lane the pair was observed in ("orders", ...)
    source: str = ""        # which extractor produced it
    evidence: str = ""      # the file it was read out of
    ts: float | None = None

    @property
    def pair(self) -> tuple:
        return (self.request_id, self.talkroom_id)


class IdentityChain:
    """募集 id <-> talkroom id, exact pairs only. Ambiguity resolves to None, not a guess."""

    def __init__(self, links: Sequence[IdentityLink] = ()):
        self.links = tuple(links)
        by_request: dict = {}
        by_talkroom: dict = {}
        for link in self.links:
            if not link.request_id or not link.talkroom_id:
                continue
            by_request.setdefault(link.request_id, set()).add(link.talkroom_id)
            by_talkroom.setdefault(link.talkroom_id, set()).add(link.request_id)
        self._by_request = by_request
        self._by_talkroom = by_talkroom
        self.conflicts = frozenset(
            [key for key, values in by_request.items() if len(values) > 1]
            + [key for key, values in by_talkroom.items() if len(values) > 1]
        )

    @classmethod
    def from_links(cls, links: Iterable[IdentityLink]) -> "IdentityChain":
        return cls(tuple(links))

    @classmethod
    def load(cls, path=None) -> "IdentityChain":
        path = Path(path) if path is not None else default_chain_path()
        links = []
        for row in read_jsonl(path):
            request_id = str(row.get("request_id") or "").strip()
            talkroom_id = str(row.get("talkroom_id") or "").strip()
            if not request_id or not talkroom_id:
                continue
            links.append(IdentityLink(
                request_id=request_id,
                talkroom_id=talkroom_id,
                lane=str(row.get("lane") or ""),
                source=str(row.get("source") or ""),
                evidence=str(row.get("evidence") or ""),
                ts=parse_ts(row.get("ts")),
            ))
        return cls(tuple(links))

    @property
    def request_ids(self) -> frozenset:
        return frozenset(self._by_request)

    @property
    def talkroom_ids(self) -> frozenset:
        return frozenset(self._by_talkroom)

    def _resolve(self, index: dict, key: str):
        values = index.get(str(key or "").strip())
        if not values or len(values) > 1:
            return None
        return next(iter(values))

    def talkroom_for(self, request_id):
        return self._resolve(self._by_request, request_id)

    def request_for(self, talkroom_id):
        return self._resolve(self._by_talkroom, talkroom_id)

    def lanes_for(self, request_id) -> frozenset:
        rid = str(request_id or "").strip()
        return frozenset(link.lane for link in self.links if link.request_id == rid and link.lane)

    def pairs(self) -> frozenset:
        return frozenset(link.pair for link in self.links if link.request_id and link.talkroom_id)


def links_from_queue_snapshot(snapshot: dict, *, evidence: str = "", ts=None) -> tuple:
    """Read (募集 id, talkroom id) out of a coconala_queue_snapshot.py document.

    Only orders[] rows that carry BOTH ids yield a link. A direct offer has no 募集
    behind it (real case: talkroom 17943244 -> offer page request_id null), and an
    absent id is left absent.
    """
    if not isinstance(snapshot, dict):
        return ()
    out = []
    for lane in ("orders",):
        for row in snapshot.get(lane) or ():
            if not isinstance(row, dict):
                continue
            request_id = str(row.get("request_id") or "").strip()
            talkroom_id = str(row.get("talkroom_id") or "").strip()
            if not request_id.isdigit() or not talkroom_id.isdigit():
                continue
            out.append(IdentityLink(
                request_id=request_id, talkroom_id=talkroom_id, lane=lane,
                source="queue_snapshot", evidence=evidence, ts=ts,
            ))
    return tuple(out)


def links_from_offer_evidence(path) -> tuple:
    """Read a link out of an `offer-<talkroom id>.json` evidence file.

    coconala_queue_snapshot.py drops one of these per talkroom after running
    OFFER_EXPRESSION against the offer page. The talkroom id is in the filename and the
    募集 id is in the body -- both exact, both already on disk, nothing ever read them.
    """
    path = Path(path)
    stem = path.stem
    if not stem.startswith("offer-"):
        return ()
    talkroom_id = stem[len("offer-"):].strip()
    if not talkroom_id.isdigit():
        return ()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return ()
    if not isinstance(data, dict):
        return ()
    request_id = str(data.get("request_id") or "").strip()
    if not request_id.isdigit():
        # A direct offer has no 募集 behind it. Absent stays absent.
        return ()
    return (IdentityLink(request_id=request_id, talkroom_id=talkroom_id, lane="orders",
                         source="offer_evidence", evidence=str(path)),)


def harvest_links(root=None) -> tuple:
    """Collect every exact link already lying in the state dir. Reads, never writes."""
    root = Path(root) if root is not None else state_dir()
    seen: set = set()
    out = []

    def take(links):
        for link in links:
            if link.pair in seen:
                continue
            seen.add(link.pair)
            out.append(link)

    patterns = ("queue-snapshot-*.json", "queue-pass*.json", "action-queue-*.json")
    for pattern in patterns:
        for path in sorted(root.rglob(pattern)):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError, ValueError):
                continue    # one corrupt evidence file must not cost us the others
            take(links_from_queue_snapshot(data, evidence=str(path)))
    for path in sorted(root.rglob("offer-*.json")):
        take(links_from_offer_evidence(path))
    return tuple(out)


def record_links(links: Iterable[IdentityLink], *, path=None, now=None) -> int:
    """Append pairs not already recorded. Returns how many were added. Never rewrites."""
    path = Path(path) if path is not None else default_chain_path()
    known = IdentityChain.load(path).pairs()
    fresh = []
    seen = set(known)
    for link in links:
        if not link.request_id or not link.talkroom_id or link.pair in seen:
            continue
        seen.add(link.pair)
        fresh.append(link)
    if not fresh:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for link in fresh:
            handle.write(json.dumps({
                "ts": link.ts if link.ts is not None else now,
                "request_id": link.request_id,
                "talkroom_id": link.talkroom_id,
                "lane": link.lane,
                "source": link.source,
                "evidence": link.evidence,
            }, ensure_ascii=False) + "\n")
    return len(fresh)


# --- applications -------------------------------------------------------------

@dataclass(frozen=True)
class Application:
    request_id: str
    stage: str = STAGE_APPLIED
    talkroom_id: str = ""
    category: str = ""
    title: str = ""
    ts: float | None = None
    events: int = 0
    application_recorded: bool = True

    @property
    def linked(self) -> bool:
        return bool(self.talkroom_id)


@dataclass(frozen=True)
class ApplicationLedger:
    applications: tuple = ()
    observations: tuple = ()
    by_stage: dict = field(default_factory=dict)
    # Same stages over the wider observation set. Reporting only `by_stage` printed
    # paid=0 beside two real settled orders, because neither had an 'applied' row.
    observation_by_stage: dict = field(default_factory=dict)
    linked: int = 0
    unlinked: int = 0
    unrecoverable: int = 0
    orphan_engagements: int = 0
    sweep_events: int = 0
    unknown_events: int = 0
    unattributed_earnings: tuple = ()
    linked_observations: int = 0

    def coverage(self) -> dict:
        return {
            "applications": len(self.applications),
            "observations": len(self.observations),
            "by_stage": dict(self.by_stage),
            "observation_by_stage": dict(self.observation_by_stage),
            "linked": self.linked,
            "linked_observations": self.linked_observations,
            "unlinked": self.unlinked,
            "unrecoverable": self.unrecoverable,
            "orphan_engagements": self.orphan_engagements,
            "sweep_events": self.sweep_events,
            "unknown_events": self.unknown_events,
            "unattributed_earnings": list(self.unattributed_earnings),
        }


def _deeper(current: str, candidate: str) -> str:
    return candidate if _STAGE_RANK[candidate] > _STAGE_RANK[current] else current


def paid_request_ids(earnings_rows: Sequence[dict], chain: IdentityChain) -> dict:
    """earnings row -> the 募集 id it belongs to, resolved through the chain only.

    earnings.requestId is a talkroom id in the live ledger, which is exactly why this
    goes through the chain. A row whose identity does not resolve maps to "" and is
    reported as unattributed rather than attached to a plausible-looking application.
    """
    resolved: dict = {}
    for row in earnings_rows or ():
        if str(row.get("status") or "").strip() not in SETTLED_STATUSES:
            continue
        key = str(row.get("requestId") or "").strip()
        candidates = [row.get("requestId"), row.get("talkroom_id")]
        request_id = ""
        for candidate in candidates:
            ident = identify(candidate, chain)
            if ident.kind == ID_TALKROOM:
                request_id = chain.request_for(ident.value) or ""
            elif ident.kind == ID_REQUEST:
                request_id = ident.value
            if request_id:
                break
        resolved[key or (request_id or "?")] = request_id
    return resolved


def build(applied_rows: Sequence[dict], earnings_rows: Sequence[dict], *,
          chain: IdentityChain) -> ApplicationLedger:
    """One record per application, carrying the deepest stage it is proven to have reached."""
    paid = paid_request_ids(earnings_rows, chain)
    paid_requests = {rid for rid in paid.values() if rid}

    applied_ids: set = set()
    engaged_only: set = set()
    stages: dict = {}
    meta: dict = {}
    counts: dict = {}
    unrecoverable = sweep_events = unknown_events = 0

    for row in applied_rows or ():
        if not isinstance(row, dict):
            continue
        kind = classify_event(row)
        if kind == EVENT_SWEEP:
            sweep_events += 1
            continue
        if kind == EVENT_UNKNOWN:
            unknown_events += 1
            continue

        ident = identify(row.get("requestId"), chain)
        request_id = ""
        if ident.kind == ID_REQUEST:
            request_id = ident.value
        elif ident.kind == ID_TALKROOM:
            request_id = chain.request_for(ident.value) or ""
        if not request_id:
            unrecoverable += 1
            continue

        counts[request_id] = counts.get(request_id, 0) + 1
        stages.setdefault(request_id, STAGE_APPLIED)
        record = meta.setdefault(request_id, {})
        ts = parse_ts(row.get("ts")) or parse_ts(row.get("applied_at"))
        if kind == EVENT_APPLICATION:
            applied_ids.add(request_id)
            # The application's own timestamp wins; an engagement's ts only fills a gap.
            if record.get("ts") is None or not record.get("dated_by_application") or (
                    ts is not None and ts < record["ts"]):
                record["ts"] = ts
            record["dated_by_application"] = True
        else:
            engaged_only.add(request_id)
            if record.get("ts") is None and not record.get("dated_by_application"):
                record["ts"] = ts
            stages[request_id] = _deeper(
                stages[request_id],
                ENGAGEMENT_STATUS_STAGE[str(row.get("status") or "").strip()])
        if not record.get("category"):
            record["category"] = str(row.get("category") or "").strip()
        if not record.get("title"):
            record["title"] = str(row.get("title") or "").strip()

    observations = []
    by_stage = {stage: 0 for stage in STAGE_ORDER}
    observation_by_stage = {stage: 0 for stage in STAGE_ORDER}
    linked = unlinked = linked_observations = 0
    for request_id in sorted(applied_ids | engaged_only):
        stage = stages.get(request_id, STAGE_APPLIED)
        talkroom_id = chain.talkroom_for(request_id) or ""
        # A talkroom in the ORDERS lane is a live deal, whatever the agent wrote down.
        if "orders" in chain.lanes_for(request_id):
            stage = _deeper(stage, STAGE_CONTRACTED)
        if request_id in paid_requests:
            stage = _deeper(stage, STAGE_PAID)
        record = meta.get(request_id, {})
        recorded = request_id in applied_ids
        observations.append(Application(
            request_id=request_id,
            stage=stage,
            talkroom_id=talkroom_id,
            category=record.get("category") or "",
            title=record.get("title") or "",
            ts=record.get("ts"),
            events=counts.get(request_id, 0),
            application_recorded=recorded,
        ))
        observation_by_stage[stage] += 1
        if talkroom_id:
            linked_observations += 1
        if not recorded:
            continue                       # orphans are observations, not applications
        by_stage[stage] += 1
        if talkroom_id:
            linked += 1
        else:
            unlinked += 1

    observations.sort(key=lambda a: (a.ts if a.ts is not None else float("inf"),
                                     a.request_id))
    applications = [o for o in observations if o.application_recorded]
    # Money we cannot explain: no 募集 we have ANY row for. Both live payments resolve
    # through the chain onto a 募集 whose only rows are engagements, so they are
    # attributed -- reporting them as unattributed would have been the honest-looking
    # but wrong answer.
    known_requests = applied_ids | engaged_only
    unattributed = tuple(sorted(
        key for key, request_id in paid.items() if request_id not in known_requests))

    return ApplicationLedger(
        applications=tuple(applications),
        observations=tuple(observations),
        by_stage=by_stage,
        observation_by_stage=observation_by_stage,
        linked=linked,
        unlinked=unlinked,
        unrecoverable=unrecoverable,
        orphan_engagements=len(engaged_only - applied_ids),
        sweep_events=sweep_events,
        unknown_events=unknown_events,
        unattributed_earnings=unattributed,
        linked_observations=linked_observations,
    )


def build_from_state(*, applied_path=None, earnings_path=None,
                     chain_path=None) -> ApplicationLedger:
    applied = read_jsonl(applied_path if applied_path is not None
                         else state_dir() / "applied.jsonl")
    earnings = read_jsonl(earnings_path if earnings_path is not None
                          else state_dir() / "earnings.jsonl")
    return build(applied, earnings, chain=IdentityChain.load(chain_path))


def _main(argv=None) -> int:
    import argparse

    import time

    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--applied", default=None)
    parser.add_argument("--earnings", default=None)
    parser.add_argument("--chain", default=None)
    parser.add_argument("--state-dir", default=None,
                        help="where the ledgers and queue evidence live")
    parser.add_argument("--harvest", action="store_true",
                        help="append newly provable (募集, talkroom) pairs to the chain")
    args = parser.parse_args(argv)

    root = Path(args.state_dir) if args.state_dir else state_dir()
    chain_path = Path(args.chain) if args.chain else root / CHAIN_FILENAME

    out = {}
    if args.harvest:
        out["links_added"] = record_links(harvest_links(root), path=chain_path,
                                          now=int(time.time()))
    ledger = build_from_state(
        applied_path=args.applied if args.applied else root / "applied.jsonl",
        earnings_path=args.earnings if args.earnings else root / "earnings.jsonl",
        chain_path=chain_path)
    out.update(ledger.coverage())
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
