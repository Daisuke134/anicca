"""Regression contract for the parent-owned Gig application boundary.

These tests deliberately exercise the real command/module interfaces. Browser effects
are represented by injected deterministic fakes only after the parent boundary exists;
no test opens a live CDP connection.
"""

from __future__ import annotations

import importlib.util
import contextlib
import json
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SCHEMAS = ROOT / "schemas"
SNAPSHOT_SCRIPT = SCRIPTS / "application_snapshot.py"
PLANNER_SCRIPT = SCRIPTS / "application_planner.py"
FENCE_SCRIPT = SCRIPTS / "application_effect_fence.py"
PARENT_SCRIPT = SCRIPTS / "application_parent.py"
RUNNER_SCRIPT = ROOT.parents[0] / "agent-runner" / "agent_runner.py"
RUNNER_CONFIG = ROOT.parents[0] / "agent-runner" / "config.json"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _snapshot_input() -> dict:
    return {
        "pass_id": "gig-pass-atomic-test",
        "lease_fence": {
            "task": "gig-pass-atomic-test-B2",
            "token": "0123456789abcdef0123456789abcdef",
            "generation": 7,
        },
        "observed_at": "2026-08-02T12:00:00Z",
        "objective": {
            "target_applications": 4,
            "max_applications": 7,
            "required_search_source_ids": ["single:new"],
        },
        "search_sources": [{
            "source_id": "single:new",
            "url": "https://COCONALA.com/requests?utm_source=ignored&sort=new",
            "page_index": 1,
            "card_request_ids": ["91000032"],
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": "a" * 64,
            "dom_sha256": "b" * 64,
        }],
        "request_details": [{
            "request_id": "91000032",
            "canonical_url": "https://coconala.com/job_matching/requests/91000032?ref=home",
            "title": "AI 調査",
            "category": "リサーチ",
            "visible_text": "募集内容\r\n\r\n  詳細  ",
            "accepting_applications": True,
            "budget_min_jpy": 1000,
            "budget_max_jpy": 5000,
            "applicants_count": 0,
            "contracted_count": 0,
            "observed_at": "2026-08-02T12:00:00Z",
        }],
        "already_applied_ids": [],
    }


def test_snapshot_cli_emits_hash_bound_strict_canonical_envelope(tmp_path: Path) -> None:
    """The planner must only receive a canonical, identity/hash-bound snapshot."""
    input_path = tmp_path / "collector.json"
    output_path = tmp_path / "snapshot.json"
    input_path.write_text(json.dumps(_snapshot_input()), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(SNAPSHOT_SCRIPT),
            "build",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ],
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    envelope = json.loads(output_path.read_text(encoding="utf-8"))
    assert set(envelope) == {
        "version",
        "pass_id",
        "lease_fence",
        "observed_at",
        "objective",
        "search_sources",
        "request_details",
        "already_applied_ids",
        "snapshot_sha256",
    }
    assert envelope["search_sources"][0]["url"] == (
        "https://coconala.com/requests?sort=new"
    )
    detail = envelope["request_details"][0]
    assert detail["canonical_url"] == "https://coconala.com/requests/91000032"
    # The snapshot contract preserves leading innerText whitespace; only line-end
    # whitespace is stripped before repeated blank lines are collapsed.
    assert detail["visible_text"] == "募集内容\n\n  詳細"
    assert len(detail["content_sha256"]) == 64
    assert len(envelope["snapshot_sha256"]) == 64


def test_snapshot_allows_every_configured_source_beyond_candidate_batch() -> None:
    """Source coverage is not capped by the 40 request-detail planner batch."""
    snapshot = _load(SNAPSHOT_SCRIPT, "application_snapshot_source_cap_red")
    collector = _snapshot_input()
    source_ids = ["single:new"] + [f"single:category:source-{index}" for index in range(60)]
    collector["objective"]["required_search_source_ids"] = source_ids
    collector["search_sources"] = [
        {
            "source_id": source_id,
            "url": f"https://coconala.com/requests?keyword=source-{index}",
            "page_index": 1,
            "card_request_ids": ["91000032"] if index == 0 else [],
            "has_next": False,
            "exhausted": True,
            "screenshot_sha256": f"{index + 1:064x}",
            "dom_sha256": f"{index + 101:064x}",
        }
        for index, source_id in enumerate(source_ids)
    ]

    envelope = snapshot.build_envelope(collector)

    assert len(envelope["search_sources"]) == 61
    assert len(envelope["request_details"]) == 1
    assert snapshot.validate_snapshot(envelope) == []


def test_planner_cli_rejects_non_one_to_one_decisions_and_effect_claims(tmp_path: Path) -> None:
    """Planner output is judgments only: every snapshot ID exactly once, no effects."""
    collector_path = tmp_path / "collector.json"
    snapshot_path = tmp_path / "snapshot.json"
    collector_path.write_text(json.dumps(_snapshot_input()), encoding="utf-8")
    snapshot_proc = subprocess.run(
        [
            sys.executable,
            str(SNAPSHOT_SCRIPT),
            "build",
            "--input",
            str(collector_path),
            "--output",
            str(snapshot_path),
        ],
        text=True,
        capture_output=True,
    )
    assert snapshot_proc.returncode == 0, snapshot_proc.stderr
    decisions_path = tmp_path / "decisions.json"
    decisions_path.write_text(json.dumps({
        "decisions": [{
            "request_id": "91000032",
            "business_class": "submit_required",
            "reason_codes": [],
            "proposal_text": "依頼内容を確認し、根拠を整理して成果物として分かりやすく納品します。" * 20,
            "price_jpy": 1000,
            "deliver_date": "2026-08-03",
            "submit_verified": True,
        }],
    }), encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            str(PLANNER_SCRIPT),
            "validate",
            "--snapshot",
            str(snapshot_path),
            "--decisions",
            str(decisions_path),
        ],
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 2
    assert "additional" in (proc.stdout + proc.stderr).lower()


