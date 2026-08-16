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


PASSTHROUGH_ENV = (
    "LANG",
    "LC_ALL",
    "TZ",
    "ANICCA_BUDGET_SCOPE_ID",
    "ANICCA_PASS_TOKEN_BUDGET",
    "ANICCA_LOOP_DAILY_TOKEN_BUDGET",
    "ANICCA_BUDGET_REQUIRED",
    "ANICCA_BUDGET_DAILY_SCOPE",
    "ANICCA_TOKEN_BUDGET_LEDGER",
    "ANICCA_BUDGET_DAY_TZ",
    "ANICCA_USAGE_LEDGER",
)


def _owner_path(value: str, owner_home: Path) -> Path:
    if value == "~":
        return owner_home
    if value.startswith("~/"):
        return owner_home / value[2:]
    path = Path(value)
    return path if path.is_absolute() else owner_home / path


def allowlisted_environment(source: dict[str, str], executable: Path) -> dict[str, str]:
    owner_home = Path(source.get("HOME") or str(Path.home())).resolve()
    state_home = _owner_path(
        source.get("LIFE_MANAGER_STATE_HOME", str(owner_home / ".local" / "state" / "life-manager")),
        owner_home,
    ).resolve()
    codex_home = state_home / "affiliate" / "codex-runner"
    user_home = codex_home / "user-home"
    for directory in (codex_home, user_home):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        directory.chmod(0o700)
    auth_file = _owner_path(
        source.get("AFFILIATE_CODEX_AUTH_FILE", str(owner_home / ".codex" / "auth.json")),
        owner_home,
    ).resolve()
    child = {
        "PATH": os.pathsep.join((str(executable.parent), "/usr/bin", "/bin", "/usr/sbin", "/sbin")),
        "HOME": str(user_home),
        "CODEX_HOME": str(codex_home),
        "AFFILIATE_CODEX_HOME": str(codex_home),
        "AFFILIATE_CODEX_AUTH_FILE": str(auth_file),
        "AGENT_RUNNER_CONFIG": source.get(
            "AGENT_RUNNER_CONFIG", str(SKILL_ROOT / "config" / "agent-runner.json")
        ),
    }
    for name in PASSTHROUGH_ENV:
        if source.get(name):
            child[name] = source[name]
    return child


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
    parent_environment = dict(os.environ)
    receipt_value = parent_environment.get("AFFILIATE_CODEX_CAPABILITY_RECEIPT", "")
    if not receipt_value:
        raise PinError
    receipt_path = Path(receipt_value)
    executable = verify_codex_pin(receipt_path)
    try:
        evidence_dir = Path(sys.argv[sys.argv.index("--evidence-dir") + 1])
    except (ValueError, IndexError):
        raise PinError
    write_model_call_pin(receipt_path, evidence_dir)
    child_environment = allowlisted_environment(parent_environment, executable)
    os.environ.clear()
    os.environ.update(child_environment)
    sys.path.insert(0, str(VENDOR))
    import agent_runner
    return agent_runner.run()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PinError:
        print("affiliate agent runner: Codex binary pin rejected", file=sys.stderr)
        raise SystemExit(1)
