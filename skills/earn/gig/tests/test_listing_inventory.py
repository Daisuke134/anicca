#!/usr/bin/env python3
"""Deterministic-parts tests for listing_inventory.py (gig-loop spec Task C1).

Fixtures are real captures (read-only) from the live coconala.com/mypage/services_lists
page and one live services/<id> page, taken 2026-08-09 via the loop's own browser lease.
No network, no browser needed to run these.
"""
import asyncio
import json
import stat
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import listing_inventory as li  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_extract_own_service_ids_dedupes_and_keeps_order():
    hrefs = [
        "/mypage/services_lists", "/services/add",
        "/services/111", "/mypage/services/111", "/services/archive/111",
        "/services/222", "/mypage/services/222", "/services/archive/222",
    ]
    assert li.extract_own_service_ids(hrefs) == ["111", "222"]


def test_parse_list_page_page1_matches_known_ledger_titles():
    data = _load_fixture("services_lists_page1.json")
    hrefs_probe_ids = [
        "94000015", "94000022", "94000007", "94000017", "94000016",
        "94000014", "94000009", "94000018", "94000021", "94000010",
    ]
    cards = li.parse_list_page(data["rendered_text"], hrefs_probe_ids)
    assert len(cards) == 10
    # id->href alignment was hand-verified against the shuppin.jsonl ledger for these two:
    # 94000015's last ledger title starts with "研修" (PowerPoint listing); 94000022's with
    # "SNS投稿の公開前チェックリスト" -- both are exactly what the fixture's first two
    # cards say.
    assert cards[0]["service_id"] == "94000015"
    assert cards[0]["title"].startswith("研修資料をPowerPointで見やすくします")
    assert cards[0]["price_jpy"] == 5000
    assert cards[0]["state"] == "公開中"
    assert cards[1]["service_id"] == "94000022"
    assert cards[1]["title"].startswith("SNS投稿の公開前チェックリストを整えます")
    # This is the finding the C1 gate exists to surface: a live listing soliciting
    # real-footage video editing, the account's documented no-go (coconala.md "## 応募").
    assert cards[2]["service_id"] == "94000007"
    assert "動画" in cards[2]["title"] and "編集" in cards[2]["title"]


def test_parse_list_page_page2_single_card():
    data = _load_fixture("services_lists_page2.json")
    cards = li.parse_list_page(data["rendered_text"], ["94000008"])
    assert len(cards) == 1
    assert cards[0]["service_id"] == "94000008"
    assert cards[0]["price_jpy"] == 5000
    assert cards[0]["state"] == "公開中"


def test_parse_category_breadcrumb_real_page():
    text = (
        "1/6\nホーム\nビジネス代行・事務代行\n資料・企画書作成\nプレゼン資料作成\n"
        "研修資料をPowerPointで見やすくします\n実納品・入金済みの教育資料実務を基に対応\n"
        "評価  -\n販売実績 0件\n"
    )
    assert li.parse_category_breadcrumb(text) == "ビジネス代行・事務代行/資料・企画書作成/プレゼン資料作成"


def test_parse_category_breadcrumb_two_level():
    text = "ホーム\n生成AI活用・開発・制作\nAI導入・活用支援\nタイトル\nキャッチ\n評価  -\n"
    assert li.parse_category_breadcrumb(text) == "生成AI活用・開発・制作/AI導入・活用支援"


def test_parse_category_breadcrumb_missing_markers_returns_none():
    assert li.parse_category_breadcrumb("no breadcrumb here") is None


def test_parse_sales_count_keeps_missing_or_malformed_values_unknown():
    assert li.parse_sales_count("評価 -\n販売実績 12件\n") == 12
    assert li.parse_sales_count("評価 -\n販売実績 1,234件\n") == 1234
    assert li.parse_sales_count("評価 -\n販売実績 件\n") is None
    assert li.parse_sales_count("評価 -\n販売実績 非公開\n") is None
    assert li.parse_sales_count("評価 -\n") is None


def test_public_service_scope_stops_before_profile_and_recommendations():
    own = "ホーム\nIT相談\n自分の商品\nサービス内容\nOpenCV PoC\n20,000 円\n"
    tail = "あなたのサービスを宣伝しましょう\n競馬bot\nおすすめWebシステム"
    assert li.extract_public_service_scope(own + li.SERVICE_SCOPE_END + "\n" + tail) == own.strip()
    assert li.extract_public_service_scope(own) is None
    assert li.extract_public_service_scope(own + li.SERVICE_SCOPE_END + li.SERVICE_SCOPE_END) is None