def test_planner_accepts_complete_decisions_when_model_order_differs_from_snapshot(
    tmp_path: Path,
) -> None:
    """Decision identity is a set; the parent owns the snapshot execution order."""
    planner = _load(PLANNER_SCRIPT, "application_planner_order_independence")
    snapshot_module = _load(SNAPSHOT_SCRIPT, "application_snapshot_order_independence")
    collector = _snapshot_input()
    second = {
        **collector["request_details"][0],
        "request_id": "91000033",
        "canonical_url": "https://coconala.com/requests/91000033",
    }
    collector["request_details"].append(second)
    collector["search_sources"][0]["card_request_ids"] = ["91000032", "91000033"]
    snapshot = snapshot_module.build_envelope(collector)
    rows = [
        {
            "request_id": detail["request_id"],
            "business_class": "submit_required",
            "reason_codes": [],
            "proposal_text": "依頼内容を確認し、根拠を整理して成果物として分かりやすく納品します。" * 20,
            "price_jpy": 1000,
            "deliver_date": "2026-08-03",
        }
        for detail in reversed(snapshot["request_details"])
    ]

    assert planner.validate_decisions(snapshot, {"decisions": rows}) == []


def test_application_intent_planner_forces_provider_isolation() -> None:
    """The dedicated planner cannot receive browser-capable provider flags."""
    sys.path.insert(0, str(RUNNER_SCRIPT.parent))
    runner = _load(RUNNER_SCRIPT, "application_intent_runner_red")
    config = json.loads(RUNNER_CONFIG.read_text(encoding="utf-8"))
    planner = config["task_classes"]["application-intent-planner"]
    candidate = planner["candidates"][0]
    schema = json.loads((SCHEMAS / "application_decisions.schema.json").read_text())
    args = Namespace(
        task_class="application-intent-planner",
        schema=SCHEMAS / "application_decisions.schema.json",
        workdir=ROOT,
    )
    command = runner.command_for(
        "codex",
        "codex",
        config["providers"]["codex"],
        candidate,
        args,
        "planner prompt",
        schema,
        Path("/tmp/result.json"),
        60,
        None,
        prompt_via_stdin=True,
    )

    assert "--sandbox" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert "--dangerously-bypass-approvals-and-sandbox" not in command
    claude = runner.command_for(
        "claude-direct",
        "claude",
        config["providers"]["claude-direct"],
        planner["candidates"][1],
        args,
        "planner prompt",
        schema,
        Path("/tmp/result.json"),
        60,
        None,
        prompt_via_stdin=True,
    )
    assert claude[claude.index("--tools") + 1] == ""


def test_application_intent_planner_strips_browser_and_loopback_environment() -> None:
    """The provider child never inherits a route to the leased browser."""
    sys.path.insert(0, str(RUNNER_SCRIPT.parent))
    runner = _load(RUNNER_SCRIPT, "application_intent_runner_env_red")

    child = runner.provider_process_env(
        "claude-direct",
        {},
        environ={
            "PATH": "/usr/bin",
            "CLOAK_CDP_BASE_URL": "http://127.0.0.1:9223",
            "CDP_WS_URL": "ws://localhost:9223/devtools/page/leased",
            "BROWSER_WS": "ws://127.0.0.1:9223/devtools/page/leased",
            "UNRELATED_LOOPBACK": "http://localhost:4999/private",
        },
        task_class="application-intent-planner",
    )

    assert child == {"PATH": "/usr/bin"}


def test_parent_lease_heartbeats_and_releases_in_finally(tmp_path: Path) -> None:
    """A planner failure cannot skip release, and a long plan is heartbeated."""
    sys.path.insert(0, str(SCRIPTS))
    parent = _load(PARENT_SCRIPT, "application_parent_lease_red")
    log_path = tmp_path / "lease.log"
    lease_script = tmp_path / "lease.py"
    lease_script.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
log = Path(os.environ['APPLICATION_PARENT_TEST_LEASE_LOG'])
command = sys.argv[1]
log.open('a').write(command + '\\n')
if command == 'acquire':
    print(json.dumps({'ok': True, 'ws': 'ws://leased-target', 'token': '0' * 32, 'generation': 7}))
else:
    print(json.dumps({'ok': True}))
