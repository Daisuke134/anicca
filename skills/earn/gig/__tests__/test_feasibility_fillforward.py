"""test_feasibility_fillforward.py — RED (Phase 2a, feature gig-feasibility-volume).
PROP-002 / REQ-GFV-002 — passprep.py's fill-forward mechanism merges a missing `feasibility_rules`
key from `strategy.default.json` into a live `strategy.json` fixture WITHOUT discarding any other
existing key.
PROP-027 / REQ-GFV-019 — the SAME fill-forward mechanism (widened, not duplicated) also merges
missing `listing_playbook`/`proposal_playbook` keys.

Design contract this test locks in (verification-architecture.md §1 lists this as a Tier1 pure
function, factored out of the file-read exactly like `listings_due`/`cold_start` below):
    passprep.merge_missing_keys(existing: dict, default: dict) -> dict
Adds any key present in `default` but absent (or None) from `existing`; every key already present
in `existing` (including ones whose value differs from `default`) is left byte-for-byte untouched.
Idempotent: if `existing` already has a non-empty `feasibility_rules`, merge is a no-op for that key
(self-improve's own prior edits to that text are never clobbered).

`passprep.py` does not export `merge_missing_keys` yet -> ImportError -> RED.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import passprep  # noqa: E402  RED: merge_missing_keys does not exist yet

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


# A live-shaped fixture matching the REAL strategy.json's 22-key shape (per behavioral-spec.md §0),
# deliberately WITHOUT feasibility_rules/listing_playbook/proposal_playbook.
LIVE_FIXTURE = {
    "version": 1,
    "updated_ts": "2026-07-08T00:00:00Z",
    "max_apply_per_pass": 5,
    "improve_cadence_passes": 4,
    "priority_categories": ["PPT/スライド", "資料作成"],
    "skip_categories": ["占い"],
    "price_defaults": {"PPT/スライド": 8000},
    "proposal_templates": {"PPT/スライド": "..."},
    "profile_blurb": "custom blurb, self-improve-written, must survive",
    "pass_count": 217,
    "notes": "live notes, must survive",
    "category_performance": {"PPT/スライド": {"reply_rate": 0.5}},
    "recommended_focus": ["PPT/スライド"],
    "deprioritize": [],
    "recent_lessons": ["lesson A"],
    "apply_skip_thresholds": {"max_applicants": 12, "min_contracted_to_skip": 1, "min_budget_jpy": 3000},
}
N_ORIGINAL_KEYS = len(LIVE_FIXTURE)

DEFAULT_FIXTURE = {
    "feasibility_rules": {
        "ai_doable": "completable via browser + computer alone",
        "ai_infeasible": "phone-call handling, SMS-required login, physical on-site presence",
    },
    "listing_playbook": "松竹梅 3-tier pricing, モニター価格 for first reviews, 30分 response SLA",
    "proposal_playbook": "5段 proposal structure, 80% of market rate for zero-track-record pricing",
}

merged = passprep.merge_missing_keys(dict(LIVE_FIXTURE), DEFAULT_FIXTURE)

chk("PROP-002: merge adds feasibility_rules key",
    "feasibility_rules" in merged, True)
chk("PROP-002: merged feasibility_rules.ai_doable is non-empty",
    bool(merged.get("feasibility_rules", {}).get("ai_doable")), True)
chk("PROP-002: merge results in N+3 keys (feasibility_rules + listing_playbook + proposal_playbook)",
    len(merged), N_ORIGINAL_KEYS + 3)
chk("PROP-002: every original key's value is byte-for-byte unchanged",
    all(merged[k] == LIVE_FIXTURE[k] for k in LIVE_FIXTURE), True)
chk("PROP-002: profile_blurb (self-improve-written) survives untouched",
    merged["profile_blurb"], "custom blurb, self-improve-written, must survive")
chk("PROP-002: apply_skip_thresholds (live-tuned, max_applicants=12) survives untouched",
    merged["apply_skip_thresholds"]["max_applicants"], 12)

chk("PROP-027: merge adds listing_playbook key",
    "listing_playbook" in merged, True)
chk("PROP-027: merge adds proposal_playbook key",
    "proposal_playbook" in merged, True)
chk("PROP-027: listing_playbook content is traceable to the seed (松竹梅 spot-check phrase present)",
    "松竹梅" in merged.get("listing_playbook", ""), True)

# Idempotency: existing non-empty feasibility_rules is preserved verbatim, never overwritten.
already_customized = dict(LIVE_FIXTURE)
already_customized["feasibility_rules"] = {"ai_doable": "self-improve refined this text", "ai_infeasible": "..."}
merged2 = passprep.merge_missing_keys(dict(already_customized), DEFAULT_FIXTURE)
chk("PROP-002: idempotent — pre-existing non-empty feasibility_rules is NOT overwritten by the default",
    merged2["feasibility_rules"]["ai_doable"], "self-improve refined this text")

print(f"=== test_feasibility_fillforward: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
