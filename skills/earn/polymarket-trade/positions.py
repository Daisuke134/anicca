#!/usr/bin/env python3
"""positions.py — parse_positions_response(json_text) -> list[dict] (REQ-LV-017). Normalizes
data-api.polymarket.com/positions JSON (same shape redeem.py already parses) into
{market, size, redeemable} rows. Fail-closed like redeem.py's other parsers: malformed input -> [],
never crash, never fabricate a value for a missing field.
"""
import json


def parse_positions_response(json_text):
    try:
        data = json.loads(json_text)
    except Exception:
        return []
    if not isinstance(data, list):
        return []
    out = []
    for item in data:
        if not isinstance(item, dict):
            continue
        out.append({
            "market": item.get("title"),
            "size": item.get("currentValue"),
            "redeemable": item.get("redeemable"),
        })
    return out
