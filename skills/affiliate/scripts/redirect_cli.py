#!/usr/bin/env python3
"""Initialize the private redirect secret and mint signed placement URLs."""

import argparse
import hashlib
import hmac
import os
import re
import secrets
import tempfile
from pathlib import Path
from urllib.parse import urlencode


VALUE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}$")
HEADING = "## Affiliate Redirect"


def private_section(path):
    text = path.read_text(encoding="utf-8")
    match = re.search(r"(?ms)^## Affiliate Redirect\n.*?(?=^## |\Z)", text)
    if not match:
        raise ValueError("affiliate redirect private section is missing")
    values = dict(re.findall(r"(?m)^- ([^:]+): `([^`]+)`$", match.group()))
    return text, values


def atomic_write(path, text):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def initialize(path, base_url):
    path = path.expanduser()
    text = path.read_text(encoding="utf-8") if path.exists() else "# Affiliate Credentials (local only)\n"
    try:
        if not path.exists():
            raise ValueError("affiliate redirect private section is missing")
        _, values = private_section(path)
        if len(values.get("Signing secret", "")) < 64:
            raise ValueError("stored signing secret is invalid")
        return {"state": "ALREADY_INITIALIZED", "private_markdown": str(path)}
    except ValueError as error:
        if "section is missing" not in str(error):
            raise
    block = (
        f"\n\n{HEADING}\n\n"
        f"- Signing secret: `{secrets.token_hex(32)}`\n"
        f"- Base URL: `{base_url.rstrip('/')}`\n"
        "- Verification: `SAVED_NOT_DEPLOYED`\n"
    )
    atomic_write(path, text.rstrip() + block)
    return {"state": "INITIALIZED", "private_markdown": str(path)}


def mint(path, fields):
    _, values = private_section(path.expanduser())
    secret = values.get("Signing secret", "")
    base_url = values.get("Base URL", "").rstrip("/")
    if len(secret) < 64 or not base_url.startswith("https://"):
        raise ValueError("redirect private configuration is invalid")
    if any(not VALUE.fullmatch(value) for value in fields.values()):
        raise ValueError("invalid attribution field")
    material = "\n".join(fields.values())
    signature = hmac.new(secret.encode(), material.encode(), hashlib.sha256).hexdigest()
    return f"{base_url}/{fields['offer']}?{urlencode({**fields, 'sig': signature})}"


def main():
    parser = argparse.ArgumentParser(prog="affiliate redirect")
    parser.add_argument("command", choices=("init", "mint"))
    parser.add_argument("--private-markdown", type=Path, default=Path("~/.config/anicca/affiliate-credentials.md"))
    parser.add_argument("--base-url", default="https://anicca-proxy-staging.up.railway.app/api/affiliate/go")
    for field in ("offer", "placement", "locale", "experiment", "variant"):
        parser.add_argument(f"--{field}")
    args = parser.parse_args()
    if args.command == "init":
        print(initialize(args.private_markdown, args.base_url)["state"])
        return 0
    fields = {name: getattr(args, name) for name in ("offer", "placement", "locale", "experiment", "variant")}
    if any(value is None for value in fields.values()):
        raise ValueError("all attribution fields are required")
    print(mint(args.private_markdown, fields))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
