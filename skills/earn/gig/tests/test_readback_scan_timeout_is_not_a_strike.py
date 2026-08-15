from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# §FG' (2026-08-09 night, read-only scout): 24 eligible candidates -- incl. two ¥100,000
# jobs -- were permanently exiled into wedge-quarantine.json. Root cause: a CDP timeout
# while _official_readback_async was scanning an UNRELATED applicant's offer page (looking
# for one exact request id, deep in the applied-offers history) was scored as a wedge
# strike against whichever candidate the readback call happened to be checking. Three such
# misattributed strikes and a perfectly healthy, never-attempted candidate is quarantined
# for life -- excluded_request_ids drops it before collection, so the only decrement path
# (a successful confirm) can never run.
#
# The fix distinguishes "this candidate's own action wedged" (still a strike) from "the scan
# hit a slow neighbour's page while checking this candidate" (application_parent.
# ReadbackScanTimeout -> readback_inconclusive, never a strike).

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def build(tmp_path):
    parent = _load(SCRIPTS / "application_parent.py", "application_parent_readback_strike")
    snapshot_module = _load(SCRIPTS / "application_snapshot.py", "application_snapshot_readback_strike")
    collector = {
        "pass_id": "gig-pass-readback-strike",
        "lease_fence": {
            "task": "gig-pass-readback-strike-B2",
            "token": "0123456789abcdef0123456789abcdef",
            "generation": 3,
        },
        "observed_at": "2026-08-09T18:00:00Z",
        "objective": {
            "target_applications": 2,
            "max_applications": 2,
            "required_search_source_ids": ["single:new"],
        },
        "search_sources": [{
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new",
            "page_index": 1,
            "card_request_ids": ["95000011"],
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": "a" * 64,
            "dom_sha256": "b" * 64,
        }],
        "request_details": [{
            "request_id": "95000011",
            "canonical_url": "https://coconala.com/requests/95000011",
            "title": "AI 調査 95000011",
            "category": "リサーチ",
            "visible_text": "募集内容",
            "accepting_applications": True,
            "budget_min_jpy": 100000,
            "budget_max_jpy": 100000,
            "applicants_count": 0,
            "contracted_count": 0,
            "observed_at": "2026-08-09T18:00:00Z",
        }],
        "already_applied_ids": [],
    }
    snapshot = snapshot_module.build_envelope(collector)
    proposal = (
        "募集内容と納品条件を確認しました。対象資料を案件ごとに整理し、必要な情報を原文から確認します。"
        "作業中は要件ごとの対応状況を記録し、完成後は指定形式、表示内容、文字化け、欠落の有無を検証します。"
        "成果物には実施内容と確認結果を添え、購入者が添付を開かなくても重要な結論が分かる説明を記載します。"
        "不明点は既存の会話、添付、関連URLを先に確認し、与えられた情報の範囲で作業可能な部分を完成させます。"
        "納品前に要求事項との対応表を再確認し、根拠のない完了報告や成果物のない進捗連絡は行いません。"
    )
    decisions = {
        "decisions": [{
            "request_id": "95000011",
            "eligibility": "eligible",
            "reason_codes": [],
            "proposal_text": proposal,
            "price_jpy": 100000,
            "deliver_date": "2026-08-14",
        }]
    }
    store = parent.fence.IntentStore(tmp_path / "intents")
    return parent, snapshot, decisions, store


def test_a_readback_scan_timeout_confirming_the_submit_is_not_scored_as_a_strike(tmp_path) -> None:
    """The post-submit exact-id readback hits a neighbour's slow page, not its own outcome."""
    parent, snapshot, decisions, store = build(tmp_path)

    class NeighbourHungEffects(parent.FixtureEffects):
        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            self.exact_id_readback_ids.append(request_id)
            # This candidate's own submit worked; the readback that would confirm it hangs
            # on someone ELSE's offer page while walking the applied-offers history.
            raise parent.ReadbackScanTimeout("cdp_Page.navigate_timeout_after_30s")

    effects = NeighbourHungEffects(snapshot, {})
    results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    assert results[0]["status"] == "readback_inconclusive:ReadbackScanTimeout"
    counts_path = store.root / "wedge-quarantine.json"
    assert not counts_path.exists() or counts_path.read_text(encoding="utf-8").strip() in ("{}", "")
    # A durable PREPARED marker survives untouched -- next pass gets to retry the readback,
    # not a blind resubmit and not a strike.
    assert store.read("95000011")["state"] == parent.fence.PREPARED


