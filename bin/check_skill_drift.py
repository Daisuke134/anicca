#!/usr/bin/env python3
"""check_skill_drift.py — REQ-VENDOR-003 backend for bin/check-skill-drift.sh: a READ-ONLY drift
auditor. Recomputes the checksum for every skills.lock-vendored path and reports `ok`/`DRIFT`
per entry, never modifying any file. Shares the exact same destination-layout + hash function as
bin/sync_skills.py (lib/vendor_hash.py + the name-keyed layout lookup) so a checksum computed by
one script always matches what the other expects.
"""
import json
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LIB_DIR = os.path.join(_REPO_ROOT, "lib")
sys.path.insert(0, _LIB_DIR)
from vendor_hash import hash_path  # noqa: E402
from vendor_layout import artifact_path  # noqa: E402


def _repo_root():
    return _REPO_ROOT


def main():
    lock_path = os.environ.get("SKILLS_LOCK_FILE") or os.path.join(_repo_root(), "skills.lock")
    vendor_root = os.environ.get("VENDOR_ROOT") or _repo_root()

    try:
        with open(lock_path) as f:
            entries = json.load(f)
    except Exception as e:
        print(f"check-skill-drift: cannot read skills.lock at {lock_path} ({e})", file=sys.stderr)
        return 1

    any_drift = False
    for entry in entries:
        name = entry.get("name", "<unnamed>")
        artifact = artifact_path(vendor_root, name, entry.get("source_path", ""))
        if not os.path.exists(artifact):
            print(f"{name}: DRIFT (missing) -- {artifact} does not exist")
            any_drift = True
            continue
        current = hash_path(artifact)
        recorded = entry.get("sha256")
        if current == recorded:
            print(f"{name}: ok")
        else:
            print(f"{name}: DRIFT (checksum mismatch) recorded={recorded} current={current}")
            any_drift = True

    return 1 if any_drift else 0


if __name__ == "__main__":
    sys.exit(main())