""",
        encoding="utf-8",
    )

    # The fake needs a stable way to receive its log path without changing the
    # production lease argv contract, so its path is injected through this env var.
    old = __import__("os").environ.get("APPLICATION_PARENT_TEST_LEASE_LOG")
    __import__("os").environ["APPLICATION_PARENT_TEST_LEASE_LOG"] = str(log_path)
    try:
        with pytest.raises(RuntimeError, match="planner failed"):
            with parent.LeaseHandle(
                lease_script=lease_script,
                task="gig-test-B2",
                heartbeat_seconds=0.01,
            ):
                time.sleep(0.05)
                raise RuntimeError("planner failed")
    finally:
        if old is None:
            __import__("os").environ.pop("APPLICATION_PARENT_TEST_LEASE_LOG", None)
        else:
            __import__("os").environ["APPLICATION_PARENT_TEST_LEASE_LOG"] = old

    commands = log_path.read_text(encoding="utf-8").splitlines()
    assert commands[0] == "acquire"
    assert "heartbeat" in commands
    assert commands[-1] == "release"


def test_parent_cdp_adapter_has_no_hidden_target_or_legacy_eligibility_gate() -> None:
    """The commit adapter owns one leased target and does not re-judge offers."""
    source = PARENT_SCRIPT.read_text(encoding="utf-8")

    cdp_adapter = source[source.index("class CdpParentEffects"):]
    assert "Target.createTarget" not in cdp_adapter
    assert "hidden_page_target" not in cdp_adapter
    assert "_load_opportunity_brief" not in cdp_adapter
    assert "application_eligibility" not in cdp_adapter


def test_proposal_feedback_reads_submit_required_exemplar(tmp_path: Path) -> None:
    feedback = _load(SCRIPTS / "proposal_feedback.py", "proposal_feedback_submit_required")
    projects_root = tmp_path / "projects"
    (projects_root / "9910000").mkdir(parents=True)
    decisions_path = tmp_path / "evidence" / "gig-pass-1" / "agent-B2" / "application-decisions.json"
    decisions_path.parent.mkdir(parents=True)
    decisions_path.write_text(json.dumps({"decisions": [{
        "request_id": "9910000",
        "business_class": "submit_required",
        "proposal_text": "synthetic submit-required proposal",
    }]}), encoding="utf-8")

    assert "synthetic submit-required proposal" in feedback.win_exemplar(
        projects_root, tmp_path / "evidence"
    )


def test_parent_form_readback_never_renavigates_after_fill() -> None:
    """Readback observes the populated form; it must not reload and erase it."""
    sys.path.insert(0, str(SCRIPTS))
    parent = _load(PARENT_SCRIPT, "application_parent_form_readback_red")
    source = PARENT_SCRIPT.read_text(encoding="utf-8")

    form_state = source[source.index("async def _form_state_async"):source.index("async def _fill_async")]
    readback = source[source.index("def readback_form"):source.index("async def _click_button_async")]
    assert "navigate: bool" in form_state
    assert "if navigate:" in form_state
    assert "_form_state_async(request_id, navigate=False)" in readback


def test_parent_accepts_only_coconala_cache_busting_query_on_offer_form() -> None:
    """Coconala appends `_t`; that must not recreate the live URL-mismatch failure."""
    sys.path.insert(0, str(SCRIPTS))
    parent = _load(PARENT_SCRIPT, "application_parent_offer_url_red")

    assert parent._is_expected_offer_form_url(
        "91000081", "https://coconala.com/offers/add/91000081?&_t=1785672985725"
    ) is True
    assert parent._is_expected_offer_form_url(
        "91000081", "https://evil.example/offers/add/91000081?_t=1"
    ) is False
    assert parent._is_expected_offer_form_url(
        "91000081", "https://coconala.com/offers/add/9999999?_t=1"
    ) is False


def test_parent_submit_records_a_verified_landing_without_retry(tmp_path: Path) -> None:
    """A verified landing needs one irreversible submit click."""
    sys.path.insert(0, str(SCRIPTS))
    parent = _load(PARENT_SCRIPT, "application_parent_multistage_submit_red")
    effects = parent.CdpParentEffects(
        ws_url="ws://127.0.0.1:9223/devtools/page/leased",
        evidence_dir=tmp_path,
        ledger_path=tmp_path / "applied.jsonl",
        pass_id="atomic-test",
    )
    responses = iter([
        ({"url": "https://coconala.com/mypage/job_matching/applied/offers", "body": "応募しました"}, b"verified"),
    ])
    calls = []

    async def fake_click(request_id: str, label: str, **_kwargs):
        calls.append((request_id, label))
        return next(responses)

    effects._click_button_async = fake_click
    effects.click_submit("91000081")

    assert calls == [("91000081", "応募する")]
    assert effects._submitted_paths["91000081"].read_bytes() == b"verified"


def test_parent_submit_does_not_retry_after_landing_is_unconfirmed(tmp_path: Path) -> None:
    """An unknown submit stays PREPARED; the same intent is never clicked again."""
    sys.path.insert(0, str(SCRIPTS))
    parent = _load(PARENT_SCRIPT, "application_parent_submit_once_red")
    effects = parent.CdpParentEffects(
        ws_url="ws://127.0.0.1:9223/devtools/page/leased",
        evidence_dir=tmp_path,
        ledger_path=tmp_path / "applied.jsonl",
        pass_id="submit-once-test",
    )
    calls = []

    async def fake_click(request_id: str, label: str, **_kwargs):
        calls.append((request_id, label))
        return (
            {"url": "https://coconala.com/offers/add/91000082", "body": "入力内容をご確認"},
            b"attempt",
        )

    effects._click_button_async = fake_click
    effects.click_submit("91000082")

    assert calls == [("91000082", "応募する")]
    assert effects._submitted_paths == {}


def test_parent_run_wires_snapshot_to_commit_inside_one_lease(tmp_path: Path) -> None:
    """The production CLI owns acquire → snapshot → decision → commit → release."""
    log_path = tmp_path / "lease.log"
    lease_script = tmp_path / "lease.py"
    lease_script.write_text(
        """#!/usr/bin/env python3
import json, os, sys
with open(os.environ['APPLICATION_PARENT_TEST_LEASE_LOG'], 'a', encoding='utf-8') as log:
    log.write(sys.argv[1] + '\\n')
if sys.argv[1] == 'acquire':
    print(json.dumps({'ok': True, 'ws': 'ws://leased-target', 'token': '0' * 32, 'generation': 7}))
else:
    print(json.dumps({'ok': True}))
