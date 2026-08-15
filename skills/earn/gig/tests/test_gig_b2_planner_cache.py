"""D2 (§EW'#2): a crashed B2 pass reuses its planner decisions instead of re-paying
for them.

application_parent.py already commits one target's applications durably (PREPARED ->
CONFIRMED, tested in test_application_atomic_boundary.py). The gap this closes is one
step earlier: the isolated planner call itself (a real model call, sometimes several
per pass -- PLANNER_REQUESTS_PER_CONTEXT batches it) ran in a fresh, per-pass
evidence_dir. A pass that died between the planner returning and commit_decisions
finishing threw that model call away; the next pass built a new evidence_dir and asked
the planner again over what was usually the same listings.

These tests cover the new pass-independent content fingerprint, the fail-closed cache
load (stale key / expired / consumed / corrupt / missing -> always None, never a
guess), and that run_parent() actually skips invoke_isolated_planner on a resumed pass
and stops offering the cache once a commit runs to completion.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PARENT_SCRIPT = SCRIPTS / "application_parent.py"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import application_snapshot as snapshot_contract  # noqa: E402


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _collector_input(*, request_id: str = "91000032", brief: str = "詳細", applicants: int = 0) -> dict:
    return {
        "pass_id": "gig-pass-cache-test",
        "lease_fence": {"task": "gig-cache-test-B2", "token": "0" * 32, "generation": 7},
        "observed_at": "2026-08-09T00:00:00Z",
        "objective": {
            "target_applications": 4,
            "max_applications": 7,
            "required_search_source_ids": ["single:new"],
        },
        "search_sources": [{
            "source_id": "single:new",
            "url": "https://coconala.com/requests?sort=new",
            "page_index": 1,
            "card_request_ids": [request_id],
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": "a" * 64,
            "dom_sha256": "b" * 64,
        }],
        "request_details": [{
            "request_id": request_id,
            "canonical_url": f"https://coconala.com/job_matching/requests/{request_id}",
            "title": "AI 調査",
            "category": "リサーチ",
            "visible_text": f"募集内容\n{brief}",
            "accepting_applications": True,
            "budget_min_jpy": 1000,
            "budget_max_jpy": 5000,
            "applicants_count": applicants,
            "contracted_count": 0,
            "observed_at": "2026-08-09T00:00:00Z",
        }],
        "already_applied_ids": [],
    }


def _envelope(**kwargs) -> dict:
    return snapshot_contract.build_envelope(_collector_input(**kwargs))


def _fresh_open_detail(parent, detail: dict) -> dict:
    fresh = {
        **detail,
        "page_state": "present",
        "accepting_control": "present",
        "deadline_state": "future",
        "deadline_value": "2026-08-20",
        "form_state": "present",
    }
    fresh["lifecycle_sha256"] = parent._lifecycle_digest(
        fresh["request_id"], fresh["canonical_url"],
        **{field: fresh[field] for field in parent._LIFECYCLE_FIELDS},
    )
    return fresh


# application_planner.MIN_PROPOSAL_CHARS is 200; commit_decisions revalidates decisions
# against that contract even when they came from the cache, so every fixture proposal
# below must clear it.
_VALID_PROPOSAL_TEXT = (
    "要件を確認し、根拠つきで丁寧に調査結果を納品いたします。実績と手順を踏まえ、期日までに正確な成果物をお届けします。"
    "ご不明点があればいつでもご連絡ください。誠実に対応いたします。過去の類似案件の経験を活かし、"
    "品質を担保しながら着実に進めます。進捗は都度共有し、認識のズレがないよう努めます。"
    "必要に応じて追加のヒアリングを行い、ご期待に沿う成果物を目指します。何卒よろしくお願い申し上げます。"
    "納期は厳守いたします。"
)
assert len(_VALID_PROPOSAL_TEXT) >= 200


# ---------------------------------------------------------------------------
# _content_fingerprint: pass-independent identity
# ---------------------------------------------------------------------------

def test_content_fingerprint_ignores_pass_identity_and_volatile_counters() -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_fingerprint_stable")
    base = _envelope()
    other = dict(_collector_input(applicants=5))
    other["pass_id"] = "gig-pass-cache-test-2"
    other["lease_fence"] = {"task": "gig-cache-test-B2-2", "token": "1" * 32, "generation": 9}
    other["observed_at"] = "2026-08-09T04:00:00Z"
    other_envelope = snapshot_contract.build_envelope(other)

    # Every field a real second pass changes by construction differs...
    assert base["snapshot_sha256"] != other_envelope["snapshot_sha256"]
    assert base["pass_id"] != other_envelope["pass_id"]
    # ...but the judgeable content is identical, so the fingerprint must match.
    assert parent._content_fingerprint(base) == parent._content_fingerprint(other_envelope)


def test_content_fingerprint_changes_when_the_brief_changes() -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_fingerprint_sensitive")
    base = _envelope()
    changed = _envelope(brief="要件が変更されました")
    assert parent._content_fingerprint(base) != parent._content_fingerprint(changed)


def test_content_fingerprint_changes_when_already_applied_ids_change() -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_fingerprint_applied")
    base = _envelope()
    other = dict(_collector_input())
    other["already_applied_ids"] = ["9999999"]
    other_envelope = snapshot_contract.build_envelope(other)
    assert parent._content_fingerprint(base) != parent._content_fingerprint(other_envelope)


# ---------------------------------------------------------------------------
# load/save/consume: fail-closed cache primitives
# ---------------------------------------------------------------------------

def test_cache_hit_returns_the_saved_decisions(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_cache_hit")
    cache_path = tmp_path / "cache.json"
    decisions = {"decisions": [{"request_id": "91000032", "business_class": "submit_required"}]}
    parent.save_planner_cache(cache_path, "key-a", decisions, ["91000083"], "pass-1")

    hit = parent.load_cached_decisions(cache_path, "key-a", ttl_seconds=3600)

    assert hit == {"decisions": decisions, "planner_missing_request_ids": ["91000083"]}


def test_cache_v1_binary_decisions_are_ignored_after_policy_contract_change(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_cache_old_binary_policy")
    cache_path = tmp_path / "cache.json"
    cache_path.write_text(json.dumps({
        "version": 1,
        "content_key": "key-a",
        "decisions": {"decisions": [{"request_id": "91000032", "eligibility": "eligible"}]},
        "planner_missing_request_ids": [],
        "pass_id": "old-pass",
        "created_at": "2026-08-13T00:00:00Z",
        "created_at_epoch": 1_000_000,
        "consumed": False,
    }), encoding="utf-8")

    assert parent.load_cached_decisions(cache_path, "key-a", ttl_seconds=3600, now=1_000_100) is None


def test_cache_miss_on_content_key_mismatch_stale_ignore_and_redo(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_cache_mismatch")
    cache_path = tmp_path / "cache.json"
    parent.save_planner_cache(cache_path, "key-a", {"decisions": []}, [], "pass-1")

    assert parent.load_cached_decisions(cache_path, "key-b", ttl_seconds=3600) is None


def test_cache_miss_when_expired_hit_within_ttl(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_cache_ttl")
    cache_path = tmp_path / "cache.json"
    parent.save_planner_cache(cache_path, "key-a", {"decisions": []}, [], "pass-1")
    created_at_epoch = json.loads(cache_path.read_text(encoding="utf-8"))["created_at_epoch"]
    later = created_at_epoch + 100

    assert parent.load_cached_decisions(cache_path, "key-a", ttl_seconds=10, now=later) is None
    assert parent.load_cached_decisions(cache_path, "key-a", ttl_seconds=1000, now=later) is not None


def test_cache_miss_once_consumed(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_cache_consumed")
    cache_path = tmp_path / "cache.json"
    parent.save_planner_cache(cache_path, "key-a", {"decisions": []}, [], "pass-1")

    parent.mark_planner_cache_consumed(cache_path, "key-a")

    assert parent.load_cached_decisions(cache_path, "key-a", ttl_seconds=3600) is None


def test_cache_miss_on_missing_file(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_cache_missing")
    assert parent.load_cached_decisions(tmp_path / "absent.json", "key-a", ttl_seconds=3600) is None


def test_cache_miss_on_corrupt_file(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_cache_corrupt")
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{not valid json", encoding="utf-8")
    assert parent.load_cached_decisions(cache_path, "key-a", ttl_seconds=3600) is None


def test_mark_consumed_leaves_a_foreign_content_key_untouched(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "app_parent_cache_foreign")
    cache_path = tmp_path / "cache.json"
    parent.save_planner_cache(cache_path, "key-a", {"decisions": []}, [], "pass-1")

    parent.mark_planner_cache_consumed(cache_path, "key-other")

    assert parent.load_cached_decisions(cache_path, "key-a", ttl_seconds=3600) is not None


# ---------------------------------------------------------------------------
# run_parent(): the actual crash-and-resume boundary
# ---------------------------------------------------------------------------

class _FakeCommitEffects:
    """Implements the same surface as CdpParentEffects, no browser involved."""

    def __init__(self, *, ws_url: str, evidence_dir: Path, ledger_path: Path, pass_id: str) -> None:
        self.ws_url = ws_url
        self.ws_recycler = None
        self.detail_by_id: dict = {}
        self._filled: dict = {}
        self.ledger: list = []

    @contextlib.contextmanager
    def target_lock(self):
        yield

    def reextract_detail(self, request_id: str) -> dict:
        return self.detail_by_id[request_id]

    def open_form(self, request_id: str) -> None:
        pass

    def adjust_offer_price(self, request_id: str, price_jpy: int) -> int:
        return price_jpy

    def fill_form(self, request_id: str, proposal_text: str, price_jpy: int, deliver_date: str) -> None:
        self._filled[request_id] = {
            "proposal_text": proposal_text, "price_jpy": price_jpy, "deliver_date": deliver_date,
        }

    def readback_form(self, request_id: str) -> dict:
        return self._filled[request_id]

    def click_confirm(self, request_id: str) -> None:
        pass

    def click_submit(self, request_id: str) -> None:
        pass

    def authoritative_exact_id_readback(self, request_id: str) -> bool:
        return True

    def canonical_ledger_append(self, row: dict) -> None:
        self.ledger.append(row)

    def crash_if_requested(self, checkpoint: str) -> None:
        pass

    def finalize_exact_readback(self, request_ids) -> None:
        pass


def _write_fake_lease_script(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        "command = sys.argv[1]\n"
        "if command == 'acquire':\n"
        "    print(json.dumps({'ok': True, 'ws': 'ws://leased-target',"
        " 'token': '0' * 32, 'generation': 7}))\n"
        "else:\n"
        "    print(json.dumps({'ok': True}))\n",
        encoding="utf-8",
    )


def test_run_parent_reuses_cached_decisions_after_a_crash_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The D2 gate: a failed pass becomes a resume point, not a repeated model call."""
    parent = _load(PARENT_SCRIPT, "app_parent_run_resume")

    envelope = _envelope()
    decisions = {
        "decisions": [{
            "request_id": "91000032",
            "business_class": "submit_required",
            "reason_codes": [],
            "proposal_text": _VALID_PROPOSAL_TEXT,
            "price_jpy": 1000,
            "deliver_date": "2026-08-10",
        }],
    }
    calls = {"planner": 0}

    def fake_invoke_isolated_planner(**_kwargs):
        calls["planner"] += 1
        return decisions, []

    def fake_collect(collector, _lease_fence):
        collector.effects.detail_by_id = {
            detail["request_id"]: _fresh_open_detail(parent, detail)
            for detail in envelope["request_details"]
        }
        return envelope

    monkeypatch.setattr(parent, "invoke_isolated_planner", fake_invoke_isolated_planner)
    monkeypatch.setattr(parent, "collect_snapshot_with_readonly_retry", fake_collect)
    monkeypatch.setattr(parent, "CdpParentEffects", _FakeCommitEffects)

    lease_script = tmp_path / "lease.py"
    _write_fake_lease_script(lease_script)
    context_path = tmp_path / "b2-context.json"
    context_path.write_text(json.dumps({
        "target_applications": 4,
        "max_applications": 7,
        "required_search_source_ids": ["single:new"],
    }), encoding="utf-8")
    cache_path = tmp_path / "planner-cache.json"

    def run_once(evidence_dir: Path) -> dict:
        return parent.run_parent(
            lease_script=lease_script,
            lease_task="gig-cache-test-B2",
            context_path=context_path,
            pass_id="gig-pass-cache-test",
            evidence_dir=evidence_dir,
            intent_root=tmp_path / "application-intents",
            ledger_path=tmp_path / "applied.jsonl",
            output_path=evidence_dir / "output.json",
            planner_runner=Path("/unused-planner-runner"),
            planner_schema=Path("/unused-planner-schema"),
            planner_workdir=tmp_path,
            planner_timeout_seconds=5,
            heartbeat_seconds=5.0,
            planner_cache_path=cache_path,
            planner_cache_ttl_seconds=3600,
        )

    # Pass 1: the planner runs for real (once) and the pass then dies before commit
    # finishes -- simulated by making the commit stage raise.
    real_pipeline = parent._run_parent_pipeline

    def crashing_pipeline(**_kwargs):
        raise RuntimeError("simulated kill mid-commit")

    parent._run_parent_pipeline = crashing_pipeline
    try:
        with pytest.raises(RuntimeError, match="simulated kill mid-commit"):
            run_once(tmp_path / "pass-1")
    finally:
        parent._run_parent_pipeline = real_pipeline

    assert calls["planner"] == 1
    cached_after_crash = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cached_after_crash["consumed"] is False
    assert cached_after_crash["decisions"] == decisions

    # Pass 2: the next wake collects the identical listing (fresh_collect is
    # deterministic here) and the real commit pipeline is restored. The planner must
    # NOT be invoked again -- the cached decisions from pass 1 are reused and then
    # retired once the commit runs to completion.
    result = run_once(tmp_path / "pass-2")

    assert calls["planner"] == 1, "planner re-invoked on identical content after resume"
    assert result["decisions"] == decisions
    assert result["results"][0]["request_id"] == "91000032"
    assert result["results"][0]["status"] in {"confirmed", "reconciled_confirmed"}
    cached_after_commit = json.loads(cache_path.read_text(encoding="utf-8"))
    assert cached_after_commit["consumed"] is True


