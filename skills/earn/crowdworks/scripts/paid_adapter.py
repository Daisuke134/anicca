#!/usr/bin/env python3
"""Thin CrowdWorks boundary for the shared marketplace Paid kernel."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from typing import Any, Callable, Mapping
from urllib.parse import parse_qs, urlsplit


HERE = Path(__file__).resolve().parent
ACTIVE_CONTRACTS_URL = "https://crowdworks.jp/e/contracts?status=active"
EMPTY_SELECTORS = (
    "div.hourly.section div.nodata",
    "div.fixed_price.section div.nodata",
    "div.competition.section div.nodata",
)


class CrowdWorksPaidWait(RuntimeError):
    def __init__(self, reason: str, remaining_work: list[str]):
        super().__init__(reason)
        self.paid_wait_reason = reason
        self.paid_remaining_work = remaining_work


def _load_account():
    path = HERE / "account.py"
    spec = importlib.util.spec_from_file_location("crowdworks_paid_account", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("crowdworks_paid_account_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _text(value: Any) -> str:
    return " ".join(value.split()) if isinstance(value, str) else ""


def read_only_inventory() -> dict[str, Any]:
    """Read the official active-contract surface without starting or repairing a browser."""
    account = _load_account()
    page = None
    try:
        browser = account._browser(account.CDP_URL)
        contexts = getattr(browser, "contexts", ())
        if len(contexts) != 1:
            raise RuntimeError("crowdworks_paid_browser_unavailable")
        page = contexts[0].new_page()
        page.goto(ACTIVE_CONTRACTS_URL, wait_until="domcontentloaded", timeout=20_000)
        parsed = urlsplit(str(page.url))
        if ((parsed.scheme, parsed.hostname, parsed.path) != ("https", "crowdworks.jp", "/e/contracts")
                or parse_qs(parsed.query) != {"status": ["active"]} or parsed.fragment):
            raise RuntimeError("crowdworks_paid_contract_source_unavailable")
        empty = []
        for selector in EMPTY_SELECTORS:
            node = page.locator(selector)
            empty.append(node.count() == 1 and _text(node.inner_text()) == "契約がありません。")
        if all(empty):
            return {
                "ok": True,
                "source_complete": True,
                "contract_candidates": [],
                "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            }
        raise CrowdWorksPaidWait(
            "official_contract_detail_required",
            ["normalize the first official active contract before authorizing work or delivery"],
        )
    finally:
        if page is not None:
            try:
                page.close()
            except Exception:
                pass


class CrowdWorksPaidAdapter:
    def __init__(self, *, account_id: str, inventory_reader: Callable[[], Mapping[str, Any]]):
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("crowdworks_account_id_invalid")
        self.account_id = account_id.strip()
        self.inventory_reader = inventory_reader

    def observe_active(self) -> list[dict[str, Any]]:
        snapshot = self.inventory_reader()
        if (not isinstance(snapshot, Mapping) or snapshot.get("ok") is not True
                or snapshot.get("source_complete") is not True
                or not isinstance(snapshot.get("contract_candidates"), list)):
            raise RuntimeError("crowdworks_paid_inventory_unavailable")
        if snapshot["contract_candidates"]:
            raise CrowdWorksPaidWait(
                "official_contract_detail_required",
                ["normalize the first official active contract before authorizing work or delivery"],
            )
        return []

    def observe_one(self, work_id: str) -> dict[str, Any]:
        raise RuntimeError("crowdworks_paid_work_unavailable")

    def context(self, work_id: str) -> dict[str, Any]:
        raise RuntimeError("crowdworks_paid_work_unavailable")

    def mutate(self, intent: dict[str, Any]) -> None:
        raise RuntimeError("crowdworks_paid_effect_not_implemented")

    def readback(self, intent: dict[str, Any]) -> dict[str, Any]:
        return {"verified": False, "authoritative_absent": False}


def decide(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "action": "wait",
        "reason": "official_contract_detail_required",
        "remaining_work": ["read funded contract terms and complete buyer context"],
    }


def build(argv: list[str]):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account-id", required=True)
    args = parser.parse_args(argv)
    return CrowdWorksPaidAdapter(account_id=args.account_id, inventory_reader=read_only_inventory), decide


__all__ = ["CrowdWorksPaidAdapter", "CrowdWorksPaidWait", "build", "decide", "read_only_inventory"]
