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


def parse_positions_by_token(json_text):
    """parse_positions_by_token(json_text) -> list[dict] (SPEC-no-naked-fills R1). Normalizes the
    SAME data-api.polymarket.com/positions JSON into PER-TOKEN rows
    {asset, market, conditionId, size} so callers can detect naked single-leg holdings (one
    outcome token held, its sibling not). `size` is the SHARE count (data-api `size`), a float.
    Fail-closed like parse_positions_response: malformed input -> [], never crash, never fabricate
    a value for a missing field (missing `asset` -> row skipped; missing `size` -> 0.0)."""
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
        asset = item.get("asset")
        if asset is None:
            continue
        try:
            size = float(item.get("size") or 0.0)
        except (TypeError, ValueError):
            size = 0.0
        out.append({
            "asset": str(asset),
            "market": item.get("title"),
            "conditionId": item.get("conditionId"),
            "size": size,
        })
    return out
