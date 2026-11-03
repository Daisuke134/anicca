"""Run the CLI against an isolated fixture of the existing JSON-lines protocol."""

import argparse
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import unittest


BINARY = None
MESSAGE = {
    "id": "message-one", "from": "alice/worker", "from_agent": "cli",
    "from_repo": None, "to": "alex/hq-codex", "via": None,
    "reply_to": None, "body": "keep <this> unchanged", "wake": True,
    "notify": False, "sent_at": 123,
}


class Fixture:
    def __init__(self, handler):
        self.handler = handler
        self.directory = tempfile.TemporaryDirectory(prefix="rhq-", dir="/tmp")
        self.root = Path(self.directory.name)
        self.home = self.root / "network"
        self.home.mkdir()
        self.requests = []
        self.errors = []
        self.socket = socket.socket(socket.AF_UNIX)
        self.socket.bind(str(self.home / "network.sock"))
        self.socket.listen()
        self.socket.settimeout(0.1)
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self.serve, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.closed.set()
        self.thread.join(timeout=3)
        self.socket.close()
        self.directory.cleanup()
        if self.errors:
            raise self.errors[0]

    def serve(self):
        try:
            while not self.closed.is_set():
                try:
                    connection, _ = self.socket.accept()
                except socket.timeout:
                    continue
                with connection, connection.makefile("rwb") as stream:
                    while line := stream.readline():
                        request = json.loads(line)
                        self.requests.append(request)
                        result = self.handler(request)
                        stream.write(json.dumps({"id": request["id"], **result}).encode() + b"\n")
                        stream.flush()
        except Exception as error:
            self.errors.append(error)

    def env(self):
        # No real daemon, login service, profile, or user's legacy state is used.
        return {
            **os.environ, "HOME": str(self.root / "user"),
            "REASON_NETWORK_HOME": str(self.home), "TINCAN_HOME": str(self.home),
            "REASON_NETWORK_NO_SERVICE": "1", "REASON_NETWORK_NO_TRAY": "1",
        }

    def run(self, *args, body=None):
        return subprocess.run([BINARY, *args], input=body, text=True, capture_output=True,
                              timeout=5, env=self.env(), cwd=self.root)


def replies(request):
    if request["op"] == "hook":
        return {"ok": True, "result": {"address": "alex/hq-codex", "ids": []}}
    if request["op"] == "inbox":
        return {"ok": True, "result": {"messages": [MESSAGE], "text": "framed <message>"}}
    if request["op"] == "delivered":
        return {"ok": True, "result": None}
    raise AssertionError(f"unexpected operation: {request['op']}")


class HqCliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if BINARY is None:
            raise RuntimeError("pass --binary with the dedicated test binary")

    def test_help_exposes_inbox_and_ack(self):
        result = subprocess.run([BINARY, "--help"], text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertRegex(result.stdout, r"(?m)^\s+inbox\s")
        self.assertRegex(result.stdout, r"(?m)^\s+ack\s")

    def test_inbox_always_peeks_and_preserves_message_body(self):
        for flags in ([], ["--peek"]):
            with self.subTest(flags=flags), Fixture(replies) as fixture:
                result = fixture.run("inbox", "--as", "hq-codex", "--wait", "7", "--json", *flags)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertEqual(json.loads(result.stdout), {
                    "session_key": "cli:hq-codex", "address": "alex/hq-codex",
                    "messages": [MESSAGE], "text": "framed <message>",
                })
                self.assertEqual([r["op"] for r in fixture.requests], ["hook", "inbox"])
                self.assertEqual(fixture.requests[0]["session_id"], "hq-codex")
                self.assertFalse(fixture.requests[0]["mail"])
                self.assertTrue(fixture.requests[0]["keep"])
                self.assertEqual({k: fixture.requests[1][k] for k in ("key", "wait_secs", "peek")},
                                 {"key": "cli:hq-codex", "wait_secs": 7, "peek": True})

    def test_ack_only_delivers_after_peeking_the_same_box(self):
        with Fixture(replies) as fixture:
            result = fixture.run("ack", "--as", "hq-codex", "--json", "message-one")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(json.loads(result.stdout), {
                "session_key": "cli:hq-codex", "address": "alex/hq-codex", "acked": ["message-one"],
            })
            self.assertEqual([r["op"] for r in fixture.requests], ["hook", "inbox", "delivered"])
            self.assertTrue(fixture.requests[1]["peek"])
            self.assertEqual(fixture.requests[1]["wait_secs"], 0)
            self.assertEqual(fixture.requests[2]["key"], "cli:hq-codex")
            self.assertEqual(fixture.requests[2]["ids"], ["message-one"])

    def test_ack_rejects_unknown_or_mixed_ids_without_any_delivery(self):
        for ids in (["sibling-id"], ["message-one", "sibling-id"]):
            with self.subTest(ids=ids), Fixture(replies) as fixture:
                result = fixture.run("ack", "--as", "hq-codex", "--json", *ids)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error", json.loads(result.stdout))
                self.assertEqual([r["op"] for r in fixture.requests], ["hook", "inbox"])

    def test_ack_rejects_a_sibling_recipient_even_if_the_id_is_returned(self):
        def sibling(request):
            if request["op"] == "inbox":
                return {"ok": True, "result": {"messages": [{**MESSAGE, "to": "alex/other"}], "text": ""}}
            return replies(request)
        with Fixture(sibling) as fixture:
            result = fixture.run("ack", "--as", "hq-codex", "--json", "message-one")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual([r["op"] for r in fixture.requests], ["hook", "inbox"])

    def test_empty_ack_and_missing_names_fail_before_registration(self):
        for args in (["ack", "--as", "hq-codex", "--json"], ["ack", "message-one"], ["inbox", "--json"],
                     ["inbox", "--as", "!!!", "--json"]):
            with self.subTest(args=args), Fixture(replies) as fixture:
                result = fixture.run(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(fixture.requests, [])

    def test_suffix_collision_fails_before_inbox_or_delivery(self):
        def collision(_):
            return {"ok": True, "result": {"address": "alex/hq-codex-2", "ids": []}}
        for args in (["inbox"], ["ack", "message-one"]):
            with self.subTest(args=args), Fixture(collision) as fixture:
                result = fixture.run(*args, "--as", "hq-codex", "--json")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error", json.loads(result.stdout))
                self.assertEqual([r["op"] for r in fixture.requests], ["hook"])

    def test_json_send_forwards_stdin_reply_and_idempotency_key(self):
        recipient = "alice/terminal@htch-runtime"
        receipt = {"ids": ["sent-one"], "recipients": [{"address": recipient, "state": "queued", "note": "waiting"}]}
        with Fixture(lambda _: {"ok": True, "result": receipt}) as fixture:
            result = fixture.run("send", "--from", "hq-codex", "--reply-to", "message-one",
                                 "--idempotency-key", "hq-receipt-one", "--json", recipient, "-",
                                 body="received <message>\n")
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(json.loads(result.stdout), receipt)
            self.assertEqual(len(fixture.requests), 1)
            request = fixture.requests[0]
            self.assertEqual({k: request[k] for k in ("op", "from", "to", "body", "reply_to", "idempotency_key")}, {
                "op": "send", "from": "hq-codex", "to": recipient, "body": "received <message>\n",
                "reply_to": "message-one", "idempotency_key": "hq-receipt-one",
            })

    def test_daemon_refusal_is_json_and_nonzero(self):
        with Fixture(lambda _: {"ok": False, "error": "fixture refusal"}) as fixture:
            result = fixture.run("inbox", "--as", "hq-codex", "--json")
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout), {"error": "fixture refusal"})

    def test_new_commands_do_not_start_a_daemon_or_migrate_legacy_state(self):
        for args in (["inbox", "--as", "hq-codex", "--json"],
                     ["ack", "--as", "hq-codex", "--json", "message-one"],
                     ["send", "--from", "hq-codex", "--json", "alice/worker", "body"]):
            with self.subTest(args=args), Fixture(replies) as fixture:
                fixture.closed.set()
                fixture.thread.join(timeout=3)
                fixture.socket.close()
                (fixture.home / "network.sock").unlink()
                legacy = fixture.home / "tincan.db"
                with sqlite3.connect(legacy) as connection:
                    connection.execute("CREATE TABLE marker (value TEXT)")
                connection.close()
                before = legacy.read_bytes()
                result = fixture.run(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("isn't running", json.loads(result.stdout)["error"])
                self.assertEqual(legacy.read_bytes(), before)
                self.assertFalse((fixture.home / "network.db").exists())
                self.assertFalse((fixture.home / "daemon.lock").exists())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--binary", type=lambda p: str(Path(p).resolve()), required=True)
    options, rest = parser.parse_known_args()
    BINARY = options.binary
    unittest.main(argv=[sys.argv[0], *rest])
