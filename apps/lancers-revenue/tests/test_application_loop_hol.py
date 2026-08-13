import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


DEPLOYED_LOOP_PATH = Path(
    "/Users/operator/.local/lib/anicca/lancers/skills/earn/lancers/scripts/application_loop.py"
)


def _load_deployed_loop():
    spec = importlib.util.spec_from_file_location(
        "test_deployed_lancers_application_loop", DEPLOYED_LOOP_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("deployed_application_loop_unavailable")
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
        "title": "業務改善のためのWebシステム開発",
        "description": (
            "公開された要件に沿って業務を支援するWebシステムを開発する案件です。"
            "少人数の担当者がSNSを兼務しており、運用を整備します。"
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


class ApplicationLoopHolTests(unittest.TestCase):
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
                            "small_b2b_evidence": "業務改善のためのWebシステム開発",
                            "sns_staff_evidence": "少人数の担当者がSNSを兼務",
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

    def test_rejects_eligible_decision_below_seventy_percent_margin(self):
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
                            "small_b2b_evidence": "業務改善のためのWebシステム開発",
                            "sns_staff_evidence": "少人数の担当者がSNSを兼務",
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

        self.assertEqual(result["error"], "planner_failed")
        self.assertEqual(submitter_project_ids, [])


if __name__ == "__main__":
    unittest.main()
