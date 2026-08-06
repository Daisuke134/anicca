from __future__ import annotations

import hashlib
import json
import subprocess
from typing import Any, Callable


class GogApplicationTransport:
    def __init__(
        self,
        *,
        account: str,
        subject: str,
        executable: str = "/opt/homebrew/bin/gog",
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ):
        if not account.strip() or not subject.strip():
            raise ValueError("Gmail account and subject are required")
        self.account = account.strip()
        self.subject = subject.strip()
        self.executable = executable
        self.runner = runner

    def __call__(
        self,
        *,
        recipient: str,
        route_kind: str,
        message_path: str,
        resume_path: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if route_kind not in {"recruiting_email", "recruiting_outreach"}:
            raise ValueError("Gmail transport route kind is invalid")
        argv = [
            self.executable,
            "gmail",
            "send",
            "--account",
            self.account,
            "--json",
            "--no-input",
            "--to",
            recipient,
            "--subject",
            self.subject,
            "--body-file",
            message_path,
            "--attach",
            resume_path,
        ]
        completed = self.runner(
            argv,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"Gmail application transport failed rc={completed.returncode}")
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError("Gmail application ACK is invalid JSON") from error
        message_id = (
            value.get("messageId")
            or value.get("id")
            or (value.get("message") or {}).get("id")
        )
        if not isinstance(message_id, str) or not message_id.strip():
            raise RuntimeError("Gmail application ACK has no message ID")
        evidence = json.dumps(
            {
                "idempotency_key": idempotency_key,
                "message_id": message_id,
                "route_kind": route_kind,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return {
            "status": "delivered",
            "provider_id": f"gmail:{message_id}",
            "evidence_sha256": hashlib.sha256(evidence.encode("utf-8")).hexdigest(),
        }
