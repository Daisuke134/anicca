---
name: life-manager-disk-cleanup
description: Host-wide, fail-closed disk capacity governor for Life Manager.
---

# Life Manager disk cleanup

This skill owns the local host capacity pass. It is intentionally not a
Life-Manager-directory cleaner: it measures the Mac and only removes an
allow-listed regenerable artifact after an open-path probe confirms
`confirmed-closed`.

## Safety contract

- `.claude`, `.codex`, `.config/ai`, OpenClaw state/identity/workspace, `.git`,
  databases, credentials, cookies, source, and `state/*.jsonl` are preserved.
- Unknown paths, active leases, symlinks, open paths, and probe errors are
  preserved and recorded.
- The 5-minute pass has one atomic lock and no LLM deletion authority.
- Pressure is asserted below 11 GiB and is not cleared until the recovery floor
  is reached; the 20 GiB threshold starts preventive containment.
- Receipts are bounded and the high-volume cleanup ledger is rotated before it
  can consume the reserve.

## Local installation

```sh
skills/self/disk-cleanup/install-launchd.sh
```

The installer renders the user-specific plist, validates it with `plutil`, and
registers `ai.anicca.life-manager-disk-cleanup` at a 300-second interval. If
the macOS launchd user domain is temporarily unavailable, the existing
emergency guard invokes `disk_cleanup.py` as its single fallback owner. The
legacy hourly label is only a compatibility trigger: when the host adapter is
installed it invokes the same emergency guard with `EMERGENCY_GUARD_FULL_PASS=1`
so deferred worktree inspection is not permanently skipped.

Run the tests with:

```sh
python3 -m pytest -q skills/self/disk-cleanup/tests/test_disk_cleanup.py
```
