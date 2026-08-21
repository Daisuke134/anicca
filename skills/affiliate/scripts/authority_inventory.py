#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import pwd
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse


CHALLENGES = {"CAPTCHA", "KYC", "CONTRACT"}
KEYCHAIN_PART = re.compile(r"^[A-Za-z0-9._-]+$")


class InputError(Exception):
    pass


def load_object(path):
    try:
        value = json.loads(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise InputError
    if not isinstance(value, dict):
        raise InputError
    return value


def load_request(path):
    try:
        raw = path.read_bytes()
        value = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        raise InputError
    if not isinstance(value, dict):
        raise InputError
    return value, hashlib.sha256(raw).hexdigest()


def required_text(value, key):
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise InputError
    return item


def canonical_secret_ref(value):
    if not isinstance(value, str) or any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise InputError
    if "?" in value or "#" in value:
        raise InputError
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        raise InputError
    if (
        parsed.scheme != "keychain"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or not KEYCHAIN_PART.fullmatch(parsed.netloc or "")
    ):
        raise InputError
    parts = parsed.path.split("/")
    if len(parts) != 2 or parts[0] or not KEYCHAIN_PART.fullmatch(parts[1]):
        raise InputError
    return "keychain://" + parsed.netloc + "/" + parts[1]


def write_receipt(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=str(path.parent))
    temporary_path = Path(temporary)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
        os.replace(str(temporary_path), str(path))
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def keychain_readback(secret_ref):
    parsed = urlparse(secret_ref)
    try:
        home = pwd.getpwuid(os.getuid()).pw_dir
    except (KeyError, OSError):
        return False
    environment = {"PATH": "/usr/bin:/bin", "LANG": "C", "LC_ALL": "C", "HOME": home}
    try:
        result = subprocess.run(
            [
                "/usr/bin/security",
                "find-generic-password",
                "-s",
                parsed.netloc,
                "-a",
                parsed.path[1:],
                "-w",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            timeout=10,
            check=False,
            env=environment,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    write_receipt(args.receipt, {"status": "IN_PROGRESS"})
    request, request_sha256 = load_request(args.request)
    intent_id = required_text(request, "intent_id")
    capability = required_text(request, "capability")
    challenge = request.get("external_challenge")
    if challenge is not None and (
        not isinstance(challenge, str) or challenge not in CHALLENGES
    ):
        raise InputError
    if challenge is not None:
        write_receipt(
            args.receipt,
            {
                "status": "EXTERNAL_CHALLENGE",
                "challenge": challenge,
                "request_sha256": request_sha256,
            },
        )
        return 0
    require_readback = request.get("require_readback", False)
    if not isinstance(require_readback, bool):
        raise InputError

    matches = []
    if args.bundle is not None:
        bundle = load_object(args.bundle)
        authorities = bundle.get("authorities")
        if not isinstance(authorities, list):
            raise InputError
        for authority in authorities:
            if not isinstance(authority, dict):
                raise InputError
            authority_intent = required_text(authority, "intent_id")
            authority_capability = required_text(authority, "capability")
            secret_ref = canonical_secret_ref(authority.get("secret_ref"))
            if authority_intent == intent_id and authority_capability == capability:
                matches.append(secret_ref)
    if len(matches) > 1:
        raise InputError

    if len(matches) == 1:
        if require_readback and not keychain_readback(matches[0]):
            write_receipt(
                args.receipt,
                {
                    "status": "EXTERNAL_CHALLENGE",
                    "challenge": "KEYCHAIN_ACCESS_REQUIRED",
                    "intent_id": intent_id,
                    "capability": capability,
                    "secret_ref": matches[0],
                    "request_sha256": request_sha256,
                },
            )
            return 0
        result = {
            "status": "AUTHORIZED" if require_readback else "REFERENCE_BOUND",
            "intent_id": intent_id,
            "capability": capability,
            "secret_ref": matches[0],
            "request_sha256": request_sha256,
        }
        if require_readback:
            result["readback_status"] = "VERIFIED_PRESENT"
    else:
        result = {
            "status": "EXTERNAL_CHALLENGE",
            "challenge": "AUTHORITY_REQUIRED",
            "request_sha256": request_sha256,
        }
    write_receipt(args.receipt, result)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (InputError, OSError):
        print("authority inventory: rejected", file=sys.stderr)
        sys.exit(1)
