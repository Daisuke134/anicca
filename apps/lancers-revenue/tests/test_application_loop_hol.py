import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


DEPLOYED_LOOP_PATH = Path(
    "/Users/anicca/.local/lib/anicca/lancers/skills/earn/lancers/scripts/application_loop.py"
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


def _opportunity(project_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_type": "lancers_public_opportunity",
        "platform": "lancers",
        "external_id": project_id,
        "title": "業務改善のためのWebシステム開発",
        "description": "公開された要件に沿って業務を支援するWebシステムを開発する案件です。",
        "url": f"https://www.lancers.jp/work/detail/{project_id}",
        "category": "システム開発・運用",
        "budget_type": "fixed",
        "budget_min_minor": 100000,
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
            "公開された要件を丁寧に確認し、利用者の業務が円滑になるよう画面と処理の流れを整理します。"
            "現状の課題を踏まえて実装方針を提案し、確認事項は分かりやすく共有します。"
        ) * 5

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


if __name__ == "__main__":
    unittest.main()
