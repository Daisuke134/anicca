#!/usr/bin/env python3
"""Validate and query the versioned Affiliate program research registry."""

import argparse
import hmac
import json
import os
import pwd
import re
import subprocess
import sys
import tempfile
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


def store_credential(program, label, markdown_path, verification):
    secret_ref = program["credential_ref"]
    if secret_ref is None:
        raise ValueError("credential reference is not configured")
    parsed = urlparse(secret_ref)
    if parsed.scheme != "keychain" or not parsed.netloc or not parsed.path[1:]:
        raise ValueError("invalid credential reference")
    secret = sys.stdin.buffer.readline().rstrip(b"\r\n")
    if len(secret) < 12 or b"\x00" in secret:
        raise ValueError("credential must contain at least 12 non-NUL bytes")
    markdown_path = markdown_path.expanduser()
    text = markdown_path.read_text(encoding="utf-8")
    section = re.search(
        rf"(?ms)^## {re.escape(label)}\n.*?(?=^## |\Z)", text,
    )
    if section is None or not re.search(r"(?m)^- Password: .*$", section.group()):
        raise ValueError("private credential section is missing")
    updated_section = re.sub(
        r"(?m)^- Password: .*$",
        "- Password: " + secret.decode("utf-8"),
        section.group(),
        count=1,
    )
    updated_section = re.sub(
        r"(?m)^- Verification: .*$",
        f"- Verification: `{verification}`",
        updated_section,
        count=1,
    )
    updated = text[:section.start()] + updated_section + text[section.end():]
    markdown_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{markdown_path.name}.", dir=markdown_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(temporary, 0o600)
        os.replace(temporary, markdown_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if secret.decode("utf-8") not in markdown_path.read_text(encoding="utf-8"):
        raise ValueError("private Markdown readback mismatch")

    environment = {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "HOME": pwd.getpwuid(os.getuid()).pw_dir,
    }
    subprocess.run(
        [
            "/usr/bin/security", "add-generic-password", "-U", "-s", parsed.netloc,
            "-a", parsed.path[1:], "-w", secret.decode("utf-8"),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=True,
        env=environment,
    )
    readback = subprocess.run(
        [
            "/usr/bin/security", "find-generic-password", "-s", parsed.netloc,
            "-a", parsed.path[1:], "-w",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        timeout=10,
        check=True,
        env=environment,
    ).stdout.rstrip(b"\r\n")
    if not hmac.compare_digest(secret, readback):
        raise ValueError("Keychain readback mismatch")
    return {
        "id": program["id"],
        "credential_ref": secret_ref,
        "keychain_state": "VERIFIED_NONEMPTY",
        "private_markdown_state": "VERIFIED_NONEMPTY",
    }


def main():
    parser = argparse.ArgumentParser(prog="affiliate programs")
    parser.add_argument("command", choices=("list", "next", "credential", "store-credential"))
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--id")
    parser.add_argument("--label")
    parser.add_argument(
        "--verification",
        choices=("SAVED_BEFORE_SUBMIT", "VERIFIED_LOGIN"),
        default="SAVED_BEFORE_SUBMIT",
    )
    parser.add_argument(
        "--private-markdown",
        type=Path,
        default=Path("~/.config/anicca/affiliate-credentials.md"),
    )
    args = parser.parse_args()
    path = Path(__file__).resolve().parents[1] / "config" / "programs" / "en-candidates.json"
    programs = load_registry(path)
    if args.decision:
        programs = [item for item in programs if item["decision"] in args.decision]
    if args.id:
        programs = [item for item in programs if item["id"] == args.id]
    if args.command in ("credential", "store-credential"):
        if len(programs) != 1:
            return 3
        if args.command == "credential":
            result = credential_state(programs[0])
        else:
            if not args.label:
                raise ValueError("--label is required")
            result = store_credential(
                programs[0], args.label, args.private_markdown, args.verification,
            )
    else:
        result = programs[:1] if args.command == "next" else programs
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result else 3


if __name__ == "__main__":
    raise SystemExit(main())
