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


def ensure_credential_section(text, label, source_label, credential_ref):
    section = re.search(rf"(?ms)^## {re.escape(label)}\n.*?(?=^## |\Z)", text)
    if section is not None:
        return text
    if not source_label:
        raise ValueError("private credential section is missing")
    source = re.search(rf"(?ms)^## {re.escape(source_label)}\n.*?(?=^## |\Z)", text)
    login = re.search(r"(?m)^- Login:\s*(.+)$", source.group() if source else "")
    if login is None:
        raise ValueError("source credential login is missing")
    return text.rstrip() + (
        f"\n\n## {label}\n"
        f"- Login: {login.group(1).strip()}\n"
        "- Password: \n"
        f"- Keychain: `{credential_ref}`\n"
        "- Verification: `UNVERIFIED`\n"
    )


def store_credential(program, label, markdown_path, verification, source_label=None):
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
    text = ensure_credential_section(text, label, source_label, secret_ref)
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


def store_login(label, markdown_path, login):
    if not login or len(login) > 320 or any(character.isspace() for character in login):
        raise ValueError("login must be one non-empty token")
    markdown_path = markdown_path.expanduser()
    text = markdown_path.read_text(encoding="utf-8")
    section = re.search(rf"(?ms)^## {re.escape(label)}\n.*?(?=^## |\Z)", text)
    if section is None or not re.search(r"(?m)^- Login: .*$", section.group()):
        raise ValueError("private credential section is missing")
    updated_section = re.sub(
        r"(?m)^- Login: .*$", "- Login: " + login, section.group(), count=1,
    )
    updated = text[:section.start()] + updated_section + text[section.end():]
    fd, temporary = tempfile.mkstemp(prefix=".affiliate-credentials.", dir=markdown_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(temporary, 0o600)
        os.replace(temporary, markdown_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if login not in markdown_path.read_text(encoding="utf-8"):
        raise ValueError("private Markdown login readback mismatch")
    return {"label": label, "private_markdown_login_state": "VERIFIED_NONEMPTY"}


def store_link(label, field, markdown_path, link):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9 -]{1,63} affiliate link", field):
        raise ValueError("invalid affiliate-link field")
    parsed = urlparse(link)
    if parsed.scheme != "https" or not parsed.netloc or any(character.isspace() for character in link):
        raise ValueError("affiliate link must be one HTTPS URL")
    markdown_path = markdown_path.expanduser()
    text = markdown_path.read_text(encoding="utf-8")
    section = re.search(rf"(?ms)^## {re.escape(label)}\n.*?(?=^## |\Z)", text)
    if section is None:
        raise ValueError("private credential section is missing")
    field_pattern = rf"(?m)^- {re.escape(field)}: .*$"
    if re.search(field_pattern, section.group()):
        updated_section = re.sub(field_pattern, f"- {field}: {link}", section.group(), count=1)
    else:
        updated_section = section.group().rstrip() + f"\n- {field}: {link}\n"
    updated = text[:section.start()] + updated_section + text[section.end():]
    fd, temporary = tempfile.mkstemp(prefix=".affiliate-links.", dir=markdown_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(updated)
        os.chmod(temporary, 0o600)
        os.replace(temporary, markdown_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    if link not in markdown_path.read_text(encoding="utf-8"):
        raise ValueError("private Markdown link readback mismatch")
    return {"label": label, "field": field, "private_markdown_link_state": "VERIFIED_NONEMPTY"}


def main():
    parser = argparse.ArgumentParser(prog="affiliate programs")
    parser.add_argument("command", choices=("list", "next", "credential", "store-credential", "store-login", "store-link"))
    parser.add_argument("--decision", action="append", default=[])
    parser.add_argument("--id")
    parser.add_argument("--label")
    parser.add_argument("--source-label")
    parser.add_argument("--field")
    parser.add_argument("--credential-ref")
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
    if args.command in ("credential", "store-credential", "store-login", "store-link"):
        if len(programs) != 1:
            return 3
        if args.credential_ref:
            programs[0] = {**programs[0], "credential_ref": args.credential_ref}
        if args.command == "credential":
            result = credential_state(programs[0])
        elif args.command == "store-login":
            if not args.label:
                raise ValueError("--label is required")
            result = store_login(args.label, args.private_markdown, sys.stdin.readline().strip())
        elif args.command == "store-link":
            if not args.label or not args.field:
                raise ValueError("--label and --field are required")
            result = store_link(
                args.label, args.field, args.private_markdown, sys.stdin.readline().strip(),
            )
        else:
            if not args.label:
                raise ValueError("--label is required")
            result = store_credential(
                programs[0], args.label, args.private_markdown, args.verification,
                args.source_label,
            )
    else:
        result = programs[:1] if args.command == "next" else programs
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if result else 3


if __name__ == "__main__":
    raise SystemExit(main())
