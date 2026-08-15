#!/usr/bin/env python3
"""Validate and query the versioned Affiliate program research registry."""

import argparse
import json
import os
import pwd
import subprocess
from pathlib import Path
from urllib.parse import urlparse


REQUIRED = {
    "id", "priority", "network", "decision", "program_url", "terms_url",
    "commission", "next_action", "evidence",
    "credential_ref",
}


def load_registry(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("market") != "en":
        raise ValueError("unsupported program registry")
    programs = data.get("programs")
    if not isinstance(programs, list) or not programs:
        raise ValueError("empty program registry")
    ids = set()
    for program in programs:
        if set(program) != REQUIRED or program["id"] in ids:
            raise ValueError("invalid or duplicate program record")
        if not program["program_url"].startswith("https://"):
            raise ValueError("program URL must use HTTPS")
        ids.add(program["id"])
    return sorted(programs, key=lambda item: item["priority"])


def credential_state(program):
    secret_ref = program["credential_ref"]
    if secret_ref is None:
        return {"id": program["id"], "credential_state": "NOT_CONFIGURED"}
    parsed = urlparse(secret_ref)
    if parsed.scheme != "keychain" or not parsed.netloc or not parsed.path[1:]:
        raise ValueError("invalid credential reference")
    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "HOME": pwd.getpwuid(os.getuid()).pw_dir,
    }
    result = subprocess.run(
        [
            "/usr/bin/security", "find-generic-password", "-s", parsed.netloc,
            "-a", parsed.path[1:], "-w",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=False,
        env=environment,
    )
    state = "VERIFIED_NONEMPTY" if result.returncode == 0 and result.stdout.strip() else "MISSING_OR_EMPTY"
    return {"id": program["id"], "credential_ref": secret_ref, "credential_state": state}


def main():
    parser = argparse.ArgumentParser(prog="affiliate programs")
    parser.add_argument("command", choices=("list", "next", "credential"))
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--id")
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "config" / "programs" / "en-candidates.json"
    programs = load_registry(path)
    if args.decision:
        programs = [item for item in programs if item["decision"] in args.decision]
    if args.id:
        programs = [item for item in programs if item["id"] == args.id]
    if args.command == "credential":
        if len(programs) != 1:
            return 3
        result = credential_state(programs[0])
    else:
        result = programs[:1] if args.command == "next" else programs
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result else 3


if __name__ == "__main__":
    raise SystemExit(main())