""",
        encoding="utf-8",
    )
    context_path = tmp_path / "b2-context.json"
    context_path.write_text(json.dumps({
        "target_applications": 4,
        "max_applications": 7,
        "required_search_source_ids": ["single:new"],
    }), encoding="utf-8")
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps({
        "collector": _snapshot_input(),
        "decisions": {
            "decisions": [{
                "request_id": "91000032",
                "business_class": "submit_required",
                "reason_codes": [],
                "proposal_text": "依頼内容を確認し、根拠を整理して成果物として分かりやすく納品します。" * 20,
                "price_jpy": 1000,
                "deliver_date": "2026-08-03",
            }],
        },
        "effects": {"official_applied_ids": ["91000032"]},
    }, ensure_ascii=False), encoding="utf-8")
    environment = dict(__import__("os").environ, APPLICATION_PARENT_TEST_LEASE_LOG=str(log_path))
    evidence = tmp_path / "agent-B2"
    output = evidence / "parent.result.json"
    proc = subprocess.run(
        [
            sys.executable, str(PARENT_SCRIPT), "run",
            "--lease-script", str(lease_script),
            "--lease-task", "gig-test-B2-parent",
            "--context", str(context_path),
            "--pass-id", "gig-pass-atomic-test",
            "--evidence-dir", str(evidence),
            "--intent-root", str(tmp_path / "application-intents"),
            "--ledger", str(tmp_path / "applied.jsonl"),
            "--output", str(output),
            "--fixture", str(fixture_path),
        ],
        text=True,
        capture_output=True,
        env=environment,
    )

    assert proc.returncode == 0, proc.stderr
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["applications"][0]["request_id"] == "91000032"
    assert json.loads((evidence / "summary.json").read_text(encoding="utf-8"))["task_label"] == "gig-B2"
    assert log_path.read_text(encoding="utf-8").splitlines() == ["acquire", "release"]


def test_gig_pass_routes_b2_through_the_parent_only_boundary() -> None:
    """No B2 model receives a lease, raw WS route, or direct form command."""
    source = (ROOT / "gig_pass.sh").read_text(encoding="utf-8")

    assert 'run_parent_b2()' in source
    assert 'application_parent.py" run' in source
    assert 'lane_step "B2" "application-lane-agent"' not in source
    assert "open-application --ws <leased_ws>" not in source
    assert "submit-application --ws <leased_ws>" not in source


def test_parent_b2_cannot_mark_success_before_volume_and_evidence_gate() -> None:
    """A successful subprocess is not a successful revenue lane.

    The parent projection must pass the existing code-owned B2 gate before the
    cooldown/success marker is written.  This prevents zero applications with a
    still-pageable source from silently closing the lane for the wake.
    """
    source = (ROOT / "gig_pass.sh").read_text(encoding="utf-8")
    start = source.index("run_parent_b2()")
    end = source.index("\nb2_policy_skip_reason()", start)
    body = source[start:end]

    assert 'b2_result_gate.py" validate' in body
    assert 'b2_result_gate.py" continuable' in body
    assert body.index('b2_result_gate.py" validate') < body.index('mark_step_success "B2"')
    assert "return 3" in body


def test_parent_snapshot_paginates_past_already_applied_cards(monkeypatch) -> None:
    """The same-wake continuation must discover new cards, not rescan page one."""
    parent = _load(PARENT_SCRIPT, "application_parent_pagination")

    class Effects:
        def __init__(self):
            self.urls = []

        def target_lock(self):
            return contextlib.nullcontext()

        def official_ids_for_snapshot(self):
            return ["100"]

        def collect_source(self, source_id, url, remaining):
            self.urls.append(url)
            if "page=2" in url:
                return (
                    {"source_id": source_id, "url": url, "card_request_ids": ["200"],
                     "has_next": False, "exhausted": True, "screenshot_sha256": "a" * 64,
                     "dom_sha256": "b" * 64},
                    ["200"], {"screenshot_path": "p2.png", "live_dom_path": "p2.json"}, None,
                )
            return (
                {"source_id": source_id, "url": url, "card_request_ids": ["100"],
                 "has_next": True, "exhausted": False, "screenshot_sha256": "c" * 64,
                 "dom_sha256": "d" * 64},
                ["100"], {"screenshot_path": "p1.png", "live_dom_path": "p1.json"},
                "https://coconala.com/requests?page=2&sort=new&recruiting=true",
            )

        def reextract_detail(self, request_id):
            return {"request_id": request_id}

    monkeypatch.setattr(parent.snapshot_contract, "build_envelope", lambda value: value)
    effects = Effects()
    collector = parent.CdpSnapshotCollector(
        effects,
        pass_id="pass-pagination",
        objective={"required_search_source_ids": ["single:new"]},
    )
    result = collector.collect({"lease_id": "test"})

    assert effects.urls == [
        "https://coconala.com/requests?sort=new&recruiting=true",
        "https://coconala.com/requests?page=2&sort=new&recruiting=true",
    ]
    assert result["search_sources"][0]["card_request_ids"] == ["200"]
    assert result["request_details"] == [{"request_id": "200"}]
    assert result["search_sources"][0]["exhausted"] is True


def test_detail_content_hash_is_stable_across_observation_times() -> None:
    snapshot = _load(SNAPSHOT_SCRIPT, "application_snapshot_stable_hash")
    detail = _snapshot_input()["request_details"][0]
    first = snapshot._normalise_detail({**detail, "observed_at": "2026-08-02T00:00:00Z"})
    second = snapshot._normalise_detail({**detail, "observed_at": "2026-08-02T00:00:10Z"})

    assert first["observed_at"] != second["observed_at"]
    assert first["content_sha256"] == second["content_sha256"]


def test_parent_snapshot_reserves_capacity_for_every_required_source(monkeypatch) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_source_fairness")

    class Effects:
        def __init__(self):
            self.urls = []

        def target_lock(self):
            return contextlib.nullcontext()

        def official_ids_for_snapshot(self):
            return []

        def collect_source(self, source_id, url, remaining):
            self.urls.append((source_id, remaining))
            base = 1000 if source_id == "single:new" else 2000
            ids = [str(base + index) for index in range(40)][:remaining]
            return (
                {"source_id": source_id, "url": url, "card_request_ids": ids,
                 "has_next": True, "exhausted": False, "screenshot_sha256": "a" * 64,
                 "dom_sha256": "b" * 64},
                ids, {"screenshot_path": f"{source_id}.png", "live_dom_path": f"{source_id}.json"},
                None,
            )

        def reextract_detail(self, request_id):
            return {"request_id": request_id}

    monkeypatch.setattr(parent.snapshot_contract, "build_envelope", lambda value: value)
    effects = Effects()
    result = parent.CdpSnapshotCollector(
        effects,
        pass_id="pass-fairness",
        objective={"required_search_source_ids": ["single:new", "single:keyword"]},
    ).collect({"lease_id": "test"})

    assert [row[0] for row in effects.urls] == ["single:new", "single:keyword"]
    assert len(result["search_sources"]) == 2
    assert all(row["card_request_ids"] for row in result["search_sources"])
    assert len(result["request_details"]) == parent.snapshot_contract.MAX_BATCH


@pytest.mark.parametrize("checkpoint", ["after_exact_readback", "after_ledger_append"])
def test_exact_readback_crashes_recover_without_duplicate_ledger(tmp_path, checkpoint) -> None:
    parent = _load(PARENT_SCRIPT, f"application_parent_recovery_{checkpoint}")
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    store = parent.fence.IntentStore(tmp_path / "intents")
    effects = parent.FixtureEffects(snapshot, {
        "official_applied_ids": ["91000032"],
        "crash_at": checkpoint,
    })

    first = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)
    effects.crash_at = None
    second = parent.commit_decisions(snapshot, decisions, store=store, effects=effects)

    assert first[0]["status"] == f"crash_injected:{checkpoint}"
    assert second[0]["status"] == "reconciled_confirmed"
    assert len(effects.ledger) == 1
    assert store.read("91000032")["state"] == parent.fence.CONFIRMED


def test_pre_submit_navigation_timeout_retires_and_next_wake_can_submit(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_pre_submit_navigation_timeout")
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    request_id = snapshot["request_details"][0]["request_id"]
    store = parent.fence.IntentStore(tmp_path / "pre-submit-intents")

    class NavigateTimeoutEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture, *, fail_open: bool):
            super().__init__(snapshot, fixture)
            self.fail_open = fail_open
            self.submit_count = 0

        def open_form(self, request_id: str) -> None:
            if self.fail_open:
                raise parent.ParentContractError("cdp_Page.navigate_timeout_after_30s")
            super().open_form(request_id)

        def click_submit(self, request_id: str) -> None:
            self.submit_count += 1
            self.official_ids.add(request_id)
            super().click_submit(request_id)

    first_effects = NavigateTimeoutEffects(snapshot, {"official_applied_ids": []}, fail_open=True)
    first = parent.commit_decisions(snapshot, decisions, store=store, effects=first_effects)
    assert first[0]["status"] == "pre_submit_aborted:open_form:ParentContractError"
    assert first[0]["error"] == "cdp_Page.navigate_timeout_after_30s"
    assert first_effects.submit_count == 0
    assert store.read(request_id)["state"] == parent.fence.RETIRED_ABSENT
    history = list((tmp_path / "pre-submit-intents" / "recovery-history" / request_id).glob("*.json"))
    assert len(history) == 1
    assert json.loads(history[0].read_text(encoding="utf-8"))["reason"] == (
        "pre_submit_effect_not_started:open_form:ParentContractError"
    )

    second_effects = NavigateTimeoutEffects(snapshot, {"official_applied_ids": []}, fail_open=False)
    second = parent.commit_decisions(snapshot, decisions, store=store, effects=second_effects)
    assert second[0]["status"] == "confirmed"
    assert second_effects.submit_count == 1
    assert second_effects.exact_id_readback_ids == [request_id]
    assert store.read(request_id)["state"] == parent.fence.CONFIRMED


def test_missing_submit_control_retires_prepared_without_claiming_an_effect(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_submit_control_missing")
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    request_id = snapshot["request_details"][0]["request_id"]
    store = parent.fence.IntentStore(tmp_path / "submit-control-intents")

    class MissingSubmitControlEffects(parent.FixtureEffects):
        def click_submit(self, request_id: str) -> None:
            raise parent.ParentContractError("application_応募する_button_missing")

    first = parent.commit_decisions(
        snapshot,
        decisions,
        store=store,
        effects=MissingSubmitControlEffects(snapshot, {"official_applied_ids": []}),
    )

    assert first[0]["status"] == "pre_submit_aborted:click_submit_control:ParentContractError"
    assert store.read(request_id)["state"] == parent.fence.RETIRED_ABSENT

    second = parent.commit_decisions(
        snapshot,
        decisions,
        store=store,
        effects=parent.FixtureEffects(snapshot, {"official_applied_ids": [request_id]}),
    )
    assert second[0]["status"] == "confirmed"


def test_submit_exception_keeps_prepared_and_next_wake_does_not_submit(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_submit_exception_keeps_prepared")
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    request_id = snapshot["request_details"][0]["request_id"]
    store = parent.fence.IntentStore(tmp_path / "submit-exception-intents")

    class SubmitRaisesEffects(parent.FixtureEffects):
        def __init__(self, snapshot, fixture):
            super().__init__(snapshot, fixture)
            self.submit_count = 0

        def click_submit(self, request_id: str) -> None:
            self.submit_count += 1
            raise parent.ParentContractError("cdp_Page.navigate_timeout_after_30s")

    first_effects = SubmitRaisesEffects(snapshot, {"official_applied_ids": []})
    first = parent.commit_decisions(snapshot, decisions, store=store, effects=first_effects)
    assert first[0]["status"] == "submission_failed:cdp_Page.navigate_timeout_after_30s"
    assert first_effects.submit_count == 1
    assert store.read(request_id)["state"] == parent.fence.PREPARED

    second_effects = SubmitRaisesEffects(snapshot, {"official_applied_ids": []})
    second = parent.commit_decisions(snapshot, decisions, store=store, effects=second_effects)
    assert second[0]["status"] == "prepared_unconfirmed"
    assert second_effects.submit_count == 0


def test_retire_prepared_rejects_blank_reason(tmp_path: Path) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_blank_retire_reason")
    snapshot = _built_snapshot(tmp_path)
    decision = _eligible_decisions(snapshot)["decisions"][0]
    store = parent.fence.IntentStore(tmp_path / "blank-reason-intents")
    intent = parent.fence.intent_payload(
        request_id=decision["request_id"], snapshot_sha256=snapshot["snapshot_sha256"],
        proposal_text=decision["proposal_text"], price_jpy=decision["price_jpy"],
        deliver_date=decision["deliver_date"], lease_fence=snapshot["lease_fence"],
    )
    parent.fence._durable_replace(store.intent_path(decision["request_id"]), intent)
    with pytest.raises(parent.fence.IntentFenceError, match="retire_reason_invalid"):
        with store.locked(decision["request_id"]):
            store.retire_prepared_locked(
                decision["request_id"], expected_cas=intent["cas"], reason=""
            )
    assert store.read(decision["request_id"])["state"] == parent.fence.PREPARED


@pytest.mark.parametrize("preexisting_prepared", [False, True])
def test_official_readback_transport_failure_isolated_to_one_candidate(
    tmp_path: Path, preexisting_prepared: bool
) -> None:
    """A fresh or recovery readback failure must not abort the next candidate."""
    parent = _load(PARENT_SCRIPT, "application_parent_readback_failure_isolation")
    snapshot_module = _load(SNAPSHOT_SCRIPT, "application_snapshot_readback_failure_isolation")
    collector = _snapshot_input()
    second_detail = {
        **collector["request_details"][0],
        "request_id": "91000033",
        "canonical_url": "https://coconala.com/requests/91000033",
        "title": "AI 調査 2",
    }
    collector["request_details"].append(second_detail)
    collector["search_sources"][0]["card_request_ids"] = ["91000032", "91000033"]
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
                "deliver_date": "2026-08-03",
            }
            for detail in snapshot["request_details"]
        ]
    }

    class ReadbackFailureEffects(parent.FixtureEffects):
        def authoritative_exact_id_readback(self, request_id: str) -> bool:
            self.exact_id_readback_ids.append(request_id)
            if request_id == "91000032":
                raise OSError()
            return request_id in self.official_ids

    effects = ReadbackFailureEffects(snapshot, {"official_applied_ids": ["91000033"]})
    store = parent.fence.IntentStore(tmp_path / "intents")
    if preexisting_prepared:
        first = decisions["decisions"][0]
        intent = parent.fence.intent_payload(
            request_id="91000032",
            snapshot_sha256=snapshot["snapshot_sha256"],
            proposal_text=first["proposal_text"],
            price_jpy=first["price_jpy"],
            deliver_date=first["deliver_date"],
            lease_fence=snapshot["lease_fence"],
        )
        parent.fence._durable_replace(store.intent_path("91000032"), intent)
    results = parent.commit_decisions(
        snapshot,
        decisions,
        store=store,
        effects=effects,
    )

    assert results[0]["request_id"] == "91000032"
    assert results[0]["status"] == "submission_runtime_failed:OSError"
    assert results[0].get("error", "").startswith("OSError")
    assert isinstance(results[0].get("error_at"), str)
    assert results[1]["request_id"] == "91000033"
    assert results[1]["status"] == "confirmed"
    assert [row["request_id"] for row in effects.ledger] == ["91000033"]


def test_gig_pass_does_not_hold_a_legacy_base_target_alongside_parent_b2() -> None:
    """B2's parent lease is the only application target; no unused base lease leaks."""
    source = (ROOT / "gig_pass.sh").read_text(encoding="utf-8")

    assert 'cdp_context_lease.py" acquire "$GIG_LEASE"' not in source
    assert 'cdp_context_lease.py" release "$GIG_LEASE"' not in source
    assert '--lease-task "${GIG_LEASE}-B2-parent"' in source


