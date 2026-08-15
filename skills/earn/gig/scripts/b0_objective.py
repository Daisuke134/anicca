#!/usr/bin/env python3
"""Decide what the storefront lane should do this pass, and say it in one sentence.

Why this exists: B0's instruction was "inspect the storefront and improve one listing".
That is a maintenance mandate, not a growth one, so the storefront sat at four live
listings for weeks. Applications are supply-capped by how many jobs Coconala posts, but
listings are inbound and have no such ceiling — they are the only lane that can carry the
account toward a million yen a month. A lane with no growth objective cannot self-improve
toward one either, because it never produces the evidence.

So the decision is made in code, deterministically, and handed to the agent as a concrete
target. The agent still does the judgement work — what to write, which listing is weakest —
but it can no longer quietly do nothing.

Priority order, most valuable first:
  1. publish a draft that is already written but unpublished (fastest inbound surface)
  2. fix a listing whose title or body carries a known defect (typos cost trust and clicks)
  3. reuse an existing slot when the platform listing cap is already reached
  4. create a new listing while below target and below the platform cap (growth)
  5. otherwise improve the weakest existing listing (quality)

Usage:
  b0_objective.py                    # one-line objective for the step prompt
  b0_objective.py --json             # the full decision with its inputs
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

STATE = Path(os.environ.get("GIG_STATE_DIR", str(Path.home() / "gig")))
FUNNEL = STATE / "gig-funnel.jsonl"
SHUPPIN = STATE / "shuppin.jsonl"
STRATEGY = STATE / "strategy.json"

DEFAULT_TARGET = 20
PLATFORM_LISTING_CAPACITY = 20

# Defects seen on the live storefront. Kept as data so the agent is told exactly what to
# look for instead of being asked to guess what "improve" means.
KNOWN_DEFECT_MARKERS = ["しますます", "作りますます", "ますます"]


def _rows(path: Path) -> list[dict]:
    out: list[dict] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue          # a torn line must never stop the pass
    return out


def _last(path: Path) -> dict:
    rows = _rows(path)
    return rows[-1] if rows else {}


def target_listings() -> int:
    try:
        strategy = json.loads(STRATEGY.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_TARGET
    value = strategy.get("target_live_listings", DEFAULT_TARGET)
    return int(value) if isinstance(value, (int, float)) else DEFAULT_TARGET


def storefront_state() -> dict:
    funnel = _last(FUNNEL)
    live = int(funnel.get("listings_live") or 0)
    rows = _rows(SHUPPIN)

    drafts, defective, published, known = [], [], set(), set()
    for row in rows:
        status = str(row.get("status") or "")
        title = str(row.get("title") or "")
        sid = str(row.get("service_id") or "")
        # Placeholders and comma-joined batches are not a listing anyone can act on.
        if not sid or sid == "N/A" or "," in sid or not sid.isdigit():
            continue
        known.add(sid)
        # Order matters: statuses such as draft_finished_and_published and
        # published_from_draft contain "draft" but mean the listing is live. Checking
        # published first stops the lane being sent to publish something already public.
        if "publish" in status or "公開" in status:
            published.add(sid)
        elif "draft" in status or "下書き" in status:
            drafts.append(sid)
        if any(marker in title for marker in KNOWN_DEFECT_MARKERS):
            defective.append(sid)
    drafts = [sid for sid in drafts if sid not in published]
    return {
        "live": live,
        "target": target_listings(),
        "draft_ids": sorted(set(drafts)),
        "defective_ids": sorted(set(defective)),
        "known_service_count": len(known),
        "platform_listing_capacity": PLATFORM_LISTING_CAPACITY,
        "ledger_rows": len(rows),
    }


def decide(state: dict) -> dict:
    live, target = state["live"], state["target"]
    must_reuse_existing = False
    if state["draft_ids"]:
        action = "publish_draft"
        sentence = (
            f"PUBLISH one unpublished draft listing (candidates: {', '.join(state['draft_ids'][:3])}). "
            "A written-but-unpublished listing earns nothing; publishing it is the cheapest "
            "increase in inbound surface. Confirm on the real page that it is public, then "
            "append the result to shuppin.jsonl."
        )
    elif state["defective_ids"]:
        action = "fix_defect"
        sentence = (
            f"FIX the defective listing text (candidates: {', '.join(state['defective_ids'][:3])}); "
            "known defects include the typo 'しますます'/'作りますます' in titles. Buyers judge "
            "competence by the title. Verify the corrected text on the live page before recording it."
        )
    elif (
        live < target
        and state.get("known_service_count", 0) >= PLATFORM_LISTING_CAPACITY
    ):
        action = "recover_existing"
        must_reuse_existing = True
        sentence = (
            f"RECOVER one existing listing slot: only {live} are recorded live against a target "
            f"of {target}, but {state['known_service_count']} distinct service IDs are already "
            f"known and Coconala permits {PLATFORM_LISTING_CAPACITY}. Do not open /services/add. "
            "Inspect every page of /mypage/services_lists, choose a draft or paused service, "
            "rewrite it around work this account has actually delivered and been paid for, and "
            "publish or resume it. If the fresh UI shows every existing slot is already public, "
            "improve the weakest live service instead; verified_noop is not a successful outcome. "
            "If a publish or resume attempt returns a capacity rejection, do not stop: immediately "
            "improve one currently public service in the same wake. "
            "Confirm the exact public /services/<id> page before recording."
        )
    elif live < target:
        action = "create_listing"
        sentence = (
            f"CREATE one new listing: {live} are live against a target of {target}. Base it on work "
            "this account has actually delivered and been paid for, so the copy can cite real "
            "outcomes rather than claims. Listings are the only inbound lane and are not capped by "
            "how many jobs Coconala posts. Publish it and confirm it is public before recording."
        )
    else:
        action = "improve_weakest"
        sentence = (
            f"IMPROVE the weakest of the {live} live listings (target {target} is met). Pick by "
            "measured performance where evidence exists, and only record the change once the "
            "browser confirms it."
        )
    return {
        "action": action,
        "objective": sentence,
        "must_reuse_existing": must_reuse_existing,
        **state,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    decision = decide(storefront_state())
    print(json.dumps(decision, ensure_ascii=False) if args.json else decision["objective"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
