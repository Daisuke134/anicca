#!/usr/bin/env python3
"""Decode a Google Authenticator export QR payload into per-account TOTP secrets.

Usage:
  zbarimg --raw OTP-export.png | python3 decode-otp-migration.py
  echo "otpauth-migration://offline?data=..." | python3 decode-otp-migration.py
  python3 decode-otp-migration.py "otpauth-migration://offline?data=..."

Outputs JSON: [{name, issuer, secret_base32, algorithm, digits, otp_type}, ...]

Use the `secret_base32` value as `NAIST_TOTP_SECRET` (or any other site's
TOTP secret) in `~/.openclaw/state/naist/<slug>/secrets.env`.

Security: this script never persists the input or output. Pipe the secrets
straight into your encrypted env file (chmod 600). Never commit them.
"""
import base64
import json
import re
import sys
import urllib.parse


def read_input() -> str:
    if len(sys.argv) > 1 and sys.argv[1] not in ("-", ""):
        return sys.argv[1]
    return sys.stdin.read().strip()


def extract_data_param(s: str) -> str:
    """Accept either a raw `data=...` base64 string or a full otpauth-migration URI."""
    s = s.strip()
    if s.startswith("otpauth-migration://"):
        q = urllib.parse.urlparse(s).query
        return urllib.parse.parse_qs(q)["data"][0]
    return s


def read_varint(buf: bytes, i: int):
    n, shift = 0, 0
    while True:
        b = buf[i]; i += 1
        n |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return n, i


def parse_otp_params(buf: bytes) -> dict:
    fields, i = {}, 0
    while i < len(buf):
        tag, i = read_varint(buf, i)
        wire, fnum = tag & 7, tag >> 3
        if wire == 0:
            v, i = read_varint(buf, i)
            fields[fnum] = v
        elif wire == 2:
            ln, i = read_varint(buf, i)
            fields[fnum] = buf[i:i + ln]
            i += ln
        else:
            raise ValueError(f"unsupported wire={wire}")
    return fields


def main() -> int:
    raw_input = read_input()
    if not raw_input:
        print("error: no input. Pipe `zbarimg --raw OTP-export.png` or pass URI/data string.", file=sys.stderr)
        return 64

    data_b64 = extract_data_param(raw_input)
    # url-decode (the data param is usually percent-encoded)
    data_b64 = urllib.parse.unquote(data_b64)
    # base64 may be missing padding
    data_b64 += "=" * (-len(data_b64) % 4)
    raw = base64.b64decode(data_b64)

    entries, i = [], 0
    while i < len(raw):
        tag, i = read_varint(raw, i)
        wire, fnum = tag & 7, tag >> 3
        if wire == 2:
            ln, i = read_varint(raw, i)
            sub = raw[i:i + ln]; i += ln
            if fnum == 1:
                f = parse_otp_params(sub)
                secret_bytes = f.get(1, b"")
                entries.append({
                    "name":         f.get(2, b"").decode("utf-8", "replace"),
                    "issuer":       f.get(3, b"").decode("utf-8", "replace"),
                    "secret_base32": base64.b32encode(secret_bytes).decode().rstrip("="),
                    "algorithm":    ["UNSPECIFIED", "SHA1", "SHA256", "SHA512", "MD5"][f.get(4, 1)] if f.get(4, 1) < 5 else str(f.get(4, 1)),
                    "digits":       [6, 6, 8][f.get(5, 1)] if f.get(5, 1) < 3 else "?",
                    "otp_type":     ["UNSPECIFIED", "HOTP", "TOTP"][f.get(6, 2)] if f.get(6, 2) < 3 else "?",
                })
        elif wire == 0:
            _, i = read_varint(raw, i)

    print(json.dumps(entries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
