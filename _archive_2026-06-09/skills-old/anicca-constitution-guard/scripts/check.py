#!/usr/bin/env python3
"""anicca-constitution-guard — deterministic pre-action veto.

Reads:
  - argv: --action "<free-text describing the action about to be taken>"
  - ~/.hermes/state/constitution.sha (written by anicca-heartbeat #323)
  - /Users/anicca/anicca-oss/CONSTITUTION.md (live file)
  - scripts/rules-law1.json (Law I patterns)
  - scripts/rules-northstar.json (North Star patterns)

Emits:
  - JSON line to stdout: {ts, decision, reason, action_digest, constitution_sha}
  - Appends the SAME JSON line to ~/.hermes/state/constitution-violations.jsonl
    on every call (OK or BLOCKED — append-only audit trail, not just failures).
  - Exit codes:
       0 = OK            (action passes both rule sets + hash matches)
       2 = BLOCKED       (rule match)
       3 = BLOCKED       (constitution_hash_mismatch — heartbeat hash != live file hash)
       4 = USAGE error   (missing --action)

Read-only side effects: only the append to constitution-violations.jsonl.
No network. No LLM call. Runs in <50ms.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
RULES_LAW1 = SKILL_DIR / "scripts" / "rules-law1.json"
RULES_NS = SKILL_DIR / "scripts" / "rules-northstar.json"
CONSTITUTION = Path("/Users/anicca/anicca-oss/CONSTITUTION.md")
STATE_DIR = Path.home() / ".hermes" / "state"
LOG = STATE_DIR / "constitution-violations.jsonl"
HEARTBEAT_SHA_FILE = STATE_DIR / "constitution.sha"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def load_rules(path: Path) -> list:
    return json.loads(path.read_text()).get("block_patterns", [])


def screen(action: str, patterns: list) -> tuple[bool, str, str]:
    """Returns (matched, rule_id, reason)."""
    for p in patterns:
        if re.search(p["regex"], action):
            return True, p["id"], p["reason"]
    return False, "", ""


def write_log(row: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--action", required=False,
                    help="Free-text description of the action about to be taken.")
    args = ap.parse_args()
    if not args.action:
        sys.stderr.write("usage: check.py --action '<text>'\n")
        return 4

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    action_digest = hashlib.sha256(args.action.encode("utf-8")).hexdigest()[:16]
    live_sha = sha256_file(CONSTITUTION)
    heartbeat_sha = (HEARTBEAT_SHA_FILE.read_text().strip()
                     if HEARTBEAT_SHA_FILE.exists() else "")

    # Hash check first — if constitution was tampered, every action is BLOCKED.
    if heartbeat_sha and heartbeat_sha != live_sha:
        row = {
            "ts": ts, "decision": "BLOCKED",
            "reason": "constitution_hash_mismatch",
            "action_digest": action_digest,
            "constitution_sha": live_sha,
            "heartbeat_sha": heartbeat_sha,
        }
        write_log(row)
        print(json.dumps(row, ensure_ascii=False))
        return 3

    # Rule screening (Law I first, then North Star)
    for rule_set_name, rule_file in (("law_I", RULES_LAW1),
                                     ("north_star", RULES_NS)):
        patterns = load_rules(rule_file)
        matched, rid, reason = screen(args.action, patterns)
        if matched:
            row = {
                "ts": ts, "decision": "BLOCKED",
                "reason": reason, "rule_id": rid, "rule_set": rule_set_name,
                "action_digest": action_digest,
                "constitution_sha": live_sha,
            }
            write_log(row)
            print(json.dumps(row, ensure_ascii=False))
            return 2

    # No match → OK (still log; the audit trail is append-only on every call)
    row = {
        "ts": ts, "decision": "OK", "reason": "no_rule_match",
        "action_digest": action_digest,
        "constitution_sha": live_sha,
    }
    write_log(row)
    print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
