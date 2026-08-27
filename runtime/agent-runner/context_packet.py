#!/usr/bin/env python3
"""Deterministic bounded context packets shared by repository loop adapters."""

from __future__ import annotations

import json
from typing import Any


class ContextPacketError(ValueError):
    pass


def _truncate_utf8(value: str, limit: int) -> str:
    raw = value.encode("utf-8")
    if len(raw) <= limit:
        return value
    suffix = "…"
    room = max(0, limit - len(suffix.encode("utf-8")))
    return raw[:room].decode("utf-8", errors="ignore") + suffix


def _bounded(value: Any, *, depth: int, string_bytes: int, list_items: int, map_items: int) -> Any:
    if depth < 0:
        raise ContextPacketError("context packet depth exceeded")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return _truncate_utf8(value, string_bytes)
    if isinstance(value, list):
        return [
            _bounded(
                item,
                depth=depth - 1,
                string_bytes=string_bytes,
                list_items=list_items,
                map_items=map_items,
            )
            for item in value[:list_items]
        ]
    if isinstance(value, dict):
        return {
            str(key): _bounded(
                child,
                depth=depth - 1,
                string_bytes=string_bytes,
                list_items=list_items,
                map_items=map_items,
            )
            for key, child in list(value.items())[:map_items]
        }
    raise ContextPacketError(f"unsupported context value: {type(value).__name__}")


def _encode(packet: dict[str, Any]) -> bytes:
    return json.dumps(
        packet,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def build_packet(
    *,
    kind: str,
    fields: dict[str, Any],
    max_bytes: int = 8192,
    max_fields: int = 24,
    string_bytes: int = 512,
    list_items: int = 8,
    map_items: int = 24,
    max_depth: int = 4,
) -> dict[str, Any]:
    if not kind or len(fields) > max_fields:
        raise ContextPacketError("context packet kind/field limit invalid")
    bounded = _bounded(
        fields,
        depth=max_depth,
        string_bytes=string_bytes,
        list_items=list_items,
        map_items=map_items,
    )
    packet = {
        "version": 1,
        "kind": kind,
        "fields": bounded,
        "limits": {
            "max_bytes": max_bytes,
            "max_fields": max_fields,
            "string_bytes": string_bytes,
            "list_items": list_items,
            "map_items": map_items,
            "max_depth": max_depth,
        },
        "metrics": {
            "field_count": len(bounded),
            "byte_count": 0,
            # A tokenizer can emit at most one token per input byte. This is a
            # deliberately conservative provider-independent ceiling.
            "conservative_token_ceiling": 0,
        },
    }
    for _ in range(8):
        byte_count = len(_encode(packet))
        if (
            packet["metrics"]["byte_count"] == byte_count
            and packet["metrics"]["conservative_token_ceiling"] == byte_count
        ):
            break
        packet["metrics"]["byte_count"] = byte_count
        packet["metrics"]["conservative_token_ceiling"] = byte_count
    final_size = len(_encode(packet))
    if final_size != packet["metrics"]["byte_count"]:
        raise ContextPacketError("context packet metrics did not stabilize")
    if final_size > max_bytes:
        raise ContextPacketError(f"context packet exceeds {max_bytes} bytes")
    return packet


def serialize_packet(packet: dict[str, Any]) -> bytes:
    encoded = _encode(packet)
    metrics = packet.get("metrics")
    if not isinstance(metrics, dict) or metrics.get("byte_count") != len(encoded):
        raise ContextPacketError("context packet byte_count mismatch")
    return encoded
