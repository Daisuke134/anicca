#!/usr/bin/env python3
"""Canonical hook eligibility and idempotent creative experiment planning."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

from product_router import Registry, RoutingError, load_registry, require


def read_jsonl(path: pathlib.Path) -> list[dict]:
    rows = []
    if not pathlib.Path(path).exists():
        return rows
    for line_no, line in enumerate(pathlib.Path(path).read_text(encoding="utf-8").splitlines(), 1):
        require(bool(line.strip()), f"blank JSONL line: {path}:{line_no}")
        row = json.loads(line)
        require(isinstance(row, dict), f"JSONL row must be object: {path}:{line_no}")
        rows.append(row)
    return rows


def parse_time(value: str) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None, "history timestamp requires timezone")
    return parsed


def eligible_hooks(registry: Registry, hooks_path: pathlib.Path, product_id: str,
                   account_id: str, history_path: pathlib.Path | None = None,
                   now: str | None = None, days: int = 14) -> list[dict]:
    require(product_id in registry.products, f"unknown product: {product_id}")
    require(account_id in registry.accounts, f"unknown account: {account_id}")
    account = registry.accounts[account_id]
    require(account["product_id"] == product_id, "account product mismatch")
    used: set[str] = set()
    if history_path is not None and pathlib.Path(history_path).exists():
        current = parse_time(now) if now else dt.datetime.now(dt.timezone.utc)
        cutoff = current - dt.timedelta(days=days)
        for row in read_jsonl(history_path):
            if row.get("account_id") != account_id or not row.get("hook_id"):
                continue
            planned_at = parse_time(row["planned_at"])
            if planned_at >= cutoff:
                used.add(row["hook_id"])
    eligible = [
        row for row in read_jsonl(hooks_path)
        if row.get("schema_version") == "marketing.hook.v1"
        and row.get("status") == "active"
        and row.get("product_ids") == [product_id]
        and row.get("language") in {account["language"], "multi"}
        and row.get("id") not in used
    ]
    return sorted(eligible, key=lambda row: row["id"])


def stable_id(prefix: str, values: list[str]) -> str:
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()
    return f"{prefix}.{hashlib.sha256(payload).hexdigest()[:24]}"


def create_plan(registry: Registry, hooks_path: pathlib.Path, *, product_id: str,
                account_id: str, hook_id: str, tactic_id: str, renderer_id: str,
                idempotency_key: str) -> dict:
    require(bool(idempotency_key.strip()), "idempotency key required")
    require(account_id in registry.accounts, f"unknown account: {account_id}")
    account = registry.accounts[account_id]
    require(account["product_id"] == product_id, "account product mismatch")
    require(renderer_id in registry.renderers, f"unknown renderer: {renderer_id}")
    require(renderer_id in account["allowed_renderer_ids"], "renderer not allowed for account")
    hooks = {row["id"]: row for row in eligible_hooks(registry, hooks_path, product_id, account_id)}
    require(hook_id in hooks, "hook is not eligible for product/account")
    tactics = {row.get("id") for row in read_jsonl(registry.engine / "intel" / "playbook.jsonl")}
    require(tactic_id in tactics, "unknown tactic")
    product = registry.products[product_id]
    identity = [product_id, account_id, hook_id, tactic_id, renderer_id, idempotency_key]
    return {
        "schema_version": "marketing.experiment-plan.v1",
        "experiment_id": stable_id("experiment", identity),
        "creative_id": stable_id("creative", identity + ["creative"]),
        "product_id": product_id,
        "account_id": account_id,
        "hook_id": hook_id,
        "hook_text": hooks[hook_id]["text"],
        "tactic_id": tactic_id,
        "renderer_id": renderer_id,
        "language": account["language"],
        "cta": product["cta"],
        "destination_url": product["destination_url"],
        "primary_metric": product["primary_metric"],
        "attribution_method": product["attribution_method"],
        "idempotency_key": idempotency_key,
        "status": "planned",
    }


def append_plan(path: pathlib.Path, plan: dict, planned_at: str) -> bool:
    rows = read_jsonl(path)
    matches = [row for row in rows if row.get("experiment_id") == plan["experiment_id"]]
    record = {**plan, "planned_at": planned_at}
    if matches:
        comparable = {key: value for key, value in matches[0].items() if key != "planned_at"}
        require(comparable == plan, "experiment replay conflicts with stored plan")
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    return True


def main(argv: list[str] | None = None) -> int:
    engine = pathlib.Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    candidates = sub.add_parser("candidates")
    candidates.add_argument("--product", required=True)
    candidates.add_argument("--account", required=True)
    candidates.add_argument("--history", type=pathlib.Path)
    plan = sub.add_parser("plan")
    for command in (plan,):
        command.add_argument("--product", required=True)
        command.add_argument("--account", required=True)
        command.add_argument("--hook", required=True)
        command.add_argument("--tactic", required=True)
        command.add_argument("--renderer", required=True)
        command.add_argument("--idempotency-key", required=True)
        command.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        registry = load_registry(engine)
        hooks_path = engine / "intel" / "hook-library.jsonl"
        if args.command == "candidates":
            result = {"status": "success", "candidates": eligible_hooks(
                registry, hooks_path, args.product, args.account, args.history)}
        else:
            result = create_plan(registry, hooks_path, product_id=args.product,
                                 account_id=args.account, hook_id=args.hook,
                                 tactic_id=args.tactic, renderer_id=args.renderer,
                                 idempotency_key=args.idempotency_key)
            if args.output:
                result = {**result, "appended": append_plan(
                    args.output, result, dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"))}
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
