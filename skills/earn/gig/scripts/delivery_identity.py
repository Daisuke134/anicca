"""Stable marketplace identity shared by project and delivery ledgers."""

from __future__ import annotations

from typing import Any


def stable_identity(item: dict[str, Any]) -> str:
    """Return one safe identity for every durable paid-work artifact path.

    Request IDs are preferred when available, then talkroom IDs, then the
    marketplace contract ID.  All consumers must use this same precedence so
    a queue observation cannot write evidence under a different project root.
    """
    value = item.get("request_id") or item.get("talkroom_id") or item.get("contract_id")
    identity = str(value or "").strip()
    if not identity:
        raise ValueError("request_id, talkroom_id, or contract_id is required")
    if identity in {".", ".."} or "/" in identity or "\\" in identity:
        raise ValueError("project identity must be a single safe path component")
    return identity
