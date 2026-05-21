import json
import unittest
from unittest.mock import patch, MagicMock


class _Resp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class PostToTikTokTests(unittest.TestCase):
    def setUp(self):
        # Import inside test so patches can target module symbols reliably.
        import tools  # noqa: F401

    @patch("tools.time.sleep")
    @patch("tools._append_dlq_entry")
    def test_non_retryable_auth_goes_to_dlq(self, dlq_mock, sleep_mock):
        import tools

        tools.api.record_ops_event = MagicMock(return_value={"success": True})

        with patch("tools.requests.post") as post_mock:
            post_mock.return_value = _Resp(401, text="unauthorized")
            out = json.loads(
                tools.post_to_tiktok(image_url="https://example.com/i.png", caption="hello", hashtags=[])
            )

        self.assertFalse(out["success"])
        self.assertEqual(out["category"], tools.ERR_AUTH)
        sleep_mock.assert_not_called()
        dlq_mock.assert_called_once()
        tools.api.record_ops_event.assert_called()

    @patch("tools.time.sleep")
    @patch("tools._append_dlq_entry")
    def test_retry_provider_outage_then_success(self, dlq_mock, sleep_mock):
        import tools

        tools.api.record_ops_event = MagicMock(return_value={"success": True})

        with patch("tools.requests.post") as post_mock:
            post_mock.side_effect = [
                _Resp(500, text="oops"),
                _Resp(200, payload={"postSubmissionId": "p1"}),
            ]
            out = json.loads(
                tools.post_to_tiktok(image_url="https://example.com/i.png", caption="hello", hashtags=[])
            )

        self.assertTrue(out["success"])
        self.assertEqual(out["blotato_post_id"], "p1")
        sleep_mock.assert_called_once_with(60)
        dlq_mock.assert_not_called()

    @patch("tools.time.sleep")
    @patch("tools._append_dlq_entry")
    def test_rate_limit_retries_then_dlq(self, dlq_mock, sleep_mock):
        import tools

        tools.api.record_ops_event = MagicMock(return_value={"success": True})

        with patch("tools.requests.post") as post_mock:
            post_mock.side_effect = [
                _Resp(429, text="rate"),
                _Resp(429, text="rate"),
                _Resp(429, text="rate"),
            ]
            out = json.loads(
                tools.post_to_tiktok(image_url="https://example.com/i.png", caption="hello", hashtags=[])
            )

        self.assertFalse(out["success"])
        self.assertEqual(out["category"], tools.ERR_RATE_LIMIT)
        # 3 attempts -> 2 sleeps (60, 300), then DLQ on last attempt
        self.assertEqual([c.args[0] for c in sleep_mock.call_args_list], [60, 300])
        dlq_mock.assert_called_once()

    @patch.dict("os.environ", {"BLOTATO_DRY_RUN": "true"}, clear=False)
    def test_dry_run_skips_network_and_succeeds(self):
        import tools

        tools.api.record_ops_event = MagicMock(return_value={"success": True})

        with patch("tools.requests.post") as post_mock:
            out = json.loads(
                tools.post_to_tiktok(image_url="https://example.com/i.png", caption="hello", hashtags=[])
            )

        self.assertTrue(out["success"])
        self.assertTrue(out.get("dry_run"))
        self.assertTrue(out["blotato_post_id"].startswith("dryrun-"))
        post_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
