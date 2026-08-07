from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from typing import Any, Protocol, TextIO


class AppServerError(RuntimeError):
    pass


class Transport(Protocol):
    def send(self, message: dict[str, Any]) -> None: ...
    def receive(self) -> dict[str, Any]: ...
    def close(self) -> None: ...


class JsonLineProcessTransport:
    def __init__(self, process: subprocess.Popen[str]):
        if process.stdin is None or process.stdout is None:
            raise ValueError("app-server process requires stdin and stdout pipes")
        self.process = process
        self.stdin: TextIO = process.stdin
        self.stdout: TextIO = process.stdout

    @classmethod
    def stdio(cls, *, codex: str = "codex"):
        allowed = {
            "HOME",
            "PATH",
            "SHELL",
            "USER",
            "LOGNAME",
            "TMPDIR",
            "LANG",
            "LC_ALL",
            "LC_CTYPE",
        }
        return cls(
            subprocess.Popen(
                [codex, "app-server", "--stdio"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env={name: value for name, value in os.environ.items() if name in allowed},
            )
        )

    def send(self, message: dict[str, Any]) -> None:
        self.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
        self.stdin.flush()

    def receive(self) -> dict[str, Any]:
        line = self.stdout.readline()
        if not line:
            detail = self.process.stderr.read().strip() if self.process.stderr else ""
            raise AppServerError(f"app-server proxy closed: {detail}")
        message = json.loads(line)
        if not isinstance(message, dict):
            raise AppServerError("app-server returned a non-object message")
        return message

    def close(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=5)


class CodexAppServer:
    def __init__(
        self,
        transport: Transport,
        *,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ):
        self.transport = transport
        self.on_event = on_event or (lambda _event: None)
        self.next_id = 1

    def close(self) -> None:
        self.transport.close()

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        self.transport.send({"method": method, "id": request_id, "params": params})
        while True:
            message = self.transport.receive()
            if message.get("id") == request_id:
                if "error" in message:
                    raise AppServerError(f"{method} failed: {message['error']}")
                result = message.get("result")
                if not isinstance(result, dict):
                    raise AppServerError(f"{method} returned no object result")
                return result
            self.on_event(message)

    def initialize(self, *, name: str, version: str) -> dict[str, Any]:
        result = self._request(
            "initialize",
            {"clientInfo": {"name": name, "title": name, "version": version}},
        )
        self.transport.send({"method": "initialized"})
        return result

    def wait_for_event(self, method: str) -> dict[str, Any]:
        while True:
            message = self.transport.receive()
            self.on_event(message)
            if message.get("method") == method:
                return message

    def thread_start(self, *, cwd: str, model: str) -> dict[str, Any]:
        return self._request(
            "thread/start",
            {
                "cwd": cwd,
                "model": model,
                "approvalPolicy": "never",
                "sandbox": "read-only",
                "ephemeral": False,
                "serviceName": "job-hunter",
                "config": {
                    "shell_environment_policy": {
                        "inherit": "core",
                        "ignore_default_excludes": False,
                        "exclude": ["*PASSWORD*", "*COOKIE*"],
                    }
                },
            },
        )

    def thread_resume(self, thread_id: str) -> dict[str, Any]:
        return self._request("thread/resume", {"threadId": thread_id})

    def thread_read(self, thread_id: str) -> dict[str, Any]:
        return self._request(
            "thread/read", {"threadId": thread_id, "includeTurns": True}
        )

    def thread_archive(self, thread_id: str) -> dict[str, Any]:
        return self._request("thread/archive", {"threadId": thread_id})

    def thread_fork(self, thread_id: str) -> dict[str, Any]:
        return self._request("thread/fork", {"threadId": thread_id})

    def thread_compact(self, thread_id: str) -> dict[str, Any]:
        return self._request("thread/compact/start", {"threadId": thread_id})

    def turn_start(self, thread_id: str, text: str) -> dict[str, Any]:
        return self._request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": text}],
            },
        )
