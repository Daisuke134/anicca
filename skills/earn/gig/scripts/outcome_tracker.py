#!/usr/bin/env python3
"""outcome_tracker.py — durable, append-only outcome ledger for applied Coconala requests.

M1 (gig loop spec §FH' blind spot: docs/loop-engineering/26-gig-loop-asis-tobe-plan.md).
Measured 2026-08-09: request re-inspection evidence only covers ~46h while applications
span 40 days, so "did a human win over us" vs "did the request die unfilled" was
unanswerable. The per-pass evidence that DOES exist (agent-B2/parent.result.json's
current_b2.inspected_requests) lives under ~/gig/evidence/gig-pass-<id>/ and gets GC'd.

This module tracks each applied request across its lifetime, independent of any single
pass's evidence: open -> someone_contracted(n) / closed_unfilled / expired / we_won.

Design (reuses existing primitives, does not reinvent them):
  - request identity + application time: ~/gig/applied.jsonl (existing ledger)
  - "we_won" ground truth: a ~/gig/projects/<request_id>/ directory already exists
    whenever a request converted to a contract (no browser needed for these rows)
  - page parsing: scripts/market_snapshot.parse_market (already extracts 応募人数 /
    契約人数 from the exact page text this loop already reads before every submit)
  - navigation: scripts/cdp_nav_snapshot.hidden_page_target (already the
    non-lease-holding, lock-coordinated way sibling read-only checks -- see
    gig_reality_verify.sh -- visit Coconala pages without contending with B1/B2's
    leased tabs)

Cadence and lane-registration: this is NOT a gig_pass.sh lane (those run per-pass, tens
of times per day, and are already lease/isolation heavy). Matching the existing sibling
precedent (gig_reality_verify.sh, invoked by auditor.sh on its own interval marker, own
CDP mutex), this module is invoked by gig_outcome_tracker.sh on a slow cadence from
auditor.sh -- see the OUTCOME_TRACKER block there. Its failure is isolated: an
unreachable browser, a logged-out session, or a missing script all degrade to "did
nothing this round", never to a crash that could touch the core pass.

Pure functions only below `run()`'s browser call are unit tested without any network;
`run()` accepts `observe_fn` so tests can inject a fake and never open a socket.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Callable

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from market_snapshot import parse_market  # noqa: E402

VERSION = 1

STATUS_OPEN = "open"
STATUS_SOMEONE_CONTRACTED = "someone_contracted"
STATUS_CLOSED_UNFILLED = "closed_unfilled"
STATUS_EXPIRED = "expired"
STATUS_WE_WON = "we_won"
TERMINAL_STATUSES = frozenset(
    {STATUS_SOMEONE_CONTRACTED, STATUS_CLOSED_UNFILLED, STATUS_EXPIRED, STATUS_WE_WON}
)

# ponytail: someone_contracted is treated as terminal for M1 -- a re-check would rarely
# change the win/loss attribution this ledger exists to answer. Revisit if a future
# consumer needs to distinguish "contracted, still recruiting more" from "done".
_NOT_FOUND_MARKERS = ("ページが見つかりません", "お探しのページは見つかりません")

RECHECK_COOLDOWN_SECS_DEFAULT = 20 * 3600  # "at most 1x/day" with slack for run jitter
DEFAULT_BATCH_LIMIT = 15


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def load_applied(applied_path: Path) -> dict[str, dict[str, Any]]:
    """request_id -> {request_id, url, applied_ts}, keeping the EARLIEST applied row."""
    out: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(applied_path):
        if row.get("status") != "applied":
            continue
        request_id = row.get("requestId")
        if not isinstance(request_id, str) or not request_id.isdigit():
            continue
        ts_raw = row.get("ts")
        ts = int(ts_raw) if isinstance(ts_raw, (int, float)) and not isinstance(ts_raw, bool) else 0
        url = row.get("url") or f"https://coconala.com/requests/{request_id}"
        existing = out.get(request_id)
        if existing is None or ts < existing["applied_ts"]:
            out[request_id] = {"request_id": request_id, "url": url, "applied_ts": ts}
    return out


def load_ledger_latest(ledger_path: Path) -> dict[str, dict[str, Any]]:
    """request_id -> latest row. The ledger is append-only; last write wins."""
    latest: dict[str, dict[str, Any]] = {}
    for row in _read_jsonl(ledger_path):
        request_id = row.get("request_id")
        if isinstance(request_id, str):
            latest[request_id] = row
    return latest


def won_request_ids(projects_root: Path) -> set[str]:
    root = Path(projects_root)
    if not root.is_dir():
        return set()
    return {entry.name for entry in root.iterdir() if entry.is_dir() and entry.name.isdigit()}


def classify_observation(text: str | None, accepting: object, navigated_ok: bool) -> dict[str, Any]:
    """One page fetch -> raw signals. Never raises -- a bad page must degrade to
    page_state, not crash the batch (memory: zero must record how it looked)."""
    if not navigated_ok:
        return {
            "page_state": "unreachable",
            "accepting": None,
            "contracted_count": None,
            "applicants_count": None,
        }
    normalized = unicodedata.normalize("NFKC", text or "")
    if not normalized.strip() or any(marker in normalized for marker in _NOT_FOUND_MARKERS):
        return {
            "page_state": "not_found",
            "accepting": None,
            "contracted_count": None,
            "applicants_count": None,
        }
    market = parse_market(normalized, now=time.time())
    return {
        "page_state": "observed",
        "accepting": bool(accepting) if isinstance(accepting, bool) else None,
        "contracted_count": market.get("contracted_count"),
        "applicants_count": market.get("applicants_at_bid"),
    }


def decide_status(observation: dict[str, Any]) -> str:
    """observation -> status. A pure function of the recorded signals only."""
    page_state = observation.get("page_state")
    if page_state == "not_found":
        # The listing itself is gone. Closest honest bucket without inventing a
        # deadline we never observed: functionally identical to expired for
        # win-rate purposes -- we can no longer be told who won it.
        return STATUS_EXPIRED
    if page_state == "unreachable":
        # Transient (timeout/socket) failure, not a fact about the listing. Left as
        # open so the next run retries rather than a flaky network call poisoning
        # the ledger with a false terminal state.
        return STATUS_OPEN
    contracted = observation.get("contracted_count")
    if isinstance(contracted, int) and contracted > 0:
        return STATUS_SOMEONE_CONTRACTED
    if observation.get("accepting") is False:
        return STATUS_CLOSED_UNFILLED
    return STATUS_OPEN


def select_batch(
    applied: dict[str, dict[str, Any]],
    ledger_latest: dict[str, dict[str, Any]],
    won_ids: set[str],
    *,
    now: float,
    batch_limit: int,
    cooldown_secs: int,
) -> list[str]:
    """Deterministic prioritization of requests worth a page visit this run.

    ponytail: never-checked first (newest application first -- freshest applications
    are the most actionable win/loss signal), then stale-checked (oldest check first,
    so no request starves forever). applied.jsonl carries no 募集期限 (application
    deadline) field to rank by; add that ranking if/when one is captured.
    """
    never_checked: list[tuple[int, str]] = []
    stale: list[tuple[float, str]] = []
    for request_id, app in applied.items():
        if request_id in won_ids:
            continue  # handled by won_rows_to_append, no browser needed
        row = ledger_latest.get(request_id)
        if row is not None and row.get("status") in TERMINAL_STATUSES:
            continue  # already resolved, nothing left to learn
        if row is None:
            never_checked.append((app["applied_ts"], request_id))
        else:
            checked_ts = row.get("checked_ts") or 0
            if now - checked_ts >= cooldown_secs:
                stale.append((checked_ts, request_id))
    never_checked.sort(key=lambda item: -item[0])
    stale.sort(key=lambda item: item[0])
    ordered = [request_id for _, request_id in never_checked] + [
        request_id for _, request_id in stale
    ]
    return ordered[: max(batch_limit, 0)]


def won_rows_to_append(
    applied: dict[str, dict[str, Any]],
    ledger_latest: dict[str, dict[str, Any]],
    won_ids: set[str],
    *,
    now: float,
) -> list[dict[str, Any]]:
    """we_won rows for applied requests already confirmed by ~/gig/projects/. No page
    visit required -- the win is already ground truth."""
    rows: list[dict[str, Any]] = []
    for request_id in sorted(won_ids):
        if request_id not in applied:
            continue  # M1 scope: track outcomes only for requests we applied to
        row = ledger_latest.get(request_id)
        if row is not None and row.get("status") == STATUS_WE_WON:
            continue
        rows.append(
            {
                "version": VERSION,
                "request_id": request_id,
                "status": STATUS_WE_WON,
                "checked_ts": int(now),
                "method": "project_state_dir",
                "observation": {
                    "page_state": "not_checked",
                    "accepting": None,
                    "contracted_count": None,
                    "applicants_count": None,
                },
            }
        )
    return rows


def append_rows(ledger_path: Path, rows: list[dict[str, Any]]) -> None:
    """Append-only. Preserves every existing byte -- never opened with mode 'w'."""
    if not rows:
        return
    path = Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def build_rows(
    request_ids: list[str], observations: dict[str, dict[str, Any]], *, now: float
) -> list[dict[str, Any]]:
    rows = []
    for request_id in request_ids:
        observation = observations.get(request_id) or {
            "page_state": "unreachable",
            "accepting": None,
            "contracted_count": None,
            "applicants_count": None,
        }
        rows.append(
            {
                "version": VERSION,
                "request_id": request_id,
                "status": decide_status(observation),
                "checked_ts": int(now),
                "method": "hidden_target_observe",
                "observation": observation,
            }
        )
    return rows


async def _observe_request_page(request_id: str) -> dict[str, Any]:
    """Navigate one request page in an owned hidden target (no lease contention with
    B1/B2's leased tabs -- same pattern as gig_reality_verify.sh) and classify it."""
    # Imported lazily: these pull in `websockets` and require CLOAK_CDP_BASE_URL, which
    # tests never need (they inject observe_fn and never reach this function).
    from cdp_nav_snapshot import LOAD_TIMEOUT_SECS, _call, _wait_for_load, hidden_page_target
    import websockets

    url = f"https://coconala.com/requests/{request_id}"
    text, accepting, navigated_ok = "", None, False
    async with hidden_page_target(url) as ws_url:
        async with websockets.connect(
            ws_url, ping_interval=None, open_timeout=10, max_size=40 * 1024 * 1024
        ) as ws:
            cid = 1
            await _call(ws, "Page.enable", {}, cid)
            cid += 1
            await ws.send(json.dumps({"id": cid, "method": "Page.navigate", "params": {"url": url}}))
            cid += 1
            deadline = asyncio.get_event_loop().time() + LOAD_TIMEOUT_SECS
            navigated_ok, cid = await _wait_for_load(ws, deadline, cid)
            try:
                result = await _call(
                    ws,
                    "Runtime.evaluate",
                    {
                        "expression": (
                            "JSON.stringify((()=>{"
                            "const t=document.body?document.body.innerText.slice(0,120000):'';"
                            "const visible=e=>{if(!e||e.offsetParent===null)return false;"
                            "const r=e.getBoundingClientRect();return r.width>0&&r.height>0;};"
                            "const accepting=[...document.querySelectorAll('button,a')]"
                            ".some(e=>visible(e)&&(e.innerText||'').trim()==='応募する');"
                            "return {text:t,accepting};})())"
                        ),
                        "returnByValue": True,
                    },
                    cid,
                )
                raw = result.get("result", {}).get("result", {}).get("value") or "{}"
                parsed = json.loads(raw)
                text = str(parsed.get("text") or "")
                accepting = parsed.get("accepting")
            except Exception:
                pass  # classify_observation reads navigated_ok/text as-is; never crash the batch
    return classify_observation(text, accepting, navigated_ok)


async def observe_batch(request_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Sequential by design (ponytail: bounded browser load; add concurrency with its
    own target-count guard if batch sizes grow past what a few seconds each affords)."""
    results: dict[str, dict[str, Any]] = {}
    for request_id in request_ids:
        try:
            results[request_id] = await _observe_request_page(request_id)
        except Exception as error:
            results[request_id] = {
                "page_state": "unreachable",
                "accepting": None,
                "contracted_count": None,
                "applicants_count": None,
                "error": f"{type(error).__name__}:{error}",
            }
    return results


ObserveFn = Callable[[list[str]], dict[str, dict[str, Any]]]


def run(
    *,
    applied_path: Path,
    ledger_path: Path,
    projects_root: Path,
    batch_limit: int = DEFAULT_BATCH_LIMIT,
    cooldown_secs: int = RECHECK_COOLDOWN_SECS_DEFAULT,
    now: float | None = None,
    observe_fn: ObserveFn | None = None,
) -> dict[str, Any]:
    now = time.time() if now is None else now
    observe_fn = observe_fn or (lambda ids: asyncio.run(observe_batch(ids)))

    applied = load_applied(applied_path)
    ledger_latest = load_ledger_latest(ledger_path)
    won_ids = won_request_ids(projects_root)

    won_rows = won_rows_to_append(applied, ledger_latest, won_ids, now=now)
    append_rows(ledger_path, won_rows)
    for row in won_rows:
        ledger_latest[row["request_id"]] = row

    batch = select_batch(
        applied, ledger_latest, won_ids, now=now, batch_limit=batch_limit, cooldown_secs=cooldown_secs
    )
    observations = observe_fn(batch) if batch else {}
    fresh_rows = build_rows(batch, observations, now=now)
    append_rows(ledger_path, fresh_rows)

    status_counts = {
        status: sum(1 for row in fresh_rows if row["status"] == status)
        for status in (STATUS_OPEN, STATUS_SOMEONE_CONTRACTED, STATUS_CLOSED_UNFILLED, STATUS_EXPIRED)
    }
    return {
        "ts": int(now),
        "applied_total": len(applied),
        "won_ids_total": len(won_ids),
        "won_rows_appended": len(won_rows),
        "batch_size": len(batch),
        "batch_limit": batch_limit,
        "cooldown_secs": cooldown_secs,
        "status_counts_this_run": status_counts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--applied", required=True, type=Path)
    run_parser.add_argument("--ledger", required=True, type=Path)
    run_parser.add_argument("--projects-root", required=True, type=Path)
    run_parser.add_argument("--batch-limit", type=int, default=DEFAULT_BATCH_LIMIT)
    run_parser.add_argument("--cooldown-secs", type=int, default=RECHECK_COOLDOWN_SECS_DEFAULT)
    args = parser.parse_args(argv)
    if args.command != "run":
        return 2
    summary = run(
        applied_path=args.applied,
        ledger_path=args.ledger,
        projects_root=args.projects_root,
        batch_limit=args.batch_limit,
        cooldown_secs=args.cooldown_secs,
    )
    print(json.dumps(summary, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
