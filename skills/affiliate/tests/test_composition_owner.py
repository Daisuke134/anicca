from __future__ import annotations

import importlib.util
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "composition_owner.py"


class CompositionOwnerTests(unittest.TestCase):
    def test_wake_advances_only_one_due_source_set_and_dedupes_terminal_receipt(self) -> None:
        spec = importlib.util.spec_from_file_location("affiliate_composition_owner", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            inbox = state / "composition-inbox"
            inbox.mkdir(parents=True)
            bundle = {
                "schema_version": 1,
                "receipt_type": "COMPOSITION_INPUT",
                "plan_id": "alpha-en",
                "locale": "en",
                "source_set_sha256": "a" * 64,
                "sources": [],
            }
            (inbox / "alpha-en.json").write_text(json.dumps(bundle), encoding="utf-8")
            completed = {
                "state": "READY_FOR_POLICY",
                "plan_id": "alpha-en",
                "locale": "en",
                "source_set_sha256": "a" * 64,
                "result_sha256": "b" * 64,
            }
            run_model = mock.Mock(return_value=completed)
            build_handoff = mock.Mock(return_value="c" * 64)
            build_policy = mock.Mock(return_value="d" * 64)

            first = module.wake(
                root, state, run_model=run_model, handoff_builder=build_handoff,
                policy_builder=build_policy,
            )
            second = module.wake(
                root, state, run_model=run_model, handoff_builder=build_handoff,
                policy_builder=build_policy,
            )
            third = module.wake(
                root, state, run_model=run_model, handoff_builder=build_handoff,
                policy_builder=build_policy,
            )

            self.assertEqual(first["state"], "READY_FOR_POLICY")
            self.assertEqual(second["policy_sha256"], "d" * 64)
            self.assertEqual(third["state"], "IDLE")
            self.assertEqual(run_model.call_count, 1)
            self.assertEqual(build_handoff.call_count, 1)
            self.assertEqual(build_policy.call_count, 1)
            receipt = json.loads(
                (state / "composition-receipts" / "alpha-en.json").read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["source_set_sha256"], "a" * 64)
            self.assertEqual(receipt["handoff_sha256"], "c" * 64)
            self.assertEqual(receipt["policy_sha256"], "d" * 64)

    def test_build_policy_writes_one_hash_bound_pass_receipt(self) -> None:
        spec = importlib.util.spec_from_file_location("affiliate_composition_owner", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            raw = b"Official product documentation for the benchmark."
            raw_sha256 = hashlib.sha256(raw).hexdigest()
            source = {
                "source_id": "official-product",
                "locator": "https://example.com/official",
                "evidence_class": "official_product",
                "raw_sha256": raw_sha256,
            }
            source_set_sha256 = hashlib.sha256(json.dumps(
                [source], sort_keys=True, separators=(",", ":")
            ).encode()).hexdigest()
            bundle = {
                "schema_version": 1,
                "receipt_type": "COMPOSITION_INPUT",
                "plan_id": "alpha-en",
                "locale": "en",
                "source_set_sha256": source_set_sha256,
                "sources": [source],
            }
            source_dir = state / "sources" / source["source_id"]
            source_dir.mkdir(parents=True)
            (source_dir / f"{raw_sha256}.md").write_bytes(raw)
            (source_dir / "latest.json").write_text(json.dumps({
                **source,
                "schema_version": 1,
                "receipt_type": "SOURCE_CAPTURE",
                "plan_id": "alpha-en",
                "locale": "en",
                "expires_at": "2099-01-01T00:00:00+00:00",
            }), encoding="utf-8")
            plan_dir = root / "config" / "source-plans"
            plan_dir.mkdir(parents=True)
            (plan_dir / "alpha-en.json").write_text(json.dumps({
                "plan_id": "alpha-en",
                "locale": "en",
                "offer_id": "alpha-offer",
                "buyer_intent": "Buyers comparing the documented product",
                "slug": "alpha-product-guide",
            }), encoding="utf-8")
            article = (
                "A buyer should benchmark the documented product before paying. " * 14
                + "[Official source](https://example.com/official)\n\n"
                + module.DISCLOSURE
                + "\n\n[Review the product]({{AFFILIATE_LINK}})"
            )
            handoff = {
                "schema_version": 1,
                "receipt_type": "CAMPAIGN_HANDOFF",
                "state": "READY_FOR_POLICY",
                "plan_id": "alpha-en",
                "offer_id": "alpha-offer",
                "locale": "en",
                "buyer_intent": "Buyers comparing the documented product",
                "title": "Alpha Product Guide",
                "slug": "alpha-product-guide",
                "owned_article_markdown": article,
                "disclosure": module.DISCLOSURE,
                "cta_placeholder": "{{AFFILIATE_LINK}}",
                "cited_sources": [{
                    "source_id": source["source_id"],
                    "locator": source["locator"],
                    "raw_sha256": raw_sha256,
                }],
                "x_copy": "Affiliate disclosure: Alpha Product Guide\n\n{{OWNED_ARTICLE_URL}}",
                "source_set_sha256": source_set_sha256,
                "content_fingerprint": hashlib.sha256(article.encode()).hexdigest(),
                "result_fingerprint": "b" * 64,
            }
            handoff["handoff_fingerprint"] = hashlib.sha256(json.dumps(
                handoff, sort_keys=True, separators=(",", ":")
            ).encode()).hexdigest()
            handoff_path = state / "campaign-handoffs" / "alpha-en.json"
            handoff_path.parent.mkdir(parents=True)
            handoff_path.write_text(json.dumps(handoff), encoding="utf-8")
            handoff_sha256 = hashlib.sha256(handoff_path.read_bytes()).hexdigest()
            audit_runner = mock.Mock(return_value={
                "decision": "PASS",
                "unsupported_claims": [],
                "rationale": "Every material claim is supported by the supplied source.",
                "result_sha256": "e" * 64,
                "evidence_dir": str(state / "policy-runs" / "alpha-en"),
                "execution": {"selected_model": "gpt-5.6-terra"},
            })

            policy_sha256 = module.build_policy(
                root, state, bundle,
                {"handoff_sha256": handoff_sha256},
                audit_runner=audit_runner,
            )

            policy_path = state / "campaign-policy" / "alpha-en.json"
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            self.assertEqual(policy_sha256, hashlib.sha256(policy_path.read_bytes()).hexdigest())
            self.assertEqual(policy["decision"], "PASS")
            self.assertTrue(all(policy["checks"].values()))
            self.assertEqual(policy["handoff_sha256"], handoff_sha256)
            self.assertEqual(audit_runner.call_count, 1)


if __name__ == "__main__":
    unittest.main()
