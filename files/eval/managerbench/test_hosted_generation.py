import unittest,json
from hosted_generation import classify

class HostedGenerationTests(unittest.TestCase):
    def receipt(self, text, truncated=False):
        return {"config":{"model":"test"},"events":["event: complete","data: "+json.dumps([json.dumps({"text":text,"truncated":truncated})])]}
    def test_gpu_limit(self):
        self.assertEqual(classify(self.receipt("⚠️ Generation failed before any output: Space app has reached its GPU limit.", True))["status"],"PROVIDER_GPU_LIMIT")
    def test_actual_text_not_automatically_valid(self):
        self.assertFalse(classify(self.receipt("42"))["valid"])
    def test_truncation(self):
        self.assertEqual(classify(self.receipt("42",True))["status"],"INCOMPLETE_OR_PROVIDER_ERROR")
    def test_malformed(self):
        self.assertEqual(classify({"config":{"model":"test"},"events":["event: complete","data: nonsense"]})["status"],"INVALID_ENVELOPE")
    def test_missing_model(self):
        self.assertEqual(classify({})["status"],"MODEL_ID_UNVERIFIED")
    def test_incomplete(self):
        self.assertEqual(classify({"config":{"model":"test"},"events":[]})["status"],"INCOMPLETE_STREAM")
