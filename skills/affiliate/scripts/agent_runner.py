#!/usr/bin/env python3
from __future__ import annotations

import json
import hashlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import machine_capability_inventory as inventory


SKILL_ROOT = HERE.parent
VENDOR = SKILL_ROOT / "vendor" / "agent-runner"


class PinError(Exception):
    pass


def verified_codex_record(receipt_path: Path) -> dict:
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        matches = [item for item in receipt["capabilities"]
                   if item.get("name") == "codex-cli" and item.get("kind") == "codex_cli"]
        if receipt.get("status") != "READY" or len(matches) != 1:
            raise PinError
        expected = matches[0]
        observed = inventory.inspect({"name": "codex-cli", "kind": "codex_cli",
                                      "path": expected["canonical_path"]})
        if observed != expected:
            raise PinError
        return observed
    except (KeyError, OSError, TypeError, ValueError, inventory.InventoryError):
        raise PinError


def verify_codex_pin(receipt_path: Path) -> Path:
    return Path(verified_codex_record(receipt_path)["canonical_path"])


def write_model_call_pin(receipt_path: Path, evidence_dir: Path) -> Path:
    record = verified_codex_record(receipt_path)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.chmod(0o700)
    target = evidence_dir / "codex-binary-pin.json"
    inventory.write_receipt(target, {
        "schema_version": 1,
        "status": "VERIFIED",
        **record,
        "source_receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
    })
    target.chmod(0o600)
    return target


def main() -> int:
    os.umask(0o077)
    receipt_value = os.environ.get("AFFILIATE_CODEX_CAPABILITY_RECEIPT", "")
    if not receipt_value:
        raise PinError
    receipt_path = Path(receipt_value)
    executable = verify_codex_pin(receipt_path)
    try:
        evidence_dir = Path(sys.argv[sys.argv.index("--evidence-dir") + 1])
    except (ValueError, IndexError):
        raise PinError
    write_model_call_pin(receipt_path, evidence_dir)
    os.environ["PATH"] = str(executable.parent) + os.pathsep + os.environ.get("PATH", "")
    os.environ.setdefault("AGENT_RUNNER_CONFIG", str(SKILL_ROOT / "config" / "agent-runner.json"))
    sys.path.insert(0, str(VENDOR))
    import agent_runner
    return agent_runner.run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PinError:
        print("affiliate agent runner: Codex binary pin rejected", file=sys.stderr)
        raise SystemExit(1)
