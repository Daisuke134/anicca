from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any
from urllib.parse import urlparse

from .contracts import SessionHandleV1


Connector = Callable[[str], Awaitable[Any]]


class BrowserSession:
    """Own one tagged row page inside the existing authenticated CDP browser."""

    def __init__(self, connector: Connector | None = None) -> None:
        self._connector = connector
        self._drivers: list[Any] = []
        self._pages: dict[str, Any] = {}

    @staticmethod
    def _validate_endpoint(endpoint: str) -> str:
        value = endpoint.rstrip("/")
        parsed = urlparse(value)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.port != 9222
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("BrowserSession may attach only to local CDP :9222")
        return value

    async def _connect(self, endpoint: str) -> Any:
        if self._connector is not None:
            return await self._connector(endpoint)
        from playwright.async_api import async_playwright

        driver = await async_playwright().start()
        self._drivers.append(driver)
        return await driver.chromium.connect_over_cdp(endpoint)

    @staticmethod
    async def _marker(page: Any) -> str | None:
        try:
            value = await page.evaluate("() => window.name")
        except Exception:
            return None
        return value if isinstance(value, str) else None

    async def _recover_or_create(self, browser: Any, marker: str) -> tuple[Any, bool]:
        if not browser.contexts:
            raise RuntimeError("existing CDP owner has no default browser context")
        context = browser.contexts[0]
        for page in context.pages:
            if not page.is_closed() and await self._marker(page) == marker:
                return page, True
        page = await context.new_page()
        await page.evaluate("marker => { window.name = marker }", marker)
        return page, False

    async def attach(self, endpoint: str, row_run_id: str) -> SessionHandleV1:
        endpoint = self._validate_endpoint(endpoint)
        if not row_run_id:
            raise ValueError("row_run_id is required")
        marker = f"anicca-job-search:{row_run_id}"
        browser = await self._connect(endpoint)
        recovered = await self._recover_or_create(browser, marker)
        page = recovered[0] if isinstance(recovered, tuple) else recovered
        self._pages[marker] = page
        return SessionHandleV1(1, endpoint, row_run_id, marker, 1)

    async def reconnect(self, handle: SessionHandleV1) -> SessionHandleV1:
        endpoint = self._validate_endpoint(handle.endpoint)
        page = self._pages.get(handle.page_marker)
        if page is not None and not page.is_closed():
            return handle
        browser = await self._connect(endpoint)
        recovered = await self._recover_or_create(browser, handle.page_marker)
        page = recovered[0] if isinstance(recovered, tuple) else recovered
        self._pages[handle.page_marker] = page
        return SessionHandleV1(
            1,
            endpoint,
            handle.row_run_id,
            handle.page_marker,
            handle.generation + 1,
        )

    async def resume(self, handle: SessionHandleV1) -> tuple[SessionHandleV1, bool]:
        endpoint = self._validate_endpoint(handle.endpoint)
        browser = await self._connect(endpoint)
        page, recovered = await self._recover_or_create(browser, handle.page_marker)
        self._pages[handle.page_marker] = page
        return (
            SessionHandleV1(
                1, endpoint, handle.row_run_id, handle.page_marker, handle.generation + 1
            ),
            recovered,
        )

    async def close_owned(self, handle: SessionHandleV1) -> None:
        page = self._pages.pop(handle.page_marker, None)
        if page is None or page.is_closed():
            return
        if await self._marker(page) != handle.page_marker:
            raise RuntimeError("refusing to close a page not owned by this row")
        await page.close()

    def page(self, handle: SessionHandleV1) -> Any:
        page = self._pages.get(handle.page_marker)
        if page is None or page.is_closed():
            raise RuntimeError("row page is not attached")
        return page
