#!/usr/bin/env python3
"""Optional owner email transport using the machine's sendmail-compatible binary."""

from __future__ import annotations

import hashlib
import os
import subprocess
from email.message import EmailMessage
from email.utils import parseaddr
from pathlib import Path
from typing import Any, Callable


def send_email_if_configured(
    message: str,
    *,
    event_key: str,
    run: Callable[..., Any] = subprocess.run,
) -> str | None:
    target = os.environ.get("GIG_NOTIFY_EMAIL", "").strip()
    if not target:
        return None
    if "\n" in target or "\r" in target or parseaddr(target)[1] != target:
        raise RuntimeError("owner_email_invalid")
    sender = os.environ.get("GIG_NOTIFY_FROM", "").strip() or target
    if "\n" in sender or "\r" in sender or parseaddr(sender)[1] != sender:
        raise RuntimeError("owner_email_sender_invalid")
    executable = Path(os.environ.get("GIG_SENDMAIL", "/usr/sbin/sendmail"))
    mail = EmailMessage()
    mail["To"] = target
    mail["From"] = sender
    mail["Subject"] = "[Life Manager] Coconala update"
    digest = hashlib.sha256(event_key.encode("utf-8")).hexdigest()
    mail["Message-ID"] = f"<{digest}@life-manager.local>"
    mail.set_content(message)
    completed = run(
        [str(executable), "-t"], input=mail.as_bytes(), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=60, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"owner_email_transport_failed:{completed.returncode}")
    return f"email:{digest}"
