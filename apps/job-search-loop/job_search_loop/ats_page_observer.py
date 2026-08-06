"""Read-only ATS observation on the resident's already-leased CloakBrowser."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .ats_page_classifier import classify_ats_page
from .playwright_ats import capture_snapshot


def _current_http_page(browser: Any) -> Any:
    for context in reversed(list(browser.contexts)):
        for page in reversed(list(context.pages)):
            if urlsplit(str(page.url)).scheme in {"http", "https"}:
                return page
    raise RuntimeError("resident CloakBrowser has no current HTTP(S) page")


def observe_current_page(
    owner_receipt: Mapping[str, Any],
    *,
    playwright: Any,
    snapshotter: Callable[..., dict[str, Any]] = capture_snapshot,
) -> dict[str, Any]:
    if owner_receipt.get("status") != "ready":
        raise ValueError("browser owner is not ready")
    endpoint = str(owner_receipt.get("endpoint") or "")
    parsed = urlsplit(endpoint)
    if parsed.scheme not in {"http", "ws"} or parsed.hostname not in {
        "127.0.0.1", "localhost", "::1",
    }:
        raise ValueError("browser owner endpoint must be loopback")
    lease_id = owner_receipt.get("lease_id")
    fence = owner_receipt.get("fence")
    if not isinstance(lease_id, str) or not lease_id:
        raise ValueError("browser owner lease is missing")
    if isinstance(fence, bool) or not isinstance(fence, int) or fence <= 0:
        raise ValueError("browser owner fence is missing")
    browser = playwright.chromium.connect_over_cdp(endpoint)
    snapshot = snapshotter(_current_http_page(browser), navigation_committed=True)
    return {
        "version": 1,
        "owner_lease_id": lease_id,
        "owner_fence": fence,
        "snapshot": snapshot,
        "classification": classify_ats_page(snapshot),
        "browser_action_count": 0,
    }


def _write_private(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    owner = json.loads(args.owner_receipt.read_text(encoding="utf-8"))
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        receipt = observe_current_page(owner, playwright=playwright)
    _write_private(args.output, receipt)
    classification = receipt["classification"]
    print(json.dumps({
        "status": "observed",
        "classification": classification["classification"],
        "next_route": classification["next_route"],
        "application_confirmed": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
