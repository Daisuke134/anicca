import importlib.util
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ADAPTER_PATH = REPO_ROOT / "skills/earn/lancers/scripts/lancers_adapter.py"


def _load():
    spec = importlib.util.spec_from_file_location("test_lancers_adapter", ADAPTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("lancers_adapter_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class LancersReceiptAdapterTests(unittest.TestCase):
    def test_maps_escrow_confirmed_project_to_contract_receipt(self):
        adapter = _load()

        receipt = adapter.normalize_contract_receipt(
            {
                "source_kind": "project",
                "project_id": "123",
                "proposal_id": "456",
                "status": "進行中",
                "funding_status": "escrow_confirmed",
                "price_jpy": 10000,
                "delivery_due_on": "2026-09-01",
                "proposal_text": "検証済みの提案本文",
            },
            observed_at="2026-08-26T08:00:00Z",
        )

        self.assertEqual(receipt["record_type"], "contract_receipt")
        self.assertEqual(receipt["application_external_id"], "456")
        self.assertEqual(receipt["contract_external_id"], "project:123")
        self.assertEqual(receipt["status"], "accepted")

    def test_rejects_candidate_without_escrow_readback(self):
        adapter = _load()

        with self.assertRaisesRegex(adapter.LancersProjectError, "contract_funding_unverified"):
            adapter.normalize_contract_receipt(
                {
                    "source_kind": "project",
                    "project_id": "123",
                    "proposal_id": "456",
                    "status": "進行中",
                    "funding_status": "requires_detail_readback",
                    "price_jpy": 10000,
                    "delivery_due_on": "2026-09-01",
                    "proposal_text": "検証済みの提案本文",
                },
                observed_at="2026-08-26T08:00:00Z",
            )


class LancersApplicationIntentTests(unittest.TestCase):
    OPPORTUNITY = {
        "schema_version": 1,
        "record_type": "opportunity",
        "platform": "lancers",
        "external_id": "5551",
        "title": "SNS運用代行",
        "description": "月次のSNS投稿運用をお願いします。",
        "url": "https://www.lancers.jp/work/detail/5551",
        "category": "web_marketing",
        "budget_type": "range",
        "budget_min_minor": 30000,
        "budget_max_minor": 50000,
        "currency": "JPY",
        "buyer_external_id": "buyer-1",
        "observed_at": "2026-08-31T00:00:00Z",
    }

    def _intent(self, adapter, **overrides):
        kwargs = {
            "proposal_text": "月次運用の実績があります。",
            "proposed_amount_minor": 40000,
            "created_at": "2026-08-31T00:00:00Z",
        }
        kwargs.update(overrides)
        return adapter.normalize_application_intent(self.OPPORTUNITY, **kwargs)

    def test_intent_carries_the_opportunity_terms_and_is_reproducible(self):
        adapter = _load()

        intent = self._intent(adapter)

        self.assertEqual(intent["record_type"], "application_intent")
        self.assertEqual(intent["opportunity_external_id"], "5551")
        self.assertEqual(intent["proposed_amount_minor"], 40000)
        self.assertEqual(intent["currency"], "JPY")
        self.assertEqual(intent["idempotency_key"], "lancers:application_intent:5551:v1")
        self.assertEqual(intent, self._intent(adapter))

    def test_rewriting_the_text_moves_the_content_hash_but_not_the_fence(self):
        adapter = _load()

        first = self._intent(adapter)
        second = self._intent(adapter, proposal_text="別の書き方の提案本文。")

        # A second attempt at the same listing has to collide, so the key cannot
        # follow the text.
        self.assertEqual(first["idempotency_key"], second["idempotency_key"])
        self.assertNotEqual(first["content_sha256"], second["content_sha256"])

    def test_intent_fails_closed_on_unusable_terms(self):
        adapter = _load()

        for overrides in (
            {"proposal_text": "   "},
            {"proposed_amount_minor": 0},
            {"proposed_amount_minor": -1},
            {"proposed_amount_minor": True},
            {"proposed_amount_minor": 40000.0},
        ):
            with self.subTest(**overrides), self.assertRaises(adapter.LancersProjectError):
                self._intent(adapter, **overrides)

        with self.assertRaises(adapter.LancersProjectError):
            adapter.normalize_application_intent(
                dict(self.OPPORTUNITY, record_type="event"),
                proposal_text="本文",
                proposed_amount_minor=40000,
                created_at="2026-08-31T00:00:00Z",
            )


class LancersAdapterJudgmentTests(unittest.TestCase):
    """The adapter must be unable to prefer one listing over another.

    Ranking belongs to the model. Rather than hunt for scoring code, deny the
    adapter every source a judgment could come from: a model, the network, a
    subprocess, randomness, or the wall clock.
    """

    FORBIDDEN_MODULES = {
        "random", "secrets", "subprocess", "socket", "requests", "httpx",
        "urllib.request", "http.client", "asyncio", "openai", "anthropic",
    }
    FORBIDDEN_CALLS = {"now", "today", "utcnow", "monotonic", "random", "choice", "shuffle"}

    def test_adapter_has_no_source_of_judgment(self):
        import ast

        tree = ast.parse(ADAPTER_PATH.read_text(encoding="utf-8"))

        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        self.assertEqual(imported & self.FORBIDDEN_MODULES, set())

        called = {
            node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
        }
        self.assertEqual(called & self.FORBIDDEN_CALLS, set())

    def test_normalize_projects_keeps_provider_order(self):
        adapter = _load()

        cards = [
            {
                "id": str(external_id),
                "title": "SNS運用代行",
                "description": "月次のSNS投稿運用をお願いします。",
                "url": f"https://www.lancers.jp/work/detail/{external_id}",
                "category": "web_marketing",
                "budget_type": "range",
                "budget_min": 30000,
                "budget_max": 50000,
                "currency": "JPY",
                "buyer_external_id": "buyer-1",
            }
            for external_id in (9003, 9001, 9002)
        ]

        normalized, rejected = adapter.normalize_projects(cards, observed_at="2026-08-31T00:00:00Z")

        self.assertEqual(rejected, [])
        self.assertEqual([row["external_id"] for row in normalized], ["9003", "9001", "9002"])


if __name__ == "__main__":
    unittest.main()
