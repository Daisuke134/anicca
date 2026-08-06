import unittest
from pathlib import Path


class NativeObservabilityServiceTests(unittest.TestCase):
    def test_collector_is_loopback_file_backed_and_bounded(self):
        config = (
            Path(__file__).parents[1] / "config" / "otel-collector.v1.yaml"
        ).read_text(encoding="utf-8")
        self.assertIn("endpoint: 127.0.0.1:4318", config)
        self.assertNotIn("0.0.0.0", config)
        self.assertIn("path: ${env:JOB_HUNTER_TRACE_PATH}", config)
        self.assertIn("max_megabytes: 10", config)
        self.assertIn("max_days: 30", config)
        self.assertIn("max_backups: 10", config)
        self.assertIn("timeout: 2s", config)
        self.assertIn("send_batch_size: 128", config)
        self.assertIn("receivers: [otlp]", config)
        self.assertIn("exporters: [file/job_hunter]", config)


if __name__ == "__main__":
    unittest.main()
