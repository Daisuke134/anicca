"""Fail-closed Browser Use boundary for the resident Job Hunter browser owner."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
from importlib import metadata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class BrowserUsePolicyError(RuntimeError):
    pass


class _AsyncBridge:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
        self.thread.start()

    def run(self, awaitable: Any) -> Any:
        return asyncio.run_coroutine_threadsafe(awaitable, self.loop).result(timeout=60)

    def close(self) -> None:
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=5)
        self.loop.close()


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
        self.allowed_domains = tuple(item.lower() for item in allowed_domains)
        self._bridge: _AsyncBridge | None = None

    def connect(self) -> None:
        if self._bridge is not None:
            raise BrowserUsePolicyError("Browser Use backend is already connected")
        self._bridge = _AsyncBridge()
        try:
            self._bridge.run(self.session.start())
        except Exception:
            self._bridge.close()
            self._bridge = None
            raise

    def _run(self, awaitable: Any) -> Any:
        if self._bridge is None:
            raise BrowserUsePolicyError("Browser Use backend is not connected")
        return self._bridge.run(awaitable)

    def _allowed_url(self, url: str) -> None:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in self.allowed_domains
        ):
            raise BrowserUsePolicyError("navigation URL is outside the official-domain allowlist")

    def navigate(self, url: str) -> None:
        self._allowed_url(url)
        self._run(self.session.navigate_to(url))

    def _page(self) -> Any:
        page = self._run(self.session.get_current_page())
        if page is None:
            raise BrowserUsePolicyError("Browser Use current page is missing")
        return page

    def snapshot(self) -> dict[str, Any]:
        page = self._page()
        script = """() => JSON.stringify(Array.from(document.querySelectorAll(
          'input, textarea, select, button, a, [role=button], [role=alert], [role=status]'
        )).map(n => ({
          tag: (n.tagName || '').toLowerCase(),
          type: n.getAttribute('type') || '',
          role: n.getAttribute('role') || '',
          label: n.getAttribute('aria-label') || n.getAttribute('placeholder') || '',
          name: n.getAttribute('name') || '',
          text: (n.innerText || n.textContent || '').replace(/\\s+/g, ' ').trim(),
          group_label: '',
          required: Boolean(n.required) || n.getAttribute('aria-required') === 'true'
        })))"""
        controls = json.loads(self._run(page.evaluate(script)))
        return {
            "version": 1,
            "url": self._run(page.get_url()) if hasattr(page, "get_url") else "",
            "navigation_committed": True,
            "frames": [{"url": "", "controls": controls}],
        }

    def _element(self, frame_index: int, control_index: int) -> Any:
        if frame_index != 0:
            raise BrowserUsePolicyError("Browser Use adapter does not authorize cross-origin frame access")
        if isinstance(control_index, bool) or not isinstance(control_index, int) or control_index < 0:
            raise BrowserUsePolicyError("Browser Use control index is invalid")
        elements = self._run(self._page().get_elements_by_css_selector(
            "input, textarea, select, button, a, [role=button], [role=alert], [role=status]"
        ))
        if control_index >= len(elements):
            raise BrowserUsePolicyError("Browser Use control index is stale")
        return elements[control_index]

    def fill(self, frame_index: int, control_index: int, value: str) -> None:
        self._run(self._element(frame_index, control_index).fill(value))

    def read_value(self, frame_index: int, control_index: int) -> str:
        return str(self._run(self._element(frame_index, control_index).evaluate("() => this.value")))

    def upload(self, frame_index: int, control_index: int, path: str) -> None:
        file_path = Path(path)
        if not file_path.is_file():
            raise BrowserUsePolicyError("Browser Use upload file is missing")
        element = self._element(frame_index, control_index)
        backend_node_id = getattr(element, "_backend_node_id", None)
        session_id = getattr(element, "_session_id", None)
        client = getattr(element, "_client", None)
        if not isinstance(backend_node_id, int) or not session_id or client is None:
            raise BrowserUsePolicyError("pinned Browser Use upload contract changed")
        self._run(
            client.send.DOM.setFileInputFiles(
                params={"files": [str(file_path)], "backendNodeId": backend_node_id},
                session_id=session_id,
            )
        )

    def upload_matches(self, frame_index: int, control_index: int, path: str) -> bool:
        value = self.read_value(frame_index, control_index)
        return Path(value.replace("\\", "/")).name == Path(path).name

    def screenshot(self) -> bytes:
        value = self._run(self.session.take_screenshot())
        if not isinstance(value, bytes):
            raise BrowserUsePolicyError("Browser Use screenshot did not return bytes")
        return value

    def close(self) -> None:
        if self._bridge is None:
            return
        bridge = self._bridge
        try:
            bridge.run(self.session.stop())
        finally:
            self._bridge = None
            bridge.close()


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

    def screenshot(self, path: str) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        value = self.perform("screenshot")
        if not isinstance(value, bytes) or not value:
            raise BrowserUsePolicyError("Browser Use screenshot is empty")
        destination.write_bytes(value)
        os.chmod(destination, 0o600)