def test_write_storefront_observation_is_private_atomic_and_content_hashed(tmp_path):
    inventory = [
        {
            "service_id": "222",
            "title": "買い手本文は保存しない",
            "category": "秘密カテゴリ",
            "body": "buyer text https://example.invalid/credential",
            "state": "公開中",
            "price_jpy": 5000,
            "sales_count": 3,
        },
        {
            "service_id": "111",
            "title": "別タイトル",
            "category": "別カテゴリ",
            "state": "非公開",
            "price_jpy": None,
            "sales_count": None,
        },
    ]
    output = tmp_path / "storefront-observation.json"

    first = li.write_storefront_observation(
        inventory, output_path=output, observed_at="2026-08-10T12:00:00+00:00"
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert payload == first
    assert payload["live_listings_count"] == 1
    assert payload["service_count"] == 2
    assert payload["services"] == [
        {"service_id": "111", "state": "非公開", "price_jpy": None, "sales_count": None},
        {"service_id": "222", "state": "公開中", "price_jpy": 5000, "sales_count": 3},
    ]
    serialized = output.read_text(encoding="utf-8")
    for forbidden in ("買い手本文", "秘密カテゴリ", "buyer text", "example.invalid", "credential", "別タイトル"):
        assert forbidden not in serialized
    assert not list(tmp_path.glob("*.tmp"))

    second = li.write_storefront_observation(
        list(reversed(inventory)), output_path=output, observed_at="2026-08-10T13:00:00+00:00"
    )
    assert second["content_sha256"] == first["content_sha256"]
    assert second["observed_at"] != first["observed_at"]


def test_cross_reference_ledger_reads_real_state_dir(tmp_path, monkeypatch):
    ledger = tmp_path / "shuppin.jsonl"
    ledger.write_text(
        "\n".join([
            json.dumps({"action": "shuppin_published", "service_id": "111"}),
            json.dumps({"action": "shuppin_published", "service_id": "222"}),
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(li, "STATE_DIR", tmp_path)
    result = li.cross_reference_ledger(["111", "333"])
    assert result["ledger_published_listings_count"] == 2
    assert result["ledger_claims_published_but_not_live_now"] == ["222"]
    assert result["live_now_but_ledger_never_recorded_shuppin_published"] == ["333"]


def test_new_cards_only_drops_repeats_from_a_clamped_page():
    # Real 2026-08-09 behaviour: /mypage/services_lists/page:3 clamped back onto
    # page:2's single card instead of 404ing or returning empty.
    page2 = [{"service_id": "94000008", "title": "x"}]
    page3_clamped = [{"service_id": "94000008", "title": "x"}]
    seen = {c["service_id"] for c in page2}
    assert li.new_cards_only(page3_clamped, seen) == []


def test_new_cards_only_keeps_unseen_ids():
    seen = {"111"}
    cards = [{"service_id": "111"}, {"service_id": "222"}]
    assert [c["service_id"] for c in li.new_cards_only(cards, seen)] == ["222"]


def test_leased_collection_uses_one_target_and_stops_at_first_repeated_page(monkeypatch):
    pages = []
    details = []

    async def page(_base, number, *, ws_url=None):
        pages.append((number, ws_url))
        if number == 1:
            return ["/services/111"], "公開中\nfirst\n1,000\n円\n編集する 公開設定 シェア"
        return ["/services/111"], "公開中\nfirst\n1,000\n円\n編集する 公開設定 シェア"

    async def detail(_base, service_id, *, ws_url=None):
        details.append((service_id, ws_url))
        return {"category": "category", "sales_count": 1}

    monkeypatch.setattr(li, "_fetch_list_page", page)
    monkeypatch.setattr(li, "_fetch_category", detail)
    rows = asyncio.run(li.collect_live(ws_url="ws://127.0.0.1:9223/devtools/page/storefront"))

    assert [row["service_id"] for row in rows] == ["111"]
    assert pages == [(1, "ws://127.0.0.1:9223/devtools/page/storefront"),
                     (2, "ws://127.0.0.1:9223/devtools/page/storefront")]
    assert details == [("111", "ws://127.0.0.1:9223/devtools/page/storefront")]
    assert not hasattr(li, "listing_ledger")


def test_build_fit_judgment_context_carries_known_no_go_and_listings():
    inventory = [{"service_id": "94000007", "title": "動画編集"}]
    ctx = li.build_fit_judgment_context(inventory)
    assert ctx["listings"] == inventory
    assert any("実写動画" in item for item in ctx["known_no_go"])
    assert "results" in ctx["output_schema"]


if __name__ == "__main__":
    import subprocess
    sys.exit(subprocess.run([sys.executable, "-m", "pytest", __file__, "-q"]).returncode)
