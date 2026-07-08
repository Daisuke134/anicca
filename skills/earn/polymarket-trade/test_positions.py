"""test_positions.py — RED (Phase 2a, feature claude-p-loop-verification).
PROP-LV-006 / REQ-LV-017 — parse_positions_response(json_text) -> list[dict], each shaped
{market, size, redeemable}. Pure: normalizes the data-api.polymarket.com/positions JSON (same
response shape redeem.py already parses, e.g. {"conditionId":..., "title":..., "currentValue":...,
"redeemable":...} — see redeem.py's dedupe_redeemable_conditions() fixtures for the real shape).
Fail-closed like redeem.py's other parsers: malformed input -> [] (never crash, never fabricate).

positions.py does not exist yet -> ImportError -> RED.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from positions import parse_positions_response  # RED: does not exist yet

P = 0
F = 0


def chk(name, got, want):
    global P, F
    if got == want:
        print(f"  ok {name} ({got})")
        P += 1
    else:
        print(f"  FAIL {name} want={want} got={got}")
        F += 1


# real shape from data-api.polymarket.com/positions (matches redeem.py's own fixtures)
multi = json.dumps([
    {"conditionId": "0xc8a0", "title": "Wimbledon Men's Final", "currentValue": 10.0, "redeemable": True},
    {"conditionId": "0xabc1", "title": "US Election 2028", "currentValue": 2.5, "redeemable": False},
])
chk("正常な複数ポジションJSON -> 件数一致のlist[dict]",
    parse_positions_response(multi),
    [
        {"market": "Wimbledon Men's Final", "size": 10.0, "redeemable": True},
        {"market": "US Election 2028", "size": 2.5, "redeemable": False},
    ])

chk("空配列レスポンス -> []", parse_positions_response("[]"), [])

chk("不正JSON -> [] (クラッシュしない, redeem.pyのfail-closed方針と一致)",
    parse_positions_response("{not valid json"), [])

chk("空文字列 -> []", parse_positions_response(""), [])

# a position missing currentValue/redeemable entirely -> skipped, not crashed, not fabricated
partial = json.dumps([{"conditionId": "0xdead", "title": "Broken row"}])
result = parse_positions_response(partial)
chk("欠損フィールドのrowはクラッシュせず処理される (skip or None, list is still valid)",
    isinstance(result, list), True)

print(f"=== test_positions: {P} passed {F} failed ===")
sys.exit(0 if F == 0 else 1)
