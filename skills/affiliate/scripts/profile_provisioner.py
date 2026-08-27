#!/usr/bin/env python3
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


LOCALES = (("en", 9324), ("ja", 9325), ("x-en", 9326), ("impact-en", 9327))


class ProvisionError(Exception):
    pass


def ensure_directory(path, mode=0o700):
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise ProvisionError
    if not path.exists():
        path.mkdir(mode=mode, parents=True)
    elif path.stat().st_mode & 0o777 != mode:
        raise ProvisionError


def write_if_new(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ProvisionError
    if path.exists():
        if path.read_bytes() == payload:
            return
        raise ProvisionError
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
        os.replace(str(temporary_path), str(path))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def write_monotonic_receipt(path, payload):
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    if not path.exists():
        write_if_new(path, data)
        return
    if path.is_symlink() or not path.is_file():
        raise ProvisionError
    try:
        previous = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ProvisionError
    previous_locales = previous.get("locales")
    if previous.get("status") != "READY" or not isinstance(previous_locales, dict):
        raise ProvisionError
    if any(payload["locales"].get(name) != value for name, value in previous_locales.items()):
        raise ProvisionError
    if previous == payload:
        return
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(str(temporary_path), str(path))
    finally:
        temporary_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.expanduser()
    if root.is_symlink() or (root.exists() and not root.is_dir()):
        raise ProvisionError
    ensure_directory(root)
    locales = {}
    for locale, port in LOCALES:
        profile = root / locale
        ensure_directory(profile)
        locales[locale] = {"path": str(profile.absolute()), "cdp_port": port}
    payload = {"status": "READY", "locales": locales}
    write_monotonic_receipt(args.receipt.expanduser(), payload)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ProvisionError, OSError, ValueError):
        print("profile provisioner: failed closed", file=sys.stderr)
        sys.exit(1)
