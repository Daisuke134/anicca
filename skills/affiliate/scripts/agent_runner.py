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


class EvidenceError(Exception):
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


def secure_evidence_tree(evidence_dir: Path) -> None:
    if evidence_dir.is_symlink():
        raise EvidenceError
    evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    for path in (evidence_dir, *evidence_dir.rglob("*")):
        if path.is_symlink():
            raise EvidenceError
        if path.is_dir():
            path.chmod(0o700)
        elif path.is_file():
            path.chmod(0o600)
        else:
            raise EvidenceError


def seal_evidence(evidence_dir: Path, runner_exit_code: int) -> Path:
    secure_evidence_tree(evidence_dir)
    summary_path = evidence_dir / "summary.json"
    attempts_path = evidence_dir / "attempts.jsonl"
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if not isinstance(summary, dict):
            raise EvidenceError
        attempt_count = int(summary.get("attempt_count", 0))
        attempt_rows = []
        if attempts_path.is_file():
            attempt_rows = [
                json.loads(line) for line in attempts_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        if any(not isinstance(row, dict) for row in attempt_rows) or len(attempt_rows) != attempt_count:
            raise EvidenceError
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        raise EvidenceError
    seal_path = evidence_dir / "evidence-seal.json"
    inventory.write_receipt(seal_path, {
        "schema_version": 1,
        "status": "SEALED",
        "runner_exit_code": runner_exit_code,
        "summary_sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
        "attempts_sha256": (
            hashlib.sha256(attempts_path.read_bytes()).hexdigest()
            if attempts_path.is_file() else None
        ),
    })
    seal_path.chmod(0o600)
    return seal_path


def verify_evidence_seal(evidence_dir: Path) -> dict:
    seal_path = evidence_dir / "evidence-seal.json"
    summary_path = evidence_dir / "summary.json"
    attempts_path = evidence_dir / "attempts.jsonl"
    try:
        if evidence_dir.is_symlink() or evidence_dir.stat().st_mode & 0o077:
            raise EvidenceError
        for path in evidence_dir.rglob("*"):
            if path.is_symlink() or path.stat().st_mode & 0o077:
                raise EvidenceError
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        expected_attempts = (
            hashlib.sha256(attempts_path.read_bytes()).hexdigest()
            if attempts_path.is_file() else None
        )
        if (
            seal.get("status") != "SEALED"
            or seal.get("summary_sha256") != hashlib.sha256(summary_path.read_bytes()).hexdigest()
            or seal.get("attempts_sha256") != expected_attempts
        ):
            raise EvidenceError
        return seal
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        raise EvidenceError


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
    secure_evidence_tree(evidence_dir)
    (evidence_dir / "evidence-seal.json").unlink(missing_ok=True)
    write_model_call_pin(receipt_path, evidence_dir)
    child_environment = allowlisted_environment(parent_environment, executable)
    os.environ.clear()
    os.environ.update(child_environment)
    sys.path.insert(0, str(VENDOR))
    import agent_runner
    runner_exit_code = agent_runner.run()
    secure_evidence_tree(evidence_dir)
    if (evidence_dir / "summary.json").is_file():
        seal_evidence(evidence_dir, runner_exit_code)
    return runner_exit_code


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PinError, EvidenceError):
        print("affiliate agent runner: execution boundary rejected", file=sys.stderr)
        raise SystemExit(1)
