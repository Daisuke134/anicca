import json
import tempfile
import unittest
from pathlib import Path

from job_search_loop.observability_service import docker_run_args, health_receipt


class ObservabilityServiceTests(unittest.TestCase):
    def test_launcher_contract_is_pinned_private_and_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            volume = Path(directory) / "private-data"
            config = {
                "version": 1,
                "container_name": "anicca-job-hunter-observability",
                "image": "grafana/otel-lgtm@sha256:" + "4" * 64,
                "volume": str(volume),
                "retention": "30d",
            }
            args = docker_run_args(config)
            self.assertEqual(args[-1], config["image"])
            self.assertIn("127.0.0.1:4318:4318", args)
            self.assertIn("127.0.0.1:3000:3000", args)
            self.assertIn(f"{volume.resolve()}:/data", args)
            self.assertIn("max-size=10m", args)
            self.assertIn("max-file=3", args)
            self.assertIn("PROMETHEUS_EXTRA_ARGS=--storage.tsdb.retention.time=30d", args)
            self.assertEqual(volume.stat().st_mode & 0o777, 0o700)

    def test_health_receipt_contains_no_private_payload(self):
        receipt = health_receipt(
            image_id="sha256:" + "a" * 64,
            running=True,
            otlp_healthy=True,
            grafana_healthy=True,
        )
        self.assertEqual(receipt["status"], "healthy")
        self.assertEqual(receipt["listeners"], ["127.0.0.1:3000", "127.0.0.1:4318"])
        self.assertNotIn("payload", json.dumps(receipt))


if __name__ == "__main__":
    unittest.main()
