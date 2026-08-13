import copy
import hashlib
import io
import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import jsonschema


REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_LOOP_PATH = REPO_ROOT / "skills/earn/lancers/scripts/application_loop.py"


def _load_deployed_loop():
    spec = importlib.util.spec_from_file_location(
        "test_canonical_lancers_application_loop", CANONICAL_LOOP_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("canonical_application_loop_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _opportunity(project_id: str, *, budget_min_minor: int = 100000) -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_type": "lancers_public_opportunity",
        "platform": "lancers",
        "external_id": project_id,
        "title": "月次SNS運用の外部委託",
        "description": (
            "依頼主の業種: 情報通信業\n"
            "依頼概要: SNS運用を毎月、外部委託でお願いしたいです。"
        ),
        "url": f"https://www.lancers.jp/work/detail/{project_id}",
        "category": "システム開発・運用",
        "budget_type": "fixed",
        "budget_min_minor": budget_min_minor,
        "budget_max_minor": 300000,
        "currency": "JPY",
        "buyer_external_id": f"buyer-{project_id}",
        "observed_at": "2026-08-13T12:00:00+00:00",
    }


def _proposal_text(price: int = 250000) -> str:
    return (
        "公開された要件を踏まえ、業務改善のためのWebシステムを整備し、少人数の担当者がSNSを兼務する状況でも作業が滞らない状態を目指します。"
        "最初の30日で現状整理、画面設計、試作、動作確認、引き継ぎ資料を納品します。"
        f"対象チャネルは2つ、月8本、修正は2回までとし、価格は{price}円、納期は2026-08-20です。"
        "毎月の運用支援と改善提案を継続範囲に含めます。現在の優先チャネルはこの2つでよろしいでしょうか？"
    )


def _qualification(
    *,
    commercial_buyer_evidence: str = "依頼主の業種: 情報通信業",
    ongoing_sns_outsourcing_evidence: str = "SNS運用を毎月、外部委託でお願いしたいです。",
    expected_platform_fee_jpy: int = 50000,
    expected_ai_cost_jpy: int = 2000,
    expected_subcontractor_cost_jpy: int = 0,
    expected_revision_refund_allowance_jpy: int = 7000,
) -> dict[str, object]:
    return {
        "commercial_buyer_evidence": commercial_buyer_evidence,
        "ongoing_sns_outsourcing_evidence": ongoing_sns_outsourcing_evidence,
        "expected_platform_fee_jpy": expected_platform_fee_jpy,
        "expected_ai_cost_jpy": expected_ai_cost_jpy,
        "expected_subcontractor_cost_jpy": expected_subcontractor_cost_jpy,
        "expected_revision_refund_allowance_jpy": expected_revision_refund_allowance_jpy,
        "cost_source_version": "lancers-g1-conservative-v1",
    }


def _eligible_decision(
    project_id: str = "6000001",
    *,
    price_jpy: int = 250000,
    qualification: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "request_id": project_id,
        "eligibility": "eligible",
        "reason_codes": ["public_scope_fit"],
        "proposal_text": _proposal_text(price_jpy),
        "price_jpy": price_jpy,
        "deliver_date": "2026-08-20",
        "qualification": qualification or _qualification(),
    }


def _ineligible_decision(project_id: str) -> dict[str, object]:
    return {
        "request_id": project_id,
        "eligibility": "ineligible",
        "reason_codes": ["claimed_project"],
        "proposal_text": None,
        "price_jpy": None,
        "deliver_date": None,
        "qualification": None,
    }


class _FakeLocator:
    def __init__(self, *, text: str = "", attributes: dict[str, str] | None = None, children: dict[str, object] | None = None):
        self._text = text
        self._attributes = attributes or {}
        self._children = children or {}

    def count(self) -> int:
        return 1

    def nth(self, index: int) -> "_FakeLocator":
        if index != 0:
            raise AssertionError(index)
        return self

    def inner_text(self) -> str:
        return self._text

    def get_attribute(self, name: str) -> str | None:
        return self._attributes.get(name)

    def locator(self, selector: str) -> "_FakeLocator":
        return self._children[selector]  # type: ignore[return-value]


class _FakeProposalPage:
    def __init__(self, *, project_id: str, heading_text: str, project_href: str | None = None):
        proposal_id = "27808988"
        heading_href = f"/work/proposal/{proposal_id}"
        card_heading = _FakeLocator(
            text=heading_text,
            attributes={"href": heading_href},
        )
        card = _FakeLocator(
            attributes={"id": f"js-list-item-{proposal_id}"},
            children={"a.p-simpleProposal-list__heading-title": card_heading},
        )
        self.url = "https://www.lancers.jp/mypage/proposals"
        self._locators = {
            f'a[href="/work/detail/{project_id}"]': _FakeLocator(
                attributes={"href": project_href or f"/work/detail/{project_id}"},
            ),
            f'a[href^="/work/proposals/{project_id}/"][href$="?ref=mypage_control"]': _FakeLocator(
                text="提案をみる",
                attributes={
                    "href": f"/work/proposals/{project_id}/keiodaisuke?ref=mypage_control"
                },
            ),
            'meta[property="og:url"]': _FakeLocator(
                attributes={
                    "content": f"https://www.lancers.jp/work/proposals/{project_id}/keiodaisuke"
                },
            ),
            "a.p-simpleProposal-list__heading-title": _FakeLocator(
                text=heading_text,
                attributes={"href": heading_href},
            ),
            f"div#js-list-item-{proposal_id}": card,
        }

    def locator(self, selector: str) -> _FakeLocator:
        return self._locators[selector]

    def goto(self, url: str, **_kwargs: object) -> None:
        self.url = url


class _FakeBrowser:
    def __init__(self, page: _FakeProposalPage):
        self.contexts = [self]
        self._page = page

    def new_page(self) -> _FakeProposalPage:
        return self._page


class ApplicationLoopHolTests(unittest.TestCase):
    def test_default_proposal_reader_accepts_mutable_display_name(self):
        application_loop = _load_deployed_loop()
        project_id = "5585503"
        page = _FakeProposalPage(
            project_id=project_id,
            heading_text="SNS・AI業務設計室 さんの提案",
        )

        self.assertEqual(
            application_loop.application_tick._default_proposal_reader(page, project_id),
            {"proposal_id": "27808988", "project_id": project_id},
        )

    def test_default_proposal_reader_rejects_malformed_heading(self):
        application_loop = _load_deployed_loop()
        project_id = "5585503"
        page = _FakeProposalPage(project_id=project_id, heading_text="提案")

        self.assertEqual(
            application_loop.application_tick._default_proposal_reader(page, project_id),
            {},
        )

    def test_run_live_tick_reconciles_target_pending_descriptor_only(self):
        application_loop = _load_deployed_loop()
        application_tick = application_loop.application_tick
        other_project_id = "5585496"
        target_project_id = "5586112"
        markers = {
            project_id: hashlib.sha256(
                f"lancers:application:{project_id}".encode()
            ).hexdigest()
            for project_id in (other_project_id, target_project_id)
        }
        state = {
            "fingerprints": list(markers.values()),
            "pending": {
                markers[other_project_id]: {
                    "proposal_id": "27800001",
                    "content_sha256": hashlib.sha256(b"other").hexdigest(),
                    "amount_minor": 110000,
                    "delivery_due_on": "2026-09-01",
                    "project_id": other_project_id,
                },
                markers[target_project_id]: {
                    "proposal_id": None,
                    "content_sha256": hashlib.sha256(b"target").hexdigest(),
                    "amount_minor": 98000,
                    "delivery_due_on": "2026-09-10",
                    "project_id": target_project_id,
                },
            },
        }
        receipts = []
        page = _FakeProposalPage(project_id=target_project_id, heading_text="unused")
        browser = _FakeBrowser(page)
        remaining_pending = None

        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "application.json"
            state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
            with patch.object(
                application_tick,
                "_production_account_ready",
                return_value=True,
            ), patch.object(
                application_tick,
                "read_pending_descriptor",
                return_value={
                    "project_id": other_project_id,
                    "amount_minor": 110000,
                    "delivery_due_on": "2026-09-01",
                },
            ), patch.object(
                application_tick,
                "read_pending_descriptors",
                create=True,
                return_value=[
                    {
                        "project_id": other_project_id,
                        "amount_minor": 110000,
                        "delivery_due_on": "2026-09-01",
                    },
                    {
                        "project_id": target_project_id,
                        "amount_minor": 98000,
                        "delivery_due_on": "2026-09-10",
                    },
                ],
            ):
                result = application_tick.run_live_tick(
                    project_id=target_project_id,
                    proposal_text="pending reconciliation",
                    proposed_amount_minor=98000,
                    delivery_due_on="2026-09-10",
                    state_path=state_path,
                    browser_factory=lambda _url: browser,
                    ledger_writer=receipts.append,
                    now=lambda: "2026-08-13T12:00:00Z",
                    submitter_override=lambda *_args: self.fail("pending_submit"),
                    readback_override=lambda _proposal_id, project_id: {
                        "proposal_id": "27808988",
                        "project_id": project_id,
                    },
                )
            remaining_pending = json.loads(state_path.read_text(encoding="utf-8"))["pending"]

        self.assertTrue(result.ok)
        self.assertFalse(result.submitted)
        self.assertTrue(result.application_verified)
        self.assertEqual(result.project_id, target_project_id)
        self.assertEqual(result.provider_proposal_id, "27808988")
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["opportunity_external_id"], target_project_id)
        self.assertEqual(remaining_pending.keys(), {markers[other_project_id]})

    def test_default_discovery_query_targets_g1_revenue_lane(self):
        application_loop = _load_deployed_loop()
        queries = []

        def discoverer(**kwargs):
            queries.append(kwargs["query"])
            return {"ok": True, "error": None, "opportunities": []}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            application_loop.run_loop(
                state_path=root / "application.json",
                evidence_root=root / "evidence",
                discoverer=discoverer,
            )
            application_loop.run_loop(
                state_path=root / "application.json",
                evidence_root=root / "evidence",
                discoverer=discoverer,
                query="explicit-query",
            )

        self.assertEqual(queries, ["SNS運用", "explicit-query"])

    def test_invoke_planner_uses_canonical_agent_runner_arguments(self):
        application_loop = _load_deployed_loop()
        calls = []

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            return type("Completed", (), {"returncode": 0})()

        with tempfile.TemporaryDirectory() as directory:
            evidence = Path(directory) / "evidence"
            evidence.mkdir()
            result_path = evidence / "result.json"
            result_path.write_text(json.dumps({"decisions": []}), encoding="utf-8")
            (evidence / "summary.json").write_text(
                json.dumps({"status": "success", "result_path": str(result_path)}),
                encoding="utf-8",
            )
            with patch.object(
                application_loop.subprocess, "run", side_effect=fake_run
            ):
                result = application_loop.invoke_planner("planner prompt", evidence)

        command = calls[0][0]
        self.assertNotIn("--timeout-seconds", command)
        for argument in (
            "--task-class",
            "application-intent-planner",
            "--prompt-stdin",
            "--schema",
            str(application_loop.PLANNER_SCHEMA),
            "--evidence-dir",
            str(evidence),
            "--task-label",
            "lancers-application-intent",
            "--loop",
            "lancers-application",
            "--workdir",
            str(application_loop.SKILLS_ROOT.parent),
        ):
            self.assertIn(argument, command)
        self.assertEqual(result, {"decisions": []})

    def test_normal_tick_submits_only_first_ranked_eligible_project(self):
        application_loop = _load_deployed_loop()
        submitter_project_ids = []
        opportunities = [_opportunity("6000001"), _opportunity("6000002")]

        def discoverer(**kwargs):
            return {"ok": True, "error": None, "opportunities": opportunities}

        def planner(prompt, evidence):
            return {
                "decisions": [
                    _eligible_decision("6000001"),
                    _eligible_decision("6000002"),
                ]
            }

        def submitter(**kwargs):
            submitter_project_ids.append(kwargs["project_id"])
            return {
                "ok": True,
                "submitted": True,
                "application_verified": True,
                "project_id": kwargs["project_id"],
                "provider_proposal_id": f"proposal-{kwargs['project_id']}",
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = application_loop.run_loop(
                state_path=root / "application.json",
                evidence_root=root / "evidence",
                discoverer=discoverer,
                planner=planner,
                submitter=submitter,
                clock=lambda: datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
            )

        self.assertEqual(submitter_project_ids, ["6000001"])
        self.assertEqual(result["eligible_count"], 2)
        self.assertEqual(result["verified_count"], 1)

    def test_reconcile_only_reconciles_every_pending_application_without_discovery_or_submit(self):
        application_loop = _load_deployed_loop()
        project_ids = ["5585496", "5586112"]
        state = {"fingerprints": [], "pending": {}}
        for project_id in project_ids:
            marker = hashlib.sha256(
                f"lancers:application:{project_id}".encode()
            ).hexdigest()
            state["fingerprints"].append(marker)
            state["pending"][marker] = {
                "proposal_id": None,
                "content_sha256": hashlib.sha256(
                    f"proposal:{project_id}".encode()
                ).hexdigest(),
                "amount_minor": 250000,
                "delivery_due_on": "2026-09-10",
                "project_id": project_id,
            }

        called_project_ids = []

        def run_live_tick(**kwargs):
            called_project_ids.append(kwargs["project_id"])
            return {
                "ok": False,
                "error": "submission_uncertain",
                "project_id": kwargs["project_id"],
            }

        def forbidden(*_args, **_kwargs):
            raise AssertionError("discovery_or_submit_called")

        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "application.json"
            state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
            original_state = copy.deepcopy(json.loads(state_path.read_text()))
            with patch.object(
                application_loop.application_tick,
                "run_live_tick",
                side_effect=run_live_tick,
            ), patch.object(
                application_loop.status, "run_discovery", side_effect=forbidden
            ), patch.object(
                application_loop, "_plan_and_submit", side_effect=forbidden
            ), patch.object(application_loop, "_submit", side_effect=forbidden):
                result = application_loop.run_reconcile_only(state_path)

                self.assertEqual(called_project_ids, project_ids)
                self.assertEqual(result["reconciled_project_ids"], project_ids)
                self.assertEqual(result["verified_project_ids"], [])
                self.assertEqual(result["unresolved_project_ids"], project_ids)
                self.assertFalse(result["submitted"])
                self.assertEqual(json.loads(state_path.read_text()), original_state)

                called_project_ids.clear()
                self.assertEqual(
                    application_loop.main(
                        ["--json", "--reconcile-only", "--state-path", str(state_path)],
                        stdout=io.StringIO(),
                    ),
                    1,
                )
                self.assertEqual(called_project_ids, project_ids)

    def test_uncertain_pending_is_quarantined_without_blocking_new_verified_application(self):
        application_loop = _load_deployed_loop()
        discovery_calls = []
        planner_calls = []
        submitter_project_ids = []
        opportunities = [_opportunity("5585496"), _opportunity("6000001")]
        proposal_text = (
            "公開された要件を踏まえ、業務改善のためのWebシステムを整備し、少人数の担当者がSNSを兼務する状況でも作業が滞らない状態を目指します。"
            "最初の30日で現状整理、画面設計、試作、動作確認、引き継ぎ資料を納品します。"
            "対象チャネルは2つ、月8本、修正は2回までとし、価格は250000円、納期は2026-08-20です。"
            "毎月の運用支援と改善提案を継続範囲に含めます。現在の優先チャネルはこの2つでよろしいでしょうか？"
        )

        def discoverer(**kwargs):
            discovery_calls.append(kwargs)
            return {"ok": True, "error": None, "opportunities": opportunities}

        def planner(prompt, evidence):
            planner_calls.append((prompt, evidence))
            return {
                "decisions": [
                    {
                        "request_id": "6000001",
                        "eligibility": "eligible",
                        "reason_codes": ["public_scope_fit"],
                        "proposal_text": proposal_text,
                        "price_jpy": 250000,
                        "deliver_date": "2026-08-20",
                        "qualification": {
                            "commercial_buyer_evidence": "依頼主の業種: 情報通信業",
                            "ongoing_sns_outsourcing_evidence": "SNS運用を毎月、外部委託でお願いしたいです。",
                            "expected_platform_fee_jpy": 50000,
                            "expected_ai_cost_jpy": 2000,
                            "expected_subcontractor_cost_jpy": 0,
                            "expected_revision_refund_allowance_jpy": 7000,
                            "cost_source_version": "lancers-g1-conservative-v1",
                        },
                    }
                ]
            }

        def submitter(**kwargs):
            submitter_project_ids.append(kwargs["project_id"])
            return {
                "ok": True,
                "submitted": True,
                "application_verified": True,
                "project_id": kwargs["project_id"],
                "provider_proposal_id": "9000001",
            }

        pending = {
            "project_id": "5585496",
            "amount_minor": 250000,
            "delivery_due_on": "2026-09-10",
            "proposal_id": None,
        }
        pending_result = application_loop.ApplicationLoopResult(
            False,
            error="submission_uncertain",
            project_id="5585496",
            unresolved_project_id="5585496",
        )
        fixed_clock = lambda: datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = None
            with patch.object(
                application_loop.application_tick,
                "read_pending_descriptor",
                return_value=pending,
            ), patch.object(
                application_loop,
                "_reconcile_pending",
                return_value=pending_result,
            ), patch.object(
                application_loop.application_tick,
                "state_has_claim",
                side_effect=lambda _state_path, project_id: project_id == "5585496",
            ):
                result = application_loop.run_loop(
                    state_path=root / "application.json",
                    evidence_root=root / "evidence",
                    discoverer=discoverer,
                    planner=planner,
                    submitter=submitter,
                    clock=fixed_clock,
                )

        self.assertEqual(len(discovery_calls), 1)
        self.assertEqual(submitter_project_ids, ["6000001"])
        self.assertNotIn("5585496", submitter_project_ids)
        self.assertEqual(len(planner_calls), 1)
        snapshot = json.loads(planner_calls[0][0].split("SNAPSHOT:\n", 1)[1])
        self.assertEqual(
            [row["external_id"] for row in snapshot["opportunities"]], ["6000001"]
        )
        self.assertEqual(result["verified_count"], 1)
        self.assertEqual(result["verified_project_ids"], ["6000001"])
        self.assertEqual(result["verified_provider_proposal_ids"], ["9000001"])
        self.assertEqual(result["unresolved_project_id"], "5585496")

    def test_rejects_projected_margin_below_seventy_percent_before_submit(self):
        application_loop = _load_deployed_loop()
        submitter_project_ids = []
        opportunities = [_opportunity("6000001", budget_min_minor=98000)]
        proposal_text = (
            "公開された要件を踏まえ、業務改善のためのWebシステムを整備し、少人数の担当者がSNSを兼務する状況でも作業が滞らない状態を目指します。"
            "最初の30日で現状整理、画面設計、試作、動作確認、引き継ぎ資料を納品します。"
            "対象チャネルは2つ、月8本、修正は2回までとし、価格は98000円、納期は2026-08-20です。"
            "毎月の運用支援と改善提案を継続範囲に含めます。現在の優先チャネルはこの2つでよろしいでしょうか？"
        )

        def discoverer(**kwargs):
            return {"ok": True, "error": None, "opportunities": opportunities}

        def planner(prompt, evidence):
            return {
                "decisions": [
                    {
                        "request_id": "6000001",
                        "eligibility": "eligible",
                        "reason_codes": ["public_scope_fit"],
                        "proposal_text": proposal_text,
                        "price_jpy": 98000,
                        "deliver_date": "2026-08-20",
                        "qualification": {
                            "commercial_buyer_evidence": "依頼主の業種: 情報通信業",
                            "ongoing_sns_outsourcing_evidence": "SNS運用を毎月、外部委託でお願いしたいです。",
                            "expected_platform_fee_jpy": 19600,
                            "expected_ai_cost_jpy": 2000,
                            "expected_subcontractor_cost_jpy": 0,
                            "expected_revision_refund_allowance_jpy": 7801,
                            "cost_source_version": "lancers-g1-conservative-v1",
                        },
                    }
                ]
            }

        def submitter(**kwargs):
            submitter_project_ids.append(kwargs["project_id"])
            return {
                "ok": True,
                "submitted": True,
                "application_verified": True,
                "project_id": kwargs["project_id"],
                "provider_proposal_id": "9000002",
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(
                application_loop.application_tick,
                "read_pending_descriptor",
                return_value=None,
            ), patch.object(
                application_loop.application_tick,
                "state_has_claim",
                return_value=False,
            ):
                result = application_loop.run_loop(
                    state_path=root / "application.json",
                    evidence_root=root / "evidence",
                    discoverer=discoverer,
                    planner=planner,
                    submitter=submitter,
                    clock=lambda: datetime(
                        2026, 8, 13, 12, 0, tzinfo=timezone.utc
                    ),
                )

        self.assertEqual(result.get("error"), "planner_failed")
        self.assertEqual(submitter_project_ids, [])

    def test_rejects_semantically_empty_public_evidence_before_submit(self):
        application_loop = _load_deployed_loop()
        submitter_project_ids = []
        opportunities = [_opportunity("6000001")]

        def discoverer(**kwargs):
            return {"ok": True, "error": None, "opportunities": opportunities}

        def planner(prompt, evidence):
            return {
                "decisions": [
                    _eligible_decision(
                        qualification=_qualification(
                            commercial_buyer_evidence="依頼主の業種: 情報通信業",
                            ongoing_sns_outsourcing_evidence="SNS運用",
                        )
                    )
                ]
            }

        def submitter(**kwargs):
            submitter_project_ids.append(kwargs["project_id"])
            return {
                "ok": True,
                "submitted": True,
                "application_verified": True,
                "project_id": kwargs["project_id"],
                "provider_proposal_id": "9000003",
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(
                application_loop.application_tick,
                "read_pending_descriptor",
                return_value=None,
            ), patch.object(
                application_loop.application_tick,
                "state_has_claim",
                return_value=False,
            ):
                result = application_loop.run_loop(
                    state_path=root / "application.json",
                    evidence_root=root / "evidence",
                    discoverer=discoverer,
                    planner=planner,
                    submitter=submitter,
                    clock=lambda: datetime(
                        2026, 8, 13, 12, 0, tzinfo=timezone.utc
                    ),
                )

        self.assertEqual(result.get("error"), "planner_failed")
        self.assertEqual(submitter_project_ids, [])

    def test_claimed_pending_projects_are_excluded_before_planning_even_over_batch_limit(self):
        application_loop = _load_deployed_loop()
        planner_snapshots = []
        submitter_project_ids = []
        opportunities = [
            _opportunity("5585496"),
            _opportunity("5586112"),
            _opportunity("6000001"),
        ] + [_opportunity(str(7000000 + index)) for index in range(18)]

        def discoverer(**kwargs):
            return {"ok": True, "error": None, "opportunities": opportunities}

        def planner(prompt, evidence):
            snapshot = json.loads(prompt.split("SNAPSHOT:\n", 1)[1])
            planner_snapshots.append(snapshot)
            return {
                "decisions": [
                    _eligible_decision(row["external_id"])
                    if row["external_id"] == "6000001"
                    else _ineligible_decision(row["external_id"])
                    for row in snapshot["opportunities"]
                ]
            }

        def submitter(**kwargs):
            submitter_project_ids.append(kwargs["project_id"])
            return {
                "ok": True,
                "submitted": True,
                "application_verified": True,
                "project_id": kwargs["project_id"],
                "provider_proposal_id": "9000004",
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(
                application_loop.application_tick,
                "read_pending_descriptor",
                return_value=None,
            ), patch.object(
                application_loop.application_tick,
                "state_has_claim",
                side_effect=lambda _state_path, project_id: project_id
                in {"5585496", "5586112"},
            ):
                result = application_loop.run_loop(
                    state_path=root / "application.json",
                    evidence_root=root / "evidence",
                    discoverer=discoverer,
                    planner=planner,
                    submitter=submitter,
                    clock=lambda: datetime(
                        2026, 8, 13, 12, 0, tzinfo=timezone.utc
                    ),
                )

        self.assertNotIn("error", result)
        planned_project_ids = [
            row["external_id"] for row in planner_snapshots[0]["opportunities"]
        ]
        self.assertNotIn("5585496", planned_project_ids)
        self.assertNotIn("5586112", planned_project_ids)
        self.assertIn("6000001", planned_project_ids)
        self.assertEqual(submitter_project_ids, ["6000001"])
        self.assertEqual(result["verified_project_ids"], ["6000001"])

    def test_schema_and_runtime_share_eligibility_contract_matrix(self):
        application_loop = _load_deployed_loop()
        schema = json.loads(
            Path(application_loop.SCHEMA_PATH).read_text(encoding="utf-8")
        )
        validator = jsonschema.Draft202012Validator(schema)
        row = _opportunity("6000001", budget_min_minor=98000)
        valid_eligible = _eligible_decision(
            price_jpy=98000,
            qualification=_qualification(
                expected_platform_fee_jpy=19600,
                expected_revision_refund_allowance_jpy=7000,
            ),
        )
        valid_ineligible = _ineligible_decision("6000001")
        eligible_without_qualification = copy.deepcopy(valid_eligible)
        eligible_without_qualification["qualification"] = None
        eligible_with_low_price = copy.deepcopy(valid_eligible)
        eligible_with_low_price["price_jpy"] = 1
        eligible_with_old_staff_contract = copy.deepcopy(valid_eligible)
        qualification = eligible_with_old_staff_contract["qualification"]
        assert isinstance(qualification, dict)
        qualification.pop("commercial_buyer_evidence")
        qualification.pop("ongoing_sns_outsourcing_evidence")
        qualification["small_b2b_evidence"] = "小規模法人向けの業務改善"
        qualification["sns_staff_evidence"] = "少人数の担当者がSNSを兼務"
        ineligible_with_qualification = copy.deepcopy(valid_ineligible)
        ineligible_with_qualification["qualification"] = _qualification()
        cases = (
            ("eligible_valid", valid_eligible, True, []),
            ("eligible_without_qualification", eligible_without_qualification, False, ["planner_failed"]),
            ("eligible_with_low_price", eligible_with_low_price, False, ["planner_failed"]),
            ("eligible_with_old_staff_contract", eligible_with_old_staff_contract, False, ["planner_failed"]),
            ("ineligible_valid", valid_ineligible, True, []),
            ("ineligible_with_qualification", ineligible_with_qualification, False, ["planner_failed"]),
        )

        for name, decision, schema_expected, runtime_expected in cases:
            payload = {"decisions": [decision]}
            schema_valid = validator.is_valid(payload)
            self.assertEqual(schema_valid, schema_expected, name)
            self.assertEqual(
                application_loop.validate_decisions(
                    [row], payload, datetime(2026, 8, 13, tzinfo=timezone.utc)
                ),
                runtime_expected,
                name,
            )

    def test_commercial_ongoing_contract_rejects_staff_proxy_and_one_off_before_submit(self):
        application_loop = _load_deployed_loop()
        staff_proxy = _opportunity("6000001")
        staff_proxy["description"] = "依頼主の業種: 情報通信業\n依頼概要: 少人数の担当者がSNSを兼務しています。"
        one_off = _opportunity("6000001")
        one_off["description"] = "依頼主の業種: 情報通信業\n依頼概要: SNS投稿を1回お願いします。"
        cases = (
            ("commercial_ongoing", _opportunity("6000001"), _eligible_decision(), True),
            ("staff_proxy", staff_proxy, _eligible_decision(qualification=_qualification(ongoing_sns_outsourcing_evidence="少人数の担当者がSNSを兼務しています。")), False),
            ("one_off", one_off, _eligible_decision(qualification=_qualification(ongoing_sns_outsourcing_evidence="SNS投稿を1回お願いします。")), False),
        )

        for name, opportunity, decision, accepted in cases:
            submitted = []

            def discoverer(**_kwargs):
                return {"ok": True, "error": None, "opportunities": [opportunity]}

            def planner(*_args):
                return {"decisions": [decision]}

            def submitter(**kwargs):
                submitted.append(kwargs["project_id"])
                return {"ok": True, "submitted": True, "application_verified": True, "project_id": kwargs["project_id"], "provider_proposal_id": "9000010"}

            with tempfile.TemporaryDirectory() as directory, patch.object(application_loop.application_tick, "read_pending_descriptor", return_value=None), patch.object(application_loop.application_tick, "state_has_claim", return_value=False):
                result = application_loop.run_loop(state_path=Path(directory) / "application.json", evidence_root=Path(directory) / "evidence", discoverer=discoverer, planner=planner, submitter=submitter, clock=lambda: datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc))

            self.assertEqual(submitted, ["6000001"] if accepted else [], name)
            self.assertEqual(result.get("verified_count"), 1 if accepted else 0, name)

    def test_ongoing_operation_request_pair_accepts_40_char_proximity_in_either_order(self):
        application_loop = _load_deployed_loop()
        forward = "SNSアカウントの全投稿を含む運用を安定して継続できる体制づくりの検討を依頼したいと考えています。"
        self.assertEqual((len(forward), forward.index("運用"), forward.index("依頼")), (49, 15, 36))
        newline = "SNSアカウントの継続運用を長期に安定して継続するための体制を\n依頼したいです。"
        self.assertEqual((newline.index("依頼") - newline.index("運用") - 2, newline.count("\n")), (19, 1))
        cases = (
            ("forward_21_char_gap", forward, []),
            ("forward_newline_19_char_gap", newline, []),
            ("reverse", "SNSの長期継続案件として、専門家へ依頼し、月次のアカウント運用を予定します。", []),
            ("bare_request", "SNSの長期継続案件として、専門家へ依頼します。", ["planner_failed"]),
        )
        for name, evidence, expected in cases:
            row = _opportunity("6000001")
            row["description"] = "依頼主の業種: 情報通信業\n依頼概要: " + evidence
            decision = _eligible_decision(qualification=_qualification(ongoing_sns_outsourcing_evidence=evidence))
            self.assertEqual(application_loop.validate_decisions([row], {"decisions": [decision]}, datetime(2026, 8, 13, tzinfo=timezone.utc)), expected, name)

    def test_qualification_cost_source_version_is_typed_for_codex_schema(self):
        schema = json.loads((REPO_ROOT / "skills/gig-work/schemas/application_decisions.schema.json").read_text(encoding="utf-8"))
        leaf = schema["properties"]["decisions"]["items"]["properties"]["qualification"]["properties"]["cost_source_version"]
        self.assertEqual(leaf, {"type": "string", "const": "lancers-g1-conservative-v1"})


if __name__ == "__main__":
    unittest.main()
