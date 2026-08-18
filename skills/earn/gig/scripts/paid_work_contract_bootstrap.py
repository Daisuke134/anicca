#!/usr/bin/env python3
"""A22: generate the initial validation contract for a NEW paid order.

`paid_work_transaction.py begin` fails closed without a pre-existing
``delivery/validation-contract.json`` -- correct for an established project,
but a brand-new order has an empty ``delivery/`` directory, which made every
new order a chicken-and-egg deadlock (SSOT 26-gig-loop-asis-tobe-plan.md
section 0.1.3 blocker #1, observed live on order 90000004).

The SSOT sanctions exactly two fixes: drop the precondition, or have CODE
generate the contract before ``begin`` pins it.  This script is the latter.
It is deterministic, generic (no order-id special cases), and idempotent:

* contract already exists           -> no-op, exit 0
* NEW order (empty baseline)        -> write generic validator + contract, exit 0
* ESTABLISHED project, no contract  -> refuse, exit 1 (that is a real anomaly)

The generated contract is deliberately minimal -- artifact existence, size
floor, and suffix allowlist -- because at bootstrap time nothing about the
deliverable is known yet.  It still rejects the observed live failure mode
(tiny fake artifacts), and the project may later replace it with a stronger
order-specific contract.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
from paid_work_validation_contract import (  # noqa: E402
    CONTRACT_RELATIVE_PATH,
    ContractError,
    parse_contract,
    trusted_paths,
)

VALIDATOR_RELATIVE_PATH = Path("validation/validate_delivery_generic.py")
MIN_ARTIFACT_BYTES = 1024
ALLOWED_SUFFIXES = [
    ".zip", ".pdf", ".md", ".txt", ".html", ".csv", ".json",
    ".png", ".jpg", ".jpeg", ".xlsx", ".docx", ".pptx", ".mp4",
]

VALIDATOR_SOURCE = '''#!/usr/bin/env python3
"""Generic bootstrap delivery validator (code-generated for a new order).

Pinned as a trusted file by delivery/validation-contract.json; the paid agent
must never edit it.  Checks only what is knowable before the order has any
history: the artifact exists, clears a size floor, and uses an allowed suffix.
"""
import json
import sys
from pathlib import Path

MIN_ARTIFACT_BYTES = {min_bytes}
ALLOWED_SUFFIXES = {suffixes}


def main() -> int:
    errors = []
    if len(sys.argv) != 2:
        errors.append("artifact_argument_missing")
    else:
        artifact = Path(sys.argv[1])
        if not artifact.is_file():
            errors.append("artifact_missing")
        else:
            if artifact.stat().st_size < MIN_ARTIFACT_BYTES:
                errors.append("artifact_too_small")
            if artifact.suffix.lower() not in ALLOWED_SUFFIXES:
                errors.append("artifact_suffix_forbidden")
    print(json.dumps({{"status": "PASS" if not errors else "FAIL", "errors": errors}}))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
'''


def _atomic_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    except BaseException:
        try:
            os.unlink(name)
        except OSError:
            pass
        raise


def _has_files(directory: Path) -> bool:
    return directory.is_dir() and any(p.is_file() for p in directory.glob("**/*"))


def _contract_payload() -> dict:
    command = {
        "argv": ["python3", str(VALIDATOR_RELATIVE_PATH), "{artifact_path}"],
        "timeout_seconds": 120,
        "expect_stdout_json": {"status": "PASS", "errors": []},
    }
    return {
        "version": 1,
        "generated_by": "paid_work_contract_bootstrap.py",
        "artifact": {
            "type": "file",
            "min_size_bytes": MIN_ARTIFACT_BYTES,
            "allowed_suffixes": ALLOWED_SUFFIXES,
        },
        "trusted_files": [str(VALIDATOR_RELATIVE_PATH)],
        "commands": [
            {"id": "generic-artifact-domain", "kind": "domain", **command},
            {"id": "generic-artifact-test", "kind": "test", **command},
        ],
    }


def bootstrap(project_root: Path) -> dict:
    root = project_root.expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"project_root_missing: {root}")
    contract_path = root / CONTRACT_RELATIVE_PATH
    if contract_path.is_file():
        return {"ok": True, "action": "exists", "contract": str(contract_path)}

    # A missing contract is only a NORMAL state on a genuinely new order:
    # nothing delivered, nothing accepted, no manifest.  An established
    # project that lost its contract is an anomaly this script must not paper
    # over with a weaker generic contract.
    manifest = root / "delivery" / "paid-work-result.json"
    if manifest.is_file() or _has_files(root / "artifacts") or _has_files(root / "acceptance"):
        raise SystemExit(
            f"contract_missing_on_established_project: {root} has prior "
            "delivery output but no delivery/validation-contract.json"
        )

    validator_path = root / VALIDATOR_RELATIVE_PATH
    if not (validator_path.is_file() and validator_path.stat().st_size > 0):
        source = VALIDATOR_SOURCE.format(
            min_bytes=MIN_ARTIFACT_BYTES,
            suffixes=json.dumps(ALLOWED_SUFFIXES),
        )
        _atomic_write(validator_path, source.encode("utf-8"), 0o644)

    payload = _contract_payload()
    content = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

    # Self-verify BEFORE publishing: begin_transaction must accept this exact
    # content, otherwise the deadlock this script exists to break would simply
    # move one step later with a less obvious reason.
    try:
        parsed = parse_contract(content)
        trusted_paths(parsed, root)
    except ContractError as exc:
        raise SystemExit(f"bootstrap_contract_self_check_failed: {exc}") from exc

    _atomic_write(contract_path, content, 0o644)
    return {"ok": True, "action": "created", "contract": str(contract_path)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True, type=Path)
    args = parser.parse_args()
    result = bootstrap(args.project_root)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
