"""Tests for the storefront objective. Run: python3 tests/test_b0_objective.py

The defect this guards against is subtle: a lane that always has *something* to say will
always look busy, so the priority order and the draft/published distinction are what decide
whether the storefront actually grows.
"""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import b0_objective  # noqa: E402

FAILURES: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if not ok else ""))
    if not ok:
        FAILURES.append(label)


def state(live=4, target=20, drafts=(), defective=(), known_service_count=4):
    return {
        "live": live,
        "target": target,
        "draft_ids": list(drafts),
        "defective_ids": list(defective),
        "known_service_count": known_service_count,
        "ledger_rows": 0,
    }


def with_ledger(rows, funnel_live=4):
    """Point the module at a temporary state dir and read the real derivation."""
    tmp = tempfile.mkdtemp()
    state_dir = Path(tmp)
    (state_dir / "shuppin.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    (state_dir / "gig-funnel.jsonl").write_text(
        json.dumps({"listings_live": funnel_live}) + "\n", encoding="utf-8"
    )
    original = b0_objective.STATE
    b0_objective.STATE = state_dir
    b0_objective.FUNNEL = state_dir / "gig-funnel.jsonl"
    b0_objective.SHUPPIN = state_dir / "shuppin.jsonl"
    b0_objective.STRATEGY = state_dir / "strategy.json"
    try:
        return b0_objective.storefront_state()
    finally:
        b0_objective.STATE = original


# --- priority order ----------------------------------------------------------
check("a draft outranks everything", b0_objective.decide(
    state(live=1, drafts=["111"], defective=["222"]))["action"] == "publish_draft")
check("a defect outranks growth", b0_objective.decide(
    state(live=1, defective=["222"]))["action"] == "fix_defect")
check("below target creates a listing", b0_objective.decide(
    state(live=4, target=20, known_service_count=4))["action"] == "create_listing")
capacity_recovery = b0_objective.decide(
    state(live=15, target=20, known_service_count=20))
check("below target at platform capacity reuses an existing listing",
      capacity_recovery["action"] == "recover_existing",
      capacity_recovery["action"])
check("capacity recovery forbids another create attempt",
      capacity_recovery.get("must_reuse_existing") is True,
      str(capacity_recovery))
check("capacity recovery treats a capacity rejection as a same-wake fallback",
      "capacity" in capacity_recovery["objective"].lower()
      and "immediately" in capacity_recovery["objective"].lower(),
      capacity_recovery["objective"])
check("at target improves the weakest", b0_objective.decide(
    state(live=20, target=20))["action"] == "improve_weakest")

# --- the distinction that cost a live run ------------------------------------
published_from_draft = with_ledger([
    {"service_id": "4244912", "status": "draft_finished_and_published"},
    {"service_id": "4302213", "status": "published_from_draft"},
])
check("statuses containing both words count as published",
      published_from_draft["draft_ids"] == [], str(published_from_draft["draft_ids"]))

genuine_draft = with_ledger([{"service_id": "999111", "status": "draft"}])
check("a genuine draft is still detected",
      genuine_draft["draft_ids"] == ["999111"], str(genuine_draft["draft_ids"]))

later_published = with_ledger([
    {"service_id": "555", "status": "draft"},
    {"service_id": "555", "status": "published"},
])
check("a draft later published is not offered again",
      later_published["draft_ids"] == [], str(later_published["draft_ids"]))

# --- ledger junk -------------------------------------------------------------
junk = with_ledger([
    {"service_id": "N/A", "status": "draft"},
    {"service_id": "111,222,333", "status": "draft"},
    {"service_id": "777", "status": "draft"},
])
check("placeholders and batches are ignored",
      junk["draft_ids"] == ["777"], str(junk["draft_ids"]))
check("known service count uses unique valid ids",
      junk.get("known_service_count") == 1, str(junk.get("known_service_count")))

torn = tempfile.mkdtemp()
Path(torn, "shuppin.jsonl").write_text('{"service_id":"1","status":"draft"}\nnot json\n', encoding="utf-8")
Path(torn, "gig-funnel.jsonl").write_text(json.dumps({"listings_live": 2}) + "\n", encoding="utf-8")
b0_objective.SHUPPIN = Path(torn, "shuppin.jsonl")
b0_objective.FUNNEL = Path(torn, "gig-funnel.jsonl")
b0_objective.STRATEGY = Path(torn, "strategy.json")
check("a torn line does not stop the decision",
      b0_objective.storefront_state()["draft_ids"] == ["1"])

# --- the objective must name a concrete action -------------------------------
sentence = b0_objective.decide(state(live=4, target=20))["objective"]
check("objective names the gap", "4" in sentence and "20" in sentence, sentence[:80])
check("objective demands verification",
      "confirm" in sentence.lower() or "public" in sentence.lower(), sentence[:80])

print()
if FAILURES:
    print(f"{len(FAILURES)} failed: {FAILURES}")
    sys.exit(1)
print("all b0 objective tests passed")
