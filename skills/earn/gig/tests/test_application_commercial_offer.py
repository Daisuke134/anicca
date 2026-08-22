from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import inspect
import sys


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("application_parent", SCRIPTS / "application_parent.py")
assert SPEC and SPEC.loader
application_parent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(application_parent)


def test_source_navigation_reuses_the_bounded_timeout_retry(monkeypatch) -> None:
    effects = object.__new__(application_parent.CdpParentEffects)
    effects.ws_url = "ws://example.invalid/devtools/page/1"
    calls = {"retry": 0}

    class Connection:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *_args):
            return None

    async def call(_ws, _method, _params, _call_id):
        return {}

    async def retry(_ws, _url, _call_id):
        calls["retry"] += 1
        return 3

    async def plain_navigation(*_args):
        raise AssertionError("source navigation must use the bounded retry path")

    async def evaluate(_ws, _expression, call_id):
        return {
            "url": "https://coconala.com/requests/categories/1",
            "title": "requests",
            "text": "",
            "hrefs": [],
            "next_href": None,
            "access_denied": False,
            "not_found": False,
        }, call_id + 1

    async def screenshot(_ws, call_id):
        return b"png", call_id + 1

    monkeypatch.setattr(
        application_parent.websockets, "connect", lambda *_args, **_kwargs: Connection()
    )
    monkeypatch.setattr(effects, "_call", call)
    monkeypatch.setattr(effects, "_navigate_retry_once", retry)
    monkeypatch.setattr(effects, "_navigate", plain_navigation)
    monkeypatch.setattr(effects, "_eval_json", evaluate)
    monkeypatch.setattr(effects, "_screenshot", screenshot)

    page, screenshot_bytes = asyncio.run(
        effects._source_async("source", "https://coconala.com/requests/categories/1")
    )

    assert calls == {"retry": 1}
    assert page["title"] == "requests"
    assert screenshot_bytes == b"png"


def test_commercial_offer_preserves_planner_price() -> None:
    detail = {"budget_min_jpy": 10_000, "budget_max_jpy": 30_000}

    assert application_parent.commercial_offer_price(detail, planner_price_jpy=15_000) == 15_000


def test_application_does_not_navigate_competitor_profiles() -> None:
    source = inspect.getsource(application_parent.CdpParentEffects._detail_async)

    assert "coconala.com/users/" not in source


def test_confirmed_application_records_pricing_version() -> None:
    row = application_parent._application_row(
        {
            "request_id": "123",
            "category": "IT・プログラミング",
            "title": "自動化",
            "canonical_url": "https://coconala.com/requests/123",
        },
        {"price_jpy": 45_000, "deliver_date": "2026-08-20"},
    )

    assert row["pricing_basis"] == "planner_selected_v1"


def test_proposal_opens_with_commitment_and_has_no_pre_contract_question() -> None:
    proposal = application_parent.commercial_proposal_text(
        "詳細をご共有いただけますか？要件に沿ってLINE Botを構築します。",
        price_jpy=99_000,
        deliver_date="2026-08-20",
    )

    assert proposal.startswith("対応可能です。")
    assert "？" not in proposal and "?" not in proposal
    assert "99,000円" in proposal
    assert "2026-08-20" in proposal
    assert "契約範囲内でご納得いただけるまで" in proposal
