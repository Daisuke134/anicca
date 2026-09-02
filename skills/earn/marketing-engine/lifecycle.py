#!/usr/bin/env python3
"""Shared evidence-driven marketing account lifecycle."""

import argparse
import copy
import datetime
import json
import os
import pathlib
import sys

import publisher


CONTRACT = "marketing-engine/v1"
ACTIVE = ("setup", "publisher_ready", "posted", "measuring", "commercial")
TERMINAL = ("publisher_failed", "session_failed", "provision_failed")


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def advance_account(account, health_probe=publisher.health):
    """Probe only setup accounts; terminal/advanced accounts are immutable here."""
    if str(account.get("status") or "") != "setup":
        return account
    updated = copy.deepcopy(account)
    result = health_probe(updated)
    updated["lifecycle_contract"] = CONTRACT
    updated["publisher"] = result.get("publisher", "meta_graph")
    updated["publisher_state"] = {**result, "checked_at": _now()}
    if result.get("ok"):
        updated["status"] = "publisher_ready"
        if result.get("publisher_account_id"):
            updated["publisher_account_id"] = result["publisher_account_id"]
    else:
        updated["status"] = "publisher_failed"
    return updated


def transition(account, event, evidence=None):
    next_status = {
        ("publisher_ready", "published"): "posted",
        ("posted", "measurement_started"): "measuring",
        ("measuring", "reach_verified"): "commercial",
    }.get((account.get("status"), event))
    if not next_status:
        raise ValueError(f"invalid lifecycle transition: {account.get('status')} + {event}")
    updated = copy.deepcopy(account)
    updated["status"] = next_status
    updated.setdefault("lifecycle_evidence", []).append({"event": event, "at": _now(), "evidence": evidence or {}})
    return updated


def _write_atomic(path, accounts):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(accounts, ensure_ascii=False, indent=2) + "\n")
    os.replace(temporary, path)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("accounts_path")
    parser.add_argument("--health-fixture")
    args = parser.parse_args(argv)
    path = pathlib.Path(args.accounts_path)
    accounts = json.loads(path.read_text())
    fixture = json.loads(pathlib.Path(args.health_fixture).read_text()) if args.health_fixture else None
    probe = (lambda _account: fixture) if fixture is not None else publisher.health
    changed = False
    failed = False
    for index, account in enumerate(accounts):
        updated = advance_account(account, probe)
        if updated is not account:
            accounts[index] = updated
            changed = True
            failed = updated["status"] == "publisher_failed"
            break
    if changed:
        _write_atomic(path, accounts)
    print(json.dumps({"contract": CONTRACT, "changed": changed, "publisher_health_failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
