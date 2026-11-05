"""Contract tests use fake CLI text solely to test the receipt format."""
import unittest

from qwen3_cpu_first_inference import GGUF_SHA256, STUDY_PROMPT, receipt


class FirstInferenceReceiptTests(unittest.TestCase):
    def test_transcript_not_benchmark(self):
        item = receipt("model loaded\nassistant: 4\n", 12, GGUF_SHA256)
        self.assertTrue(item["inference_executed"])
        self.assertFalse(item["be_fm_adapter_loaded"])
        self.assertFalse(item["behavior_prediction_accuracy_measured"])
        self.assertFalse(item["user_intervention_performed"])
        self.assertEqual(item["duration_seconds"], 12)
        self.assertIn("assistant: 4", item["stdout_excerpt"])

    def test_reject_empty_inference(self):
        with self.assertRaises(ValueError):
            receipt(" ", 5, GGUF_SHA256)

    def test_reject_unpinned_gguf(self):
        with self.assertRaises(ValueError):
            receipt("answer: 4", 5, "0" * 64)

    def test_reject_bad_duration(self):
        with self.assertRaises(ValueError):
            receipt("answer: 4", -1, GGUF_SHA256)

    def test_prompt_is_nonpersonal(self):
        self.assertIn("fictional", STUDY_PROMPT)
        self.assertNotIn("participant_id", STUDY_PROMPT)


if __name__ == "__main__":
    unittest.main()