def test_three_readback_scan_timeouts_in_a_row_never_reach_quarantine(tmp_path) -> None:
    """Contrast with test_a_form_that_wedges_pass_after_pass_is_quarantined: three of THESE
    must never add up to a strike, let alone a quarantine."""
    parent, snapshot, decisions, store = build(tmp_path)

    class AlwaysNeighbourHungEffects(parent.FixtureEffects):
        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            raise parent.ReadbackScanTimeout("cdp_Page.navigate_timeout_after_30s")

    for _ in range(5):
        effects = AlwaysNeighbourHungEffects(snapshot, {})
        results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)
        assert results[0]["status"] == "readback_inconclusive:ReadbackScanTimeout"

    counts_path = store.root / "wedge-quarantine.json"
    assert not counts_path.exists() or counts_path.read_text(encoding="utf-8").strip() in ("{}", "")


def test_a_prepared_intent_stays_prepared_when_the_reconcile_readback_is_inconclusive(tmp_path) -> None:
    """B1: the PREPARED-reentry readback (reconcile path) must also fail closed.

    If a truncated/hung readback were read as "officially absent", the PREPARED marker
    would be retired and the same request re-prepared and re-submitted -- a duplicate
    application. Inconclusive must leave the marker exactly where it was."""
    parent, snapshot, decisions, store = build(tmp_path)
    first = decisions["decisions"][0]
    intent = parent.fence.intent_payload(
        request_id="95000011",
        snapshot_sha256=snapshot["snapshot_sha256"],
        proposal_text=first["proposal_text"],
        price_jpy=first["price_jpy"],
        deliver_date=first["deliver_date"],
        lease_fence=snapshot["lease_fence"],
    )
    parent.fence._durable_replace(store.intent_path("95000011"), intent)

    class InconclusiveEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture):
            super().__init__(snapshot, fixture)
            self.retired = False

        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            raise parent.ReadbackScanTimeout(
                "official_readback_truncated_after_10_pages_next_page_remains"
            )

    effects = InconclusiveEffects(snapshot, {})
    results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    assert results[0]["status"] == "readback_inconclusive:ReadbackScanTimeout"
    assert store.read("95000011")["state"] == parent.fence.PREPARED
    assert effects.click_count == 0
    assert effects.open_count == 0


def test_a_genuine_own_action_wedge_is_still_a_strike_and_still_recovers_the_target(tmp_path) -> None:
    """Guards against over-correcting: cdp_wedged_row rows that are NOT readback-scan hangs
    on a neighbour must keep striking and recovering exactly as before this fix."""
    parent, snapshot, decisions, store = build(tmp_path)

    class OwnActionWedgedEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture):
            super().__init__(snapshot, fixture)
            self.recoveries = 0

        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            raise parent.ParentContractError("cdp_Page.enable_timeout_after_30s")

        def recover_wedged_target(self) -> bool:
            self.recoveries += 1
            return True

    effects = OwnActionWedgedEffects(snapshot, {})
    parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    # Recovery itself only fires when the loop notices the wedge on the NEXT candidate
    # (see commit_decisions' loop-start check); with one candidate the trailing check still
    # must record the strike so a poisoned form is not silently exempt from quarantine.
    # Live-lineage adaptation: the store is dict-form with a TTL (count + updated_at,
    # 2026-08-08), so read it back through the same loader the commit boundary uses.
    counts = parent.load_wedge_counts(store)
    assert counts.get("95000011") == 1
