#!/usr/bin/env python3
"""Optional owner email transport using the owner's authenticated gog Gmail."""

from __future__ import annotations

import hashlib
import os
import subprocess
from email.utils import parseaddr
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
    account = os.environ.get("GIG_GOG_ACCOUNT", "").strip()
    if not account or parseaddr(account)[1] != account:
        raise RuntimeError("owner_gog_account_invalid")
    digest = hashlib.sha256(event_key.encode("utf-8")).hexdigest()
    completed = run(
        [os.environ.get("GIG_GOG_BIN", "/opt/homebrew/bin/gog"), "--account", account,
         "gmail", "send", f"--to={target}",
         "--subject=[Mr.bot] Coconala update", f"--body={message}\n\nreceipt:{digest}",
         "--json", "--no-input"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"owner_email_transport_failed:{completed.returncode}")
    return f"email:{digest}"