def test_legacy_application_subcommands_fail_closed_before_any_cdp_connection() -> None:
    """A stale shell command cannot recreate the former model-owned bypass."""
    nav_script = SCRIPTS / "cdp_nav_snapshot.py"
    proc = subprocess.run(
        [sys.executable, str(nav_script), "open-application", "--ws", "ws://127.0.0.1:1"],
        text=True,
        capture_output=True,
    )
    help_proc = subprocess.run(
        [sys.executable, str(nav_script), "--help"],
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 2
    assert "parent_owned_application_boundary" in (proc.stdout + proc.stderr)
    assert "open-application" not in help_proc.stdout
    assert "submit-application" not in help_proc.stdout


def test_effect_fence_prepares_a_hash_bound_monotonic_intent(tmp_path: Path) -> None:
    """Prepared is durable before any form action and binds the exact offer payload."""
    root = tmp_path / "application-intents"
    lease = json.dumps({
        "task": "gig-pass-atomic-test-B2",
        "token": "0123456789abcdef0123456789abcdef",
        "generation": 7,
    })
    proc = subprocess.run(
        [
            sys.executable,
            str(FENCE_SCRIPT),
            "prepare",
            "--root",
            str(root),
            "--request-id",
            "91000032",
            "--snapshot-sha256",
            "c" * 64,
            "--proposal-text",
            "丁寧に対応します。",
            "--price-jpy",
            "1000",
            "--deliver-date",
            "2026-08-03",
            "--lease-fence-json",
            lease,
        ],
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads((root / "91000032.json").read_text(encoding="utf-8"))
    assert payload["state"] == "prepared"
    assert payload["request_id"] == "91000032"
    assert payload["snapshot_sha256"] == "c" * 64
    assert payload["proposal_sha256"]
    assert payload["cas"] == (
        "91000032:" + "c" * 64 + ":" + payload["proposal_sha256"] + ":1000:2026-08-03"
    )


def _built_snapshot(tmp_path: Path) -> dict:
    collector_path = tmp_path / "collector.json"
    snapshot_path = tmp_path / "snapshot.json"
    collector_path.write_text(json.dumps(_snapshot_input()), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SNAPSHOT_SCRIPT), "build", "--input", str(collector_path), "--output", str(snapshot_path)],
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def _eligible_decisions(snapshot: dict) -> dict:
    return {
        "decisions": [{
            "request_id": snapshot["request_details"][0]["request_id"],
            "business_class": "submit_required",
            "reason_codes": [],
            "proposal_text": "要件を確認し、根拠つきで調査結果を納品します。" * 20,
            "price_jpy": 1000,
            "deliver_date": "2026-08-03",
        }],
    }


def _run_parent(
    tmp_path: Path,
    snapshot: dict,
    decisions: dict,
    fixture: dict,
    *,
    intent_root: Path | None = None,
):
    snapshot_path = tmp_path / "parent-snapshot.json"
    decisions_path = tmp_path / "parent-decisions.json"
    fixture_path = tmp_path / "parent-fixture.json"
    output_path = tmp_path / "parent-output.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    decisions_path.write_text(json.dumps(decisions), encoding="utf-8")
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    root = intent_root or (tmp_path / "application-intents")
    proc = subprocess.run(
        [
            sys.executable,
            str(PARENT_SCRIPT),
            "commit-fixture",
            "--snapshot",
            str(snapshot_path),
            "--decisions",
            str(decisions_path),
            "--intent-root",
            str(root),
            "--fixture",
            str(fixture_path),
            "--output",
            str(output_path),
        ],
        text=True,
        capture_output=True,
    )
    return proc, output_path, root


def test_final_readback_unions_same_pass_turns_without_cross_pass_or_unexpected_ids(
    tmp_path: Path,
) -> None:
    parent = _load(PARENT_SCRIPT, "application_parent_final_readback_union")
    effects = parent.CdpParentEffects.__new__(parent.CdpParentEffects)
    effects.evidence_dir = tmp_path
    effects.pass_id = "pass-45"
    effects.target_lock = contextlib.nullcontext

    def fake_readback(expected_ids, path, max_pages=None):
        observed = set(expected_ids)
        if observed == {"5197622"}:
            observed.add("7777777")  # visible on the page, but not this turn's proof
        parent._atomic_json(path, {
            "source": "code_owned_cdp_readback", "url": "https://coconala.com/mypage/job_matching/applied/offers",
            "urls": ["https://coconala.com/mypage/job_matching/applied/offers"], "observed": True,
            "not_found": False, "pass_id": effects.pass_id, "expected_ids": sorted(expected_ids),
            "request_ids": sorted(observed),
        })
        return observed

    effects._official_readback = fake_readback
    effects.finalize_exact_readback({"5204226"})
    effects.finalize_exact_readback({"5197622"})
    payload = json.loads((tmp_path / "code-applied-readback.json").read_text(encoding="utf-8"))
    assert set(payload["expected_ids"]) == {"5204226", "5197622"}
    assert set(payload["request_ids"]) == {"5204226", "5197622"}

    effects.pass_id = "pass-46"
    effects.finalize_exact_readback({"8888888"})
    next_payload = json.loads((tmp_path / "code-applied-readback.json").read_text(encoding="utf-8"))
    assert set(next_payload["expected_ids"]) == {"8888888"}

    def missing_readback(expected_ids, path, max_pages=None):
        parent._atomic_json(path, {
            "source": "code_owned_cdp_readback", "url": "https://coconala.com/mypage/job_matching/applied/offers",
            "urls": ["https://coconala.com/mypage/job_matching/applied/offers"], "observed": True,
            "not_found": False, "expected_ids": sorted(expected_ids), "request_ids": [],
        })
        return set()

    effects.pass_id = "pass-47"
    effects._official_readback = missing_readback
    with pytest.raises(parent.ParentContractError, match="final_exact_readback_missing"):
        effects.finalize_exact_readback({"9999999"})
    missing_payload = json.loads((tmp_path / "code-applied-readback.json").read_text(encoding="utf-8"))
    assert set(missing_payload["expected_ids"]) == {"9999999"}
    assert missing_payload["request_ids"] == []


def _final_readback_effects(parent, tmp_path: Path, readback, recover):
    effects = parent.CdpParentEffects.__new__(parent.CdpParentEffects)
    effects.evidence_dir = tmp_path
    effects.pass_id = "final-readback-recovery"
    lock_events = []

    @contextlib.contextmanager
    def target_lock():
        lock_events.append("acquire")
        try:
            yield
        finally:
            lock_events.append("release")

    effects.target_lock = target_lock
    effects._official_readback = readback
    effects.recover_wedged_target = recover
    return effects, lock_events


@pytest.mark.parametrize("mode", ["transport_success", "transport_fail", "business_error"])
def test_final_exact_readback_recovery_is_bounded(tmp_path: Path, mode: str) -> None:
    parent = _load(PARENT_SCRIPT, f"application_parent_final_readback_{mode}")
    state = {"reads": 0, "recoveries": 0}

    def readback(expected_ids, path, max_pages=None):
        state["reads"] += 1
        if mode == "business_error":
            raise parent.ParentContractError("official_readback_route_invalid")
        if mode == "transport_fail" or state["reads"] == 1:
            raise parent.websockets.exceptions.ConnectionClosedError(None, None)
        parent._atomic_json(path, {"expected_ids": sorted(expected_ids), "request_ids": sorted(expected_ids)})
        return set(expected_ids)

    def recover():
        state["recoveries"] += 1
        return True

    effects, lock_events = _final_readback_effects(parent, tmp_path, readback, recover)
    if mode == "transport_success":
        effects.finalize_exact_readback({"123"})
    else:
        error = (
            parent.ParentContractError
            if mode == "business_error"
            else parent.websockets.exceptions.ConnectionClosedError
        )
        with pytest.raises(error):
            effects.finalize_exact_readback({"123"})

    assert state["reads"] == (1 if mode == "business_error" else 2)
    assert state["recoveries"] == (0 if mode == "business_error" else 1)
    assert lock_events == ["acquire", "release"]


def test_parent_rejects_stale_snapshot_before_form_open_with_zero_clicks(tmp_path: Path) -> None:
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    changed_detail = dict(_snapshot_input()["request_details"][0])
    changed_detail["visible_text"] = "募集内容が変更されました"
    proc, output_path, root = _run_parent(
        tmp_path,
        snapshot,
        decisions,
        {"fresh_details": {"91000032": changed_detail}},
    )

    assert proc.returncode == 0, proc.stderr
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["results"][0]["status"] == "stale_snapshot"
    assert output["click_count"] == 0
    assert output["open_count"] == 0
    assert not (root / "91000032.json").exists()


@pytest.mark.parametrize(
    ("checkpoint", "expected_clicks", "expected_phase"),
    [
        ("after_prepare", 0, "pre_effect"),
        ("after_open", 0, "pre_effect"),
        ("after_fill_readback", 0, "pre_effect"),
        ("after_confirm_click", 1, "pre_effect"),
        ("after_irreversible_attempt_marker", 1, "irreversible_attempt_started"),
        ("after_submit_click", 2, "irreversible_attempt_started"),
    ],
)
def test_parent_crash_injection_at_every_click_boundary_leaves_prepared_and_never_blind_retries(
    tmp_path: Path,
    checkpoint: str,
    expected_clicks: int,
    expected_phase: str,
) -> None:
    snapshot = _built_snapshot(tmp_path)
    proc, output_path, root = _run_parent(
        tmp_path,
        snapshot,
        _eligible_decisions(snapshot),
        {"crash_at": checkpoint},
    )

    assert proc.returncode == 0, proc.stderr
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["results"][0]["status"] == f"crash_injected:{checkpoint}"
    assert output["click_count"] == expected_clicks
    intent = json.loads((root / "91000032.json").read_text(encoding="utf-8"))
    assert intent["state"] == "prepared"
    assert intent["effect_phase"] == expected_phase


@pytest.mark.parametrize(
    "checkpoint",
    ["after_prepare", "after_open", "after_fill_readback", "after_confirm_click"],
)
def test_parent_pre_effect_reentry_retries_after_exact_id_absence(
    tmp_path: Path, checkpoint: str
) -> None:
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    first, _, root = _run_parent(tmp_path, snapshot, decisions, {"crash_at": checkpoint})
    assert first.returncode == 0, first.stderr
    proc, output_path, _ = _run_parent(
        tmp_path,
        snapshot,
        decisions,
        {"official_applied_ids": []},
        intent_root=root,
    )

    assert proc.returncode == 0, proc.stderr
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["results"][0]["status"] == "awaiting_exact_id_readback"
    assert output["click_count"] == 2
    assert output["exact_id_readback_ids"] == ["91000032", "91000032"]


@pytest.mark.parametrize(
    "checkpoint", ["after_irreversible_attempt_marker", "after_submit_click"]
)
def test_parent_effect_started_reentry_never_blind_retries(
    tmp_path: Path, checkpoint: str
) -> None:
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    first, _, root = _run_parent(tmp_path, snapshot, decisions, {"crash_at": checkpoint})
    assert first.returncode == 0, first.stderr
    proc, output_path, _ = _run_parent(
        tmp_path, snapshot, decisions, {"official_applied_ids": []}, intent_root=root
    )

    assert proc.returncode == 0, proc.stderr
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["results"][0]["status"] == "prepared_unconfirmed"
    assert output["click_count"] == 0
    assert output["exact_id_readback_ids"] == ["91000032"]


def test_parent_confirmed_reentry_never_clicks(tmp_path: Path) -> None:
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    lease = json.dumps(snapshot["lease_fence"])
    prepared = subprocess.run(
        [
            sys.executable, str(FENCE_SCRIPT), "prepare", "--root", str(tmp_path / "application-intents"),
            "--request-id", "91000032", "--snapshot-sha256", snapshot["snapshot_sha256"],
            "--proposal-text", decisions["decisions"][0]["proposal_text"], "--price-jpy", "1000",
            "--deliver-date", "2026-08-03", "--lease-fence-json", lease,
        ],
        text=True,
        capture_output=True,
    )
    assert prepared.returncode == 0, prepared.stderr
    intent = json.loads((tmp_path / "application-intents" / "91000032.json").read_text(encoding="utf-8"))
    confirmed = subprocess.run(
        [
            sys.executable, str(FENCE_SCRIPT), "confirm", "--root", str(tmp_path / "application-intents"),
            "--request-id", "91000032", "--expected-cas", intent["cas"],
        ],
        text=True,
        capture_output=True,
    )
    assert confirmed.returncode == 0, confirmed.stderr
    proc, output_path, _ = _run_parent(
        tmp_path,
        snapshot,
        decisions,
        {"official_applied_ids": ["91000032"]},
        intent_root=tmp_path / "application-intents",
    )

    assert proc.returncode == 0, proc.stderr
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["results"][0]["status"] == "reconciled_confirmed"
    assert output["click_count"] == 0
    assert len(output["ledger"]) == 1


def test_parent_confirms_only_the_exact_id_from_official_history(tmp_path: Path) -> None:
    snapshot = _built_snapshot(tmp_path)
    decisions = _eligible_decisions(snapshot)
    proc, output_path, root = _run_parent(
        tmp_path,
        snapshot,
        decisions,
        {"generic_success": True, "official_applied_ids": ["9999999"]},
    )

    assert proc.returncode == 0, proc.stderr
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["results"][0]["status"] == "awaiting_exact_id_readback"
    assert output["ledger"] == []
    assert json.loads((root / "91000032.json").read_text(encoding="utf-8"))["state"] == "prepared"


def test_parent_uses_one_target_lock_and_projects_confirmed_rows_to_legacy_b2(tmp_path: Path) -> None:
    snapshot = _built_snapshot(tmp_path)
    proc, output_path, _ = _run_parent(
        tmp_path,
        snapshot,
        _eligible_decisions(snapshot),
        {"official_applied_ids": ["91000032"]},
    )

    assert proc.returncode == 0, proc.stderr
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["results"][0]["status"] == "confirmed"
    assert output["target_lock_acquires"] == 1
    assert output["target_lock_releases"] == 1
    assert output["second_target_count"] == 0
    import jsonschema

    jsonschema.Draft202012Validator(
        json.loads((SCHEMAS / "gig_b2_result.schema.json").read_text(encoding="utf-8"))
    ).validate(output["legacy_b2"])
    assert output["legacy_b2"]["applications"] == [{
        "request_id": "91000032",
        "bucket": "single",
        "category": "リサーチ",
        "title": "AI 調査",
        "price_jpy": 1000,
        "deliver_date": "2026-08-03",
        "url": "https://coconala.com/requests/91000032",
        "compensation_type": None,
        "weekly_days": None,
        "weekly_hours_min": None,
        "weekly_hours_max": None,
    }]
