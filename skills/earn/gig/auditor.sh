#!/usr/bin/env bash
# Independent health audit for the four direct revenue owners and their support units.
# The canonical launchd manifest is the only owner registry. This entrypoint never
# reads or repairs the retired gig_pass/Hermes control plane.
set -uo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/gig_paths.sh
source "$HERE/scripts/gig_paths.sh"

mkdir -p "$GIG_STATE_DIR" "$GIG_LOG_DIR"

# Reconcile only labels present in the canonical registry before observing them.
GIG_LAUNCHD_REPO_DIR="$HERE/launchd" \
GIG_LAUNCHD_REGISTRY="$HERE/config/launchd/agents/gig.json" \
  bash "$HERE/plist-selfheal.sh"
selfheal_rc=$?

/opt/homebrew/bin/python3 - \
  "$HERE/config/launchd/agents/gig.json" \
  "$GIG_STATE_DIR/audit.jsonl" \
  "$LIFE_MANAGER_REPO" \
  "$selfheal_rc" <<'PY'
from __future__ import annotations

import json
import os
import plistlib
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

registry_path = Path(sys.argv[1])
audit_path = Path(sys.argv[2])
release = Path(sys.argv[3]).resolve()
selfheal_rc = int(sys.argv[4])
home = Path.home()
now = int(time.time())

registry = json.loads(registry_path.read_text(encoding="utf-8"))
labels = registry["canonical_labels"]
agents = registry["agents"]
manifest_ok = (
    len(labels) == 7
    and len(set(labels)) == 7
    and set(labels) == set(agents)
    and all(agents[label].get("desired_state") == "enabled" for label in labels)
)

launchd: dict[str, dict[str, object]] = {}
release_text = str(release) + "/"
for label in labels:
    printed = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
        capture_output=True,
        text=True,
        check=False,
    )
    plist_path = home / "Library" / "LaunchAgents" / f"{label}.plist"
    argv: list[str] = []
    try:
        argv = [str(value) for value in plistlib.loads(plist_path.read_bytes()).get("ProgramArguments", [])]
    except (OSError, plistlib.InvalidFileException, ValueError):
        pass
    repo_owned = label != "ai.anicca.hf-gig-browser"
    path_ok = (not repo_owned) or any(value.startswith(release_text) for value in argv)
    launchd[label] = {
        "loaded": printed.returncode == 0,
        "running": "state = running" in printed.stdout,
        "release_path_ok": path_ok,
    }

def last_json_line(path: Path) -> dict[str, object] | None:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    for line in reversed(lines):
        try:
            value = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(value, dict):
            return value
    return None

receipt_sources = {
    "storefront": (home / ".openclaw/logs/gig-storefront-direct-launchd.out.log", 5400),
    "apply": (home / ".openclaw/logs/gig-apply-direct-launchd.out.log", 5400),
    "reply": (home / ".openclaw/logs/gig-reply-detector-launchd.out.log", 1800),
    "paid": (home / "gig/evidence/paid-direct-live/latest.json", 7200),
}
receipts: dict[str, dict[str, object]] = {}
for owner, (path, max_age) in receipt_sources.items():
    value = last_json_line(path)
    try:
        age = now - int(path.stat().st_mtime)
    except OSError:
        age = None
    receipts[owner] = {
        "present": value is not None,
        "fresh": age is not None and 0 <= age <= max_age,
        "age_seconds": age,
        "status": value.get("status") if value else None,
        "id": (value.get("pass_id") or value.get("run_id")) if value else None,
        "effect": value.get("effect") if value else None,
        "readback": value.get("readback", value.get("official_readback")) if value else None,
        "duplicate": value.get("duplicate") if value else None,
    }

browser_ok = False
try:
    with urllib.request.urlopen("http://127.0.0.1:9223/json/version", timeout=5) as response:
        browser_ok = response.status == 200 and bool(json.load(response).get("Browser"))
except Exception:
    pass

installed = sorted(path.stem for path in (home / "Library" / "LaunchAgents").glob("ai.anicca.hf-gig-*.plist"))
inventory_ok = installed == sorted(labels)
loaded_ok = all(value["loaded"] for value in launchd.values())
paths_ok = all(value["release_path_ok"] for value in launchd.values())
receipts_ok = all(value["present"] and value["fresh"] for value in receipts.values())
status = "ok" if all((manifest_ok, inventory_ok, loaded_ok, paths_ok, receipts_ok, browser_ok, selfheal_rc == 0)) else "degraded"
row = {
    "version": 1,
    "kind": "direct_owner_health",
    "ts": now,
    "status": status,
    "release": str(release),
    "manifest_ok": manifest_ok,
    "inventory_ok": inventory_ok,
    "selfheal_rc": selfheal_rc,
    "browser_ok": browser_ok,
    "launchd": launchd,
    "receipts": receipts,
}
audit_path.parent.mkdir(parents=True, exist_ok=True)
with audit_path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
PY
