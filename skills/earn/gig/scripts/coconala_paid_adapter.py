#!/usr/bin/env python3
"""Thin Coconala boundary for the shared marketplace Paid kernel."""

from __future__ import annotations

from typing import Any, Callable, Mapping


class CoconalaPaidAdapter:
    def __init__(
        self,
        *,
        account_id: str,
        inventory_reader: Callable[[], list[dict[str, Any]]],
        refresh_reader: Callable[[dict[str, Any]], Mapping[str, Any]],
        context_reader: Callable[[dict[str, Any]], Mapping[str, Any]],
        effect_runner: Callable[[dict[str, Any]], None],
        readback_reader: Callable[[dict[str, Any]], Mapping[str, Any]],
    ):
        if not isinstance(account_id, str) or not account_id.strip():
            raise ValueError("coconala_account_id_invalid")
        self.account_id = account_id.strip()
        self.inventory_reader = inventory_reader
        self.refresh_reader = refresh_reader
        self.context_reader = context_reader
        self.effect_runner = effect_runner
        self.readback_reader = readback_reader
        self._items: dict[str, dict[str, Any]] = {}

    def _normalize(self, source: Mapping[str, Any]) -> dict[str, Any]:
        required = {
            "work_id": source.get("talkroom_id"),
            "latest_event_id": source.get("buyer_feedback_sha256"),
            "provider_state": source.get("talkroom_state") or source.get("transaction_state"),
            "observed_at": source.get("talkroom_observed_at") or source.get("snapshot_captured_at"),
        }
        if not all(isinstance(value, str) and value.strip() for value in required.values()):
            raise RuntimeError("coconala_paid_observation_invalid")
        return {
            "provider": "coconala", "account_id": self.account_id,
            **{key: value.strip() for key, value in required.items()},
        }

    def observe_active(self) -> list[dict[str, Any]]:
        sources = self.inventory_reader()
        if not isinstance(sources, list):
            raise RuntimeError("coconala_paid_inventory_unavailable")
        items: dict[str, dict[str, Any]] = {}
        rows = []
        for source in sources:
            if not isinstance(source, Mapping):
                raise RuntimeError("coconala_paid_inventory_unavailable")
            row = self._normalize(source)
            if row["work_id"] in items:
                raise RuntimeError("coconala_paid_inventory_duplicate")
            items[row["work_id"]] = dict(source)
            rows.append(row)
        self._items = items
        return rows

    def _item(self, work_id: str) -> dict[str, Any]:
        if work_id not in self._items:
            self.observe_active()
        try:
            return dict(self._items[work_id])
        except KeyError:
            raise RuntimeError("coconala_paid_work_unavailable") from None

    def observe_one(self, work_id: str) -> dict[str, Any]:
        refreshed = self.refresh_reader(self._item(work_id))
        if not isinstance(refreshed, Mapping):
            raise RuntimeError("coconala_paid_work_unavailable")
        row = self._normalize(refreshed)
        if row["work_id"] != work_id:
            raise RuntimeError("coconala_paid_work_identity_changed")
        self._items[work_id] = dict(refreshed)
        return row

    def context(self, work_id: str) -> dict[str, Any]:
        value = self.context_reader(self._item(work_id))
        if not isinstance(value, Mapping):
            raise RuntimeError("coconala_paid_context_unavailable")
        return dict(value)

    def mutate(self, intent: dict[str, Any]) -> None:
        self.effect_runner(intent)

    def readback(self, intent: dict[str, Any]) -> dict[str, Any]:
        value = self.readback_reader(intent)
        if not isinstance(value, Mapping):
            raise RuntimeError("coconala_paid_readback_unavailable")
        return dict(value)


__all__ = ["CoconalaPaidAdapter"]
