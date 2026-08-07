import os
import unittest
from io import StringIO
from unittest.mock import patch

from job_search_loop.codex_app_server import CodexAppServer, JsonLineProcessTransport


class FakeTransport:
    def __init__(self, incoming):
        self.incoming = iter(incoming)
        self.sent = []

    def send(self, message):
        self.sent.append(message)

    def receive(self):
        return next(self.incoming)

    def close(self):
        pass


class CodexAppServerTests(unittest.TestCase):
    def test_stdio_factory_starts_official_app_server_directly(self):
        class Process:
            stdin = StringIO()
            stdout = StringIO()
            stderr = StringIO()

        environment = {
            "HOME": "/Users/test",
            "PATH": "/usr/bin",
            "SHELL": "/bin/zsh",
            "TELEGRAM_BOT_TOKEN": "must-not-pass",
            "GMAIL_CLIENT_SECRET": "must-not-pass",
            "SESSION_COOKIE": "must-not-pass",
        }
        with patch.dict(os.environ, environment, clear=True), patch(
            "job_search_loop.codex_app_server.subprocess.Popen", return_value=Process()
        ) as popen:
            JsonLineProcessTransport.stdio(codex="/opt/codex")

        self.assertEqual(popen.call_args.args[0], ["/opt/codex", "app-server", "--stdio"])
        child_environment = popen.call_args.kwargs["env"]
        self.assertEqual(child_environment["HOME"], "/Users/test")
        self.assertEqual(child_environment["PATH"], "/usr/bin")
        self.assertNotIn("TELEGRAM_BOT_TOKEN", child_environment)
        self.assertNotIn("GMAIL_CLIENT_SECRET", child_environment)
        self.assertNotIn("SESSION_COOKIE", child_environment)

    def test_initialize_and_request_stream_notifications(self):
        transport = FakeTransport(
            [
                {"id": 1, "result": {"userAgent": "codex-test"}},
                {"method": "turn/started", "params": {"turn": {"id": "turn-1"}}},
                {"id": 2, "result": {"turn": {"id": "turn-1"}}},
            ]
        )
        events = []
        client = CodexAppServer(transport, on_event=events.append)

        client.initialize(name="job-hunter", version="1")
        result = client.turn_start("thread-1", "continue")

        self.assertEqual(result["turn"]["id"], "turn-1")
        self.assertEqual(events[0]["method"], "turn/started")
        self.assertEqual(transport.sent[0]["method"], "initialize")
        self.assertEqual(transport.sent[1], {"method": "initialized"})
        self.assertEqual(transport.sent[2]["method"], "turn/start")
        self.assertEqual(
            transport.sent[2]["params"]["input"],
            [{"type": "text", "text": "continue"}],
        )

    def test_wait_for_event_streams_until_matching_notification(self):
        transport = FakeTransport(
            [
                {"method": "item/started", "params": {"item": {"id": "item-1"}}},
                {
                    "method": "turn/completed",
                    "params": {"turn": {"id": "turn-1", "status": "completed"}},
                },
            ]
        )
        events = []
        client = CodexAppServer(transport, on_event=events.append)

        completed = client.wait_for_event("turn/completed")

        self.assertEqual(completed["params"]["turn"]["status"], "completed")
        self.assertEqual([event["method"] for event in events], ["item/started", "turn/completed"])

    def test_thread_methods_are_thin_protocol_wrappers(self):
        transport = FakeTransport(
            [
                {"id": 1, "result": {"thread": {"id": "thread-1"}}},
                {"id": 2, "result": {"thread": {"id": "thread-1"}}},
                {"id": 3, "result": {"thread": {"id": "thread-1"}}},
                {"id": 4, "result": {}},
            ]
        )
        client = CodexAppServer(transport)

        client.thread_start(cwd="/tmp/work", model="gpt-5.6-luna")
        client.thread_resume("thread-1")
        client.thread_read("thread-1")
        client.thread_archive("thread-1")

        self.assertEqual(
            [message["method"] for message in transport.sent],
            ["thread/start", "thread/resume", "thread/read", "thread/archive"],
        )
        self.assertEqual(transport.sent[0]["params"]["sandbox"], "read-only")
        self.assertEqual(
            transport.sent[0]["params"]["config"]["shell_environment_policy"],
            {
                "inherit": "core",
                "ignore_default_excludes": False,
                "exclude": ["*PASSWORD*", "*COOKIE*"],
            },
        )

    def test_job_hunter_profile_has_full_access_without_secret_inheritance(self):
        transport = FakeTransport(
            [{"id": 1, "result": {"thread": {"id": "thread-1"}}}]
        )
        client = CodexAppServer(transport)

        client.thread_start(
            cwd="/tmp/work",
            model="gpt-5.6-luna",
            capability_profile="job-hunter",
        )

        params = transport.sent[0]["params"]
        self.assertEqual(params["approvalPolicy"], "never")
        self.assertEqual(params["sandbox"], "danger-full-access")
        self.assertNotIn("permissions", params)
        self.assertEqual(
            params["config"]["shell_environment_policy"]["inherit"], "core"
        )


if __name__ == "__main__":
    unittest.main()
