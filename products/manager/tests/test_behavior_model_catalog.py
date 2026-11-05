"""Data catalog safety tests; no network, GPU or paid API calls."""
import unittest

from manager_core.behavior_model_catalog import MODELS, research_preflight


class BehaviorModelCatalogTests(unittest.TestCase):
    def test_card_inventory(self):
        self.assertEqual(set(MODELS), {
            "befm-1.5-4b", "centaur-70b", "ampersand-v0.1", "persimmon", "listen-twins"
        })

    def test_no_unapproved_external_spend(self):
        p = research_preflight("ampersand-v0.1", provider_api_available=True)
        self.assertFalse(p.ready)
        self.assertIn("No external spending authorization", p.blocking_reasons)

    def test_hf_gate(self):
        p = research_preflight("befm-1.5-4b", cloud_gpu_gb=24, paid_inference_budget_authorized=True)
        self.assertFalse(p.ready)
        self.assertTrue(any("terms" in reason for reason in p.blocking_reasons))

    def test_gpu_gate(self):
        p = research_preflight("centaur-70b", accepted_model_terms=True,
                               paid_inference_budget_authorized=True, cloud_gpu_gb=24)
        self.assertFalse(p.ready)
        self.assertIn("Insufficient cloud GPU VRAM", p.blocking_reasons)

    def test_license_protects_commercial_dataset(self):
        p = research_preflight("befm-1.5-4b",
                               accepted_model_terms=True, cloud_gpu_gb=24,
                               paid_inference_budget_authorized=True,
                               uses_behaviorbench_test_data=True)
        self.assertFalse(p.ready)
        self.assertTrue(any("CC BY-NC-ND" in x for x in p.blocking_reasons))

    def test_open_model_clear_but_inference_not_performed(self):
        p = research_preflight("befm-1.5-4b",
                               accepted_model_terms=True, cloud_gpu_gb=24,
                               paid_inference_budget_authorized=True)
        self.assertTrue(p.ready)
        self.assertIn("no model inference", p.note)

    def test_api_clear_but_external_execution_required(self):
        p = research_preflight("ampersand-v0.1",
                               provider_api_available=True, paid_inference_budget_authorized=True)
        self.assertTrue(p.ready)
        self.assertIn("no model inference", p.note)

    def test_nonpublic_weights_not_executable(self):
        for key in ("persimmon", "listen-twins"):
            p = research_preflight(key, provider_api_available=True,
                                   paid_inference_budget_authorized=True)
            self.assertFalse(p.ready)

    def test_unknown_model_rejected(self):
        with self.assertRaises(ValueError):
            research_preflight("simulated-but-nonexistent")

    def test_invalid_memory_rejected(self):
        for v in (-1, 10.0, None):
            with self.assertRaises(ValueError):
                research_preflight("centaur-70b", cloud_gpu_gb=v)


if __name__ == "__main__":
    unittest.main()
