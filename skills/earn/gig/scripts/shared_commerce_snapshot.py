#!/usr/bin/env python3
"""Build the small, read-only commerce view consumed by parallel lanes."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE_NAMES = (
    "strategy.json", "playbook.json", "applied.jsonl", "applied-outcomes.jsonl",
    "earnings.jsonl", "shuppin.jsonl", "gig-funnel.jsonl", "identity_chain.jsonl",
    "pass-report.jsonl", "b2-shortfall.jsonl",
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b0_objective = _load("b0_objective")
b2_objective = _load("b2_objective")
telegram_report = _load("telegram_report")


def _now(value=None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)


def _ref(gig: Path, name: str):
    path = gig / name
    try:
        stat = path.stat()
        return {"path": name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "mtime": stat.st_mtime_ns, "size": stat.st_size}
    except OSError:
        return None


def _b0(gig: Path) -> dict:
    old = {key: getattr(b0_objective, key) for key in ("STATE", "FUNNEL", "SHUPPIN", "STRATEGY")}
    try:
        b0_objective.STATE = gig
        b0_objective.FUNNEL, b0_objective.SHUPPIN = gig / "gig-funnel.jsonl", gig / "shuppin.jsonl"
        b0_objective.STRATEGY = gig / "strategy.json"
        return b0_objective.decide(b0_objective.storefront_state())
    finally:
        for key, value in old.items():
            setattr(b0_objective, key, value)


def _empty_lanes() -> dict:
    return {
        "apply": {"b2_objective": None, "objective": None, "category_order": [],
                  "freeze_experiments": None, "volume_controller": None},
        "storefront": {"b0_objective": None, "objective": None, "action": None,
                        "live": None, "target": None, "known_service_count": None},
        "reply": {},
        "paid": {},
    }


def build_snapshot(*, gig_dir=None, now=None) -> dict:
    gig = Path(gig_dir or (Path.home() / "gig"))
    at = _now(now)
    slot = int(at.timestamp()) // 1800
    refs = {name: _ref(gig, name) for name in SOURCE_NAMES}
    missing = [name for name, value in refs.items() if value is None]
    digest = hashlib.sha256(json.dumps(
        {name: value["sha256"] for name, value in refs.items() if value},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()
    snapshot_id = f"coconala:{slot}:{digest[:16]}"
    start = datetime.fromtimestamp(slot * 1800, timezone.utc)
    result = {
        "version": 1, "platform": "coconala", "generated_at": at.isoformat(),
        "expires_at": (start + timedelta(minutes=30)).isoformat(), "snapshot_id": snapshot_id,
        "slot": slot, "ready": not missing, "missing_sources": missing,
        "source_refs": refs, "idempotency": {
            "task_template": "gig:coconala:{lane}:{slot}",
            "apply_effect_template": "coconala:application:{request_id}",
            "storefront_effect_template": "coconala:listing:{service_id}:{content_sha256}",
        }, "lanes": _empty_lanes(),
    }
    if missing:
        return result
    b2 = b2_objective.build(
        applied_path=gig / "applied.jsonl", earnings_path=gig / "earnings.jsonl",
        strategy_path=gig / "strategy.json", listing_path=gig / "shuppin.jsonl",
        chain_path=gig / "identity_chain.jsonl", seed=slot, now=at.timestamp(),
    )
    volume = telegram_report.write_application_volume_controller(gig_dir=gig, now=at)
    result["lanes"]["apply"] = {
        "b2_objective": b2.get("objective"), "objective": b2.get("objective"),
        "category_order": b2.get("category_order") or [],
        "freeze_experiments": bool(b2.get("freeze_experiments")),
        "volume_controller": volume,
    }
    store = _b0(gig)
    result["lanes"]["storefront"] = {
        "b0_objective": store.get("objective"), "objective": store.get("objective"),
        "action": store.get("action"), "live": store.get("live"), "target": store.get("target"),
        "known_service_count": store.get("known_service_count"),
    }
    return result


def write_snapshot(*, gig_dir=None, output_path=None, now=None) -> dict:
    result = build_snapshot(gig_dir=gig_dir, now=now)
    output = Path(output_path or (Path.home() / "gig" / "shared-commerce-snapshot.json"))
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        try:
            Path(temporary).unlink()
        except FileNotFoundError:
            pass
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gig-dir", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--now", default=None)
    args = parser.parse_args(argv)
    print(json.dumps(write_snapshot(gig_dir=args.gig_dir, output_path=args.output, now=args.now),
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
