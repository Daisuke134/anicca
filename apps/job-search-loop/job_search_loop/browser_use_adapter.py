"""Fail-closed Browser Use boundary for the resident Job Hunter browser owner."""

from __future__ import annotations

import hashlib
import os
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class BrowserUsePolicyError(RuntimeError):
    pass


class PinnedBrowserUseBackend:
    """Construct the exact pinned Browser Use session on the local owner endpoint."""

    package = "browser-use"
    pinned_version = "0.13.7"

    def __init__(
        self,
        endpoint: str,
        *,
        allowed_domains: list[str],
        version_getter: Any = metadata.version,
        session_factory: Any = None,
    ):
        parsed = urlparse(endpoint)
        if parsed.scheme not in {"http", "ws"} or parsed.hostname not in {
            "127.0.0.1",
            "localhost",
            "::1",
        }:
            raise BrowserUsePolicyError("Browser Use CDP endpoint must be loopback")
        if not allowed_domains or any(not isinstance(item, str) or not item for item in allowed_domains):
            raise BrowserUsePolicyError("Browser Use allowed domains are required")
        installed = version_getter(self.package)
        if installed != self.pinned_version:
            raise BrowserUsePolicyError(
                f"Browser Use pinned version {self.pinned_version} is required; got {installed}"
            )
        if session_factory is None:
            from browser_use import BrowserSession

            session_factory = BrowserSession
        self.session = session_factory(
            cdp_url=endpoint,
            is_local=True,
            allowed_domains=list(allowed_domains),
            captcha_solver=False,
            keep_alive=True,
        )


class AuthorizedBrowserUseAdapter:
    """Expose Browser Use only for deterministic pre-submit browser operations."""

    authorized_actions = frozenset(
        {"navigate", "snapshot", "fill", "read_value", "upload", "upload_matches", "screenshot"}
    )
    evidence_stages = frozenset({"before", "after", "terminal"})

    def __init__(self, backend: Any, *, owner_receipt: dict[str, Any]):
        lease_id = owner_receipt.get("lease_id")
        fence = owner_receipt.get("fence")
        holder_pid = owner_receipt.get("holder_pid")
        if not isinstance(lease_id, str) or not lease_id:
            raise BrowserUsePolicyError("browser owner lease is required")
        if isinstance(fence, bool) or not isinstance(fence, int) or fence <= 0:
            raise BrowserUsePolicyError("browser owner fence is required")
        if isinstance(holder_pid, bool) or not isinstance(holder_pid, int) or holder_pid <= 0:
            raise BrowserUsePolicyError("browser owner holder is required")
        self.backend = backend
        self.lease_id = lease_id
        self.fence = fence
        self.holder_pid = holder_pid

    def perform(self, action: str, *arguments: Any) -> Any:
        if action not in self.authorized_actions:
            raise BrowserUsePolicyError(f"Browser Use action is not authorized: {action}")
        operation = getattr(self.backend, action, None)
        if not callable(operation):
            raise BrowserUsePolicyError(f"Browser Use backend does not implement: {action}")
        return operation(*arguments)

    def navigate(self, url: str) -> None:
        self.perform("navigate", url)

    def snapshot(self) -> dict[str, Any]:
        return self.perform("snapshot")

    def fill(self, frame_index: int, control_index: int, value: str) -> None:
        self.perform("fill", frame_index, control_index, value)

    def read_value(self, frame_index: int, control_index: int) -> str:
        return self.perform("read_value", frame_index, control_index)

    def upload(self, frame_index: int, control_index: int, path: str) -> None:
        self.perform("upload", frame_index, control_index, path)

    def upload_matches(self, frame_index: int, control_index: int, path: str) -> bool:
        return bool(self.perform("upload_matches", frame_index, control_index, path))

    def capture_evidence(self, stage: str, directory: Path) -> dict[str, Any]:
        if stage not in self.evidence_stages:
            raise BrowserUsePolicyError(f"unsupported evidence stage: {stage}")
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = directory / f"browser-use-{self.lease_id}-{self.fence}-{stage}.png"
        temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
        try:
            screenshot = self.perform("screenshot")
            if not isinstance(screenshot, bytes) or not screenshot:
                raise BrowserUsePolicyError("Browser Use screenshot is empty")
            temporary.write_bytes(screenshot)
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
            os.chmod(path, 0o600)
        finally:
            temporary.unlink(missing_ok=True)
        return {
            "stage": stage,
            "path": str(path),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "lease_id": self.lease_id,
            "fence": self.fence,
            "holder_pid": self.holder_pid,
        }
