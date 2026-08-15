from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


# Measured on 2026-08-06 06:03 and 06:08 (parent log, two consecutive runs):
#
#     {"ok":false,"error":"cdp_browser_wedged_for_every_attempt","results":36}
#
# results=36 means the snapshot walked 36 sources and the planner ran -- the browser was
# healthy seconds earlier. Then the FIRST submission's page killed its renderer, and because
# the commit section deliberately drives one leased target for all candidates, every later
# candidate timed out on the same dead endpoint. Restarting the whole browser and rerunning
# B2 (the pass-level retry) hits the same page and dies the same way: the unit of recovery
# has to be the target, between candidates, not the browser, between passes.
#
# Recovery is sequential replacement -- dispose the dead context, lease a fresh one, carry
# on -- so the commit still never holds two targets at once, which is what the one-target
# rule actually protects.

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
    parent = _load(SCRIPTS / "application_parent.py", "application_parent_wedge_recovery")
    snapshot_module = _load(SCRIPTS / "application_snapshot.py", "application_snapshot_wedge_recovery")
    collector = {
        "pass_id": "gig-pass-wedge-test",
        "lease_fence": {
            "task": "gig-pass-wedge-test-B2",
            "token": "0123456789abcdef0123456789abcdef",
            "generation": 7,
        },
        "observed_at": "2026-08-06T06:00:00Z",
        "objective": {
            "target_applications": 4,
            "max_applications": 7,
            "required_search_source_ids": ["single:new"],
        },
        "search_sources": [{
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new",
            "page_index": 1,
            "card_request_ids": ["91000032", "91000033"],
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": "a" * 64,
            "dom_sha256": "b" * 64,
        }],
        "request_details": [
            {
                "request_id": request_id,
                "canonical_url": f"https://coconala.com/requests/{request_id}",
                "title": f"AI 調査 {request_id}",
                "category": "リサーチ",
                "visible_text": "募集内容",
                "accepting_applications": True,
                "budget_min_jpy": 1000,
                "budget_max_jpy": 5000,
                "applicants_count": 0,
                "contracted_count": 0,
                "observed_at": "2026-08-06T06:00:00Z",
            }
            for request_id in ("91000032", "91000033")
        ],
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
        "decisions": [
            {
                "request_id": detail["request_id"],
                "business_class": "submit_required",
                "reason_codes": [],
                "proposal_text": proposal,
                "price_jpy": 1000,
                "deliver_date": "2026-08-10",
            }
            for detail in snapshot["request_details"]
        ]
    }
    store = parent.fence.IntentStore(tmp_path / "intents")
    return parent, snapshot, decisions, store


def test_a_dead_target_is_replaced_between_candidates(tmp_path) -> None:
    parent, snapshot, decisions, store = build(tmp_path)

    class WedgedEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture):
            super().__init__(snapshot, fixture)
            self.recoveries = 0
            self.wedged = True

        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            if self.wedged:
                raise parent.ParentContractError("cdp_Page.enable_timeout_after_30s")
            return super().authoritative_exact_id_readback(request_id)

        def recover_wedged_target(self) -> bool:
            self.recoveries += 1
            self.wedged = False
            return True

    effects = WedgedEffects(snapshot, {"official_applied_ids": ["91000032", "91000033"]})
    results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    by_id = {row["request_id"]: row for row in results}
    assert by_id["91000032"]["status"] == "submission_runtime_failed:ParentContractError"
    assert "cdp_Page.enable_timeout" in by_id["91000032"]["error"]
    # The dead target was replaced once, and the very next candidate went through on the
    # fresh one instead of inheriting the corpse.
    assert effects.recoveries == 1
    assert by_id["91000033"]["status"] == "confirmed"


def test_a_dead_last_target_is_replaced_before_the_next_wake(tmp_path) -> None:
    parent, snapshot, decisions, store = build(tmp_path)

    class LastTargetWedgedEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture):
            super().__init__(snapshot, fixture)
            self.recoveries = 0

        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            if request_id == "91000033":
                raise parent.ParentContractError("cdp_Page.navigate_timeout_after_30s")
            return super().authoritative_exact_id_readback(request_id)

        def recover_wedged_target(self) -> bool:
            self.recoveries += 1
            return True

    effects = LastTargetWedgedEffects(
        snapshot, {"official_applied_ids": ["91000032", "91000033"]}
    )
    results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    by_id = {row["request_id"]: row for row in results}
    assert by_id["91000032"]["status"] == "confirmed"
    assert by_id["91000033"]["status"].startswith("submission_runtime_failed")
    assert effects.recoveries == 1


def test_a_business_rejection_does_not_replace_the_target(tmp_path) -> None:
    # A form that rejects a proposal is a live, healthy page. Recycling the target on every
    # rejection would tear down a working session for nothing.
    parent, snapshot, decisions, store = build(tmp_path)

    class RejectingEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture):
            super().__init__(snapshot, fixture)
            self.recoveries = 0

        def click_submit(self, request_id: str, **kwargs) -> None:
            if request_id == "91000032":
                raise parent.ParentContractError("application_rejected_by_form")
            return super().click_submit(request_id, **kwargs)

        def recover_wedged_target(self) -> bool:
            self.recoveries += 1
            return True

    effects = RejectingEffects(snapshot, {"official_applied_ids": ["91000033"]})
    results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    by_id = {row["request_id"]: row for row in results}
    assert by_id["91000032"]["status"].startswith("submission_failed:")
    assert effects.recoveries == 0
    assert by_id["91000033"]["status"] == "confirmed"


