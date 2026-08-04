"""Contract tests for the dependency-free direct Telegram sender."""

from __future__ import annotations

import importlib.util
import json
import socket
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path


MODULE_PATH = Path(__file__).parents[1] / "telegram.py"
SPEC = importlib.util.spec_from_file_location("anicca_telegram", MODULE_PATH)
assert SPEC and SPEC.loader
telegram = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = telegram
SPEC.loader.exec_module(telegram)


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.payload

    def close(self):
        pass


def success(message_id=42):
    return {
        "ok": True,
        "result": {"message_id": message_id, "date": 1, "chat": {"id": 99}},
    }


class TelegramClientTest(unittest.TestCase):
    def test_loads_only_explicit_anicca_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            env_file = Path(tmp) / ".env"
            env_file.write_text(
                "TELEGRAM_BOT_TOKEN=test-token\nTELEGRAM_CHAT_ID=123\n",
                encoding="utf-8",
            )
            token, chat_id = telegram.load_config(environ={}, env_file=env_file)
        self.assertEqual(token, "test-token")
        self.assertEqual(chat_id, "123")

    def test_send_text_returns_every_message_id(self):
        requests = []

        def opener(request, timeout):
            requests.append((request, timeout))
            return FakeResponse(success(40 + len(requests)))

        client = telegram.TelegramClient("secret-token", "99", opener=opener)
        receipt = client.send_text("a" * 4001)
        self.assertEqual(receipt["message_ids"], [41, 42])
        self.assertEqual(receipt["chunks"], 2)
        self.assertEqual(
            json.loads(requests[0][0].data)["chat_id"],
            "99",
        )
        self.assertNotIn(b"secret-token", requests[0][0].data)

    def test_media_uses_correct_multipart_field(self):
        requests = []

        def opener(request, timeout):
            requests.append(request)
            return FakeResponse(success())

        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "proof.txt"
            media.write_text("evidence", encoding="utf-8")
            client = telegram.TelegramClient("token", "99", opener=opener)
            receipt = client.send_document(media, caption="proof")
        self.assertEqual(receipt["message_ids"], [42])
        self.assertIn("multipart/form-data", requests[0].headers["Content-type"])
        self.assertIn(b'name="document"', requests[0].data)
        self.assertIn(b'name="caption"', requests[0].data)
        self.assertIn(b"evidence", requests[0].data)

    def test_429_retries_once_after_retry_after(self):
        attempts = []
        sleeps = []

        def opener(request, timeout):
            attempts.append(request)
            if len(attempts) == 1:
                payload = {
                    "ok": False,
                    "error_code": 429,
                    "description": "slow down",
                    "parameters": {"retry_after": 2},
                }
                return FakeResponse(payload)
            return FakeResponse(success())

        client = telegram.TelegramClient(
            "token", "99", opener=opener, sleeper=sleeps.append
        )
        receipt = client.send_text("hello")
        self.assertEqual(receipt["message_ids"], [42])
        self.assertEqual(sleeps, [2])
        self.assertEqual(len(attempts), 2)

    def test_timeout_is_delivery_unknown_and_not_retried(self):
        attempts = []

        def opener(request, timeout):
            attempts.append(request)
            raise socket.timeout("timed out")

        client = telegram.TelegramClient("token", "99", opener=opener)
        with self.assertRaises(telegram.TelegramDeliveryUnknown):
            client.send_text("hello")
        self.assertEqual(len(attempts), 1)

    def test_api_error_redacts_token(self):
        def opener(request, timeout):
            return FakeResponse(
                {
                    "ok": False,
                    "error_code": 401,
                    "description": "bad token secret-token",
                }
            )

        client = telegram.TelegramClient("secret-token", "99", opener=opener)
        with self.assertRaises(telegram.TelegramError) as caught:
            client.send_text("hello")
        self.assertNotIn("secret-token", str(caught.exception))
        self.assertIn("***", str(caught.exception))

    def test_http_error_does_not_expose_token_url(self):
        def opener(request, timeout):
            raise urllib.error.HTTPError(
                request.full_url,
                502,
                "bad gateway",
                {},
                FakeResponse({"not": "telegram"}),
            )

        client = telegram.TelegramClient("secret-token", "99", opener=opener)
        with self.assertRaises(telegram.TelegramError) as caught:
            client.send_text("hello")
        self.assertNotIn("secret-token", str(caught.exception))

    def test_caption_limit_and_missing_file_fail_locally(self):
        client = telegram.TelegramClient("token", "99", opener=lambda *_a, **_k: None)
        with self.assertRaises(telegram.TelegramError):
            client.send_photo("/definitely/missing.png")
        with tempfile.TemporaryDirectory() as tmp:
            media = Path(tmp) / "photo.png"
            media.write_bytes(b"png")
            with self.assertRaises(telegram.TelegramError):
                client.send_photo(media, caption="x" * 1025)

    def test_source_has_no_openclaw_dependency(self):
        source = MODULE_PATH.read_text(encoding="utf-8").lower()
        self.assertNotIn(".openclaw", source)
        self.assertNotIn("openclaw message", source)


if __name__ == "__main__":
    unittest.main()