def test_run_parent_ignores_a_stale_cache_and_pays_for_a_fresh_planner_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Content changed between passes (a normal, non-crash wake) -> the cache must not
    be trusted even though it is unconsumed and within its TTL."""
    parent = _load(PARENT_SCRIPT, "app_parent_run_stale_cache")

    envelope = _envelope(brief="更新前の要件")
    decisions = {
        "decisions": [{
            "request_id": "91000032",
                "business_class": "submit_required",
            "reason_codes": [],
            "proposal_text": _VALID_PROPOSAL_TEXT,
            "price_jpy": 1000,
            "deliver_date": "2026-08-10",
        }],
    }
    calls = {"planner": 0}

    def fake_invoke_isolated_planner(**_kwargs):
        calls["planner"] += 1
        return decisions, []

    def fake_collect(collector, _lease_fence):
        collector.effects.detail_by_id = {
            detail["request_id"]: _fresh_open_detail(parent, detail)
            for detail in envelope["request_details"]
        }
        return envelope

    monkeypatch.setattr(parent, "invoke_isolated_planner", fake_invoke_isolated_planner)
    monkeypatch.setattr(parent, "collect_snapshot_with_readonly_retry", fake_collect)
    monkeypatch.setattr(parent, "CdpParentEffects", _FakeCommitEffects)

    lease_script = tmp_path / "lease.py"
    _write_fake_lease_script(lease_script)
    context_path = tmp_path / "b2-context.json"
    context_path.write_text(json.dumps({
        "target_applications": 4,
        "max_applications": 7,
        "required_search_source_ids": ["single:new"],
    }), encoding="utf-8")
    cache_path = tmp_path / "planner-cache.json"

    # A cache entry left over from a different market snapshot: unconsumed, fresh, but
    # keyed to content the current wake does not see.
    parent.save_planner_cache(cache_path, "some-other-content-key", decisions, [], "pass-0")

    parent.run_parent(
        lease_script=lease_script,
        lease_task="gig-cache-test-B2",
        context_path=context_path,
        pass_id="gig-pass-cache-test",
        evidence_dir=tmp_path / "pass-1",
        intent_root=tmp_path / "application-intents",
        ledger_path=tmp_path / "applied.jsonl",
        output_path=tmp_path / "pass-1" / "output.json",
        planner_runner=Path("/unused-planner-runner"),
        planner_schema=Path("/unused-planner-schema"),
        planner_workdir=tmp_path,
        planner_timeout_seconds=5,
        heartbeat_seconds=5.0,
        planner_cache_path=cache_path,
        planner_cache_ttl_seconds=3600,
    )

    assert calls["planner"] == 1, "a content-mismatched cache must not suppress the planner call"
