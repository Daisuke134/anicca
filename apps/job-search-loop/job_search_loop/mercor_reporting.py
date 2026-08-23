from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .mercor_human_gate import HumanGateStore
from .telegram import send_once


def _labels(rows: Any, *, field: str = "title") -> list[str]:
    if not isinstance(rows, list):
        return []
    values: list[str] = []
    for row in rows:
        if isinstance(row, Mapping):
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                values.append(value.strip())
    return values


def build_pass_message(*, run_id: str, result: Mapping[str, Any]) -> str:
    status = str(result.get("status") or "unknown")
    inspected = []
    for row in result.get("inspected_listings", []):
        if not isinstance(row, Mapping):
            continue
        title = row.get("title")
        decision = row.get("decision")
        if isinstance(title, str) and title.strip():
            label = title.strip()
            if isinstance(decision, str) and decision.strip():
                label += f" [{decision.strip()}]"
            inspected.append(label)
    submitted = _labels(result.get("submitted"))
    needs_human = _labels(result.get("needs_human"), field="reason") or [
        value.strip()
        for value in result.get("needs_human", [])
        if isinstance(value, str) and value.strip()
    ]
    blocked = _labels(result.get("blocked"), field="reason") or [
        value.strip()
        for value in result.get("blocked", [])
        if isinstance(value, str) and value.strip()
    ]
    fields = [f"Codex::: Mercor pass {run_id} status={status}"]
    if inspected:
        fields.append("inspected=" + "; ".join(inspected[:5]))
    if submitted:
        fields.append("submitted=" + ", ".join(submitted[:3]))
    if needs_human:
        fields.append("needs_human=" + ", ".join(needs_human[:3]))
    if blocked:
        fields.append("blocked=" + ", ".join(blocked[:3]))
    if not any((inspected, submitted, needs_human, blocked)):
        fields.append("detail=no grounded action")
    return "\n".join(fields)


def report_pass(*, run_id: str, result_path: Path, outbox: Path, gate_store: Path | None = None) -> dict[str, Any]:
    result = json.loads(Path(result_path).read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Mercor pass result must be an object")
    message = build_pass_message(run_id=run_id, result=result)
    gate_ids: list[str] = []
    if gate_store is not None:
        evidence = result.get("evidence") if isinstance(result.get("evidence"), Mapping) else {}
        evidence_ref = str(evidence.get("page_url") or f"run:{run_id}")
        store = HumanGateStore(gate_store)
        for reason in result.get("needs_human", []):
            if isinstance(reason, str) and reason.strip():
                gate_ids.append(store.record(run_id=run_id, reason=reason, evidence_ref=evidence_ref)["gate_id"])
    event_key = f"mercor-pass:{run_id}"
    try:
        delivery = send_once(database=outbox, event_key=event_key, message=message)
        status = {**delivery, "delivery": "sent", "message": message, "human_gate_ids": gate_ids}
    except Exception as error:  # reporting must not suppress the pass result
        status = {
            "delivery": "delivery_unknown",
            "reason": type(error).__name__,
            "message": message,
            "human_gate_ids": gate_ids,
        }
    return status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--result", required=True, type=Path)
    parser.add_argument("--outbox", required=True, type=Path)
    parser.add_argument("--gate-store", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    result = report_pass(run_id=args.run_id, result_path=args.result, outbox=args.outbox, gate_store=args.gate_store)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(json.dumps({"delivery": result["delivery"], "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
