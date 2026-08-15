#!/usr/bin/env python3
"""ytdlp_parse.py — parse_ytdlp_json(json_text) -> {view_count, like_count} (REQ-LV-012/014).
Shared between video (REQ-LV-012/013) and affiliate (REQ-LV-014, cross-repo, "重複実装しない").
Pure string/dict parsing only — malformed/missing input NEVER crashes and NEVER fabricates a
value; a missing or wrong-typed field is always None, never 0 or a guess.
"""
import json


def _int_or_none(v):
    return v if isinstance(v, int) and not isinstance(v, bool) else None


def parse_ytdlp_json(json_text):
    try:
        data = json.loads(json_text)
    except Exception:
        return {"view_count": None, "like_count": None}
    if not isinstance(data, dict):
        return {"view_count": None, "like_count": None}
    return {
        "view_count": _int_or_none(data.get("view_count")),
        "like_count": _int_or_none(data.get("like_count")),
    }