def test_recovery_releases_the_old_target_lock_before_the_lease_reclaims_it(tmp_path, monkeypatch) -> None:
    # Measured 2026-08-06 06:51: recovery deadlocked inside the lease. The parent holds the
    # target's operation lock for the whole commit; release, in a subprocess, takes LOCK_EX
    # on the SAME file before disposing -- so the parent asked its child to acquire a lock
    # the parent itself was holding, and the child died at the 35-second subprocess limit.
    # The old lock must be gone before the recycler runs, and the new target's lock must be
    # held afterwards.
    import fcntl

    parent, _, _, _ = build(tmp_path)
    monkeypatch.setenv("CLOAK_CONTEXT_LEASES_FILE", str(tmp_path / "leases.json"))

    def flocked(path: Path) -> bool:
        with path.open("a+", encoding="utf-8") as probe:
            try:
                fcntl.flock(probe.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                return True
            fcntl.flock(probe.fileno(), fcntl.LOCK_UN)
            return False

    effects = parent.CdpParentEffects(
        ws_url="ws://127.0.0.1:9222/devtools/page/OLDTARGET",
        evidence_dir=tmp_path / "evidence",
        ledger_path=tmp_path / "applied.jsonl",
        pass_id="wedge-lock-test",
    )
    old_lock = parent._target_lock_path("ws://x/devtools/page/OLDTARGET")
    new_lock = parent._target_lock_path("ws://x/devtools/page/NEWTARGET")

    recycled = []

    def recycler():
        # The lease's release runs here in production and takes LOCK_EX on the old
        # target's operation lock. If the parent still held it, this is the deadlock.
        assert not flocked(old_lock), "old target lock still held while the lease reclaims it"
        recycled.append(True)
        return "ws://127.0.0.1:9222/devtools/page/NEWTARGET"

    effects.ws_recycler = recycler
    with effects.target_lock():
        assert flocked(old_lock)
        assert effects.recover_wedged_target() is True
        assert recycled == [True]
        assert flocked(new_lock), "new target lock must be held after recovery"
    assert not flocked(new_lock), "commit exit must release whichever lock is current"


def test_a_prepared_intent_is_never_quarantined_by_transport_wedges(tmp_path) -> None:
    # PREPARED may already have crossed the irreversible submit boundary. Repeated official
    # readback transport failures recycle the target, but never discard that durable fence.
    parent, snapshot, decisions, store = build(tmp_path)

    class AlwaysWedgedEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture):
            super().__init__(snapshot, fixture)
            self.attempted: list[str] = []

        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            self.attempted.append(request_id)
            if request_id == "91000032":
                raise parent.ParentContractError("cdp_Page.enable_timeout_after_30s")
            return super().authoritative_exact_id_readback(request_id)

        def recover_wedged_target(self) -> bool:
            return True

    statuses = []
    for _ in range(4):
        effects = AlwaysWedgedEffects(snapshot, {"official_applied_ids": ["91000033"]})
        results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)
        by_id = {row["request_id"]: row for row in results}
        statuses.append((by_id["91000032"]["status"], "91000032" in effects.attempted))

    for status, attempted in statuses:
        assert status.startswith("submission_runtime_failed")
        assert attempted is True


def test_a_confirmed_application_clears_its_wedge_count(tmp_path) -> None:
    parent, snapshot, decisions, store = build(tmp_path)
    counts_path = store.root / "wedge-quarantine.json"
    store.root.mkdir(parents=True, exist_ok=True)
    # Timestamped entry (2026-08-08 format): a bare int would decay on load and this
    # test would then exercise decay, not the confirm-clears-count pop path it pins.
    import json as json_module
    import time as time_module
    counts_path.write_text(
        json_module.dumps({"91000032": {"count": 2, "updated_at": time_module.time()}}),
        encoding="utf-8",
    )

    effects = parent.FixtureEffects(
        snapshot, {"official_applied_ids": ["91000032", "91000033"]}
    )
    results = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)
    by_id = {row["request_id"]: row for row in results}
    assert by_id["91000032"]["status"] == "confirmed"
    import json as json_module
    counts = json_module.loads(counts_path.read_text(encoding="utf-8"))
    assert counts.get("91000032") in (None, 0)


def test_effects_without_the_recovery_hook_still_work(tmp_path) -> None:
    # FixtureEffects predates the hook; commit_decisions must not require it.
    parent, snapshot, decisions, store = build(tmp_path)

    class LegacyWedgedEffects(parent.FixtureEffects):
        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            if request_id == "91000032":
                raise parent.ParentContractError("cdp_Page.enable_timeout_after_30s")
            return super().authoritative_exact_id_readback(request_id)

    legacy = LegacyWedgedEffects(snapshot, {"official_applied_ids": ["91000033"]})
    if hasattr(type(legacy), "recover_wedged_target"):
        # If the base class grows a default, that IS the no-hook path.
        pass
    results = parent.commit_decisions(snapshot, decisions, store=store, effects=legacy)
    by_id = {row["request_id"]: row for row in results}
    assert by_id["91000033"]["status"] == "confirmed"
