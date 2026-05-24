#!/usr/bin/env python3
"""Decode Google Authenticator migration QR payload."""
import base64
import urllib.parse
import sys

data = "CigKFEpmZHJldU1QRXg2Tjk1VlVocGdlEgpkYWlzdWtlLW5hIAEoATACCkQKFPF6k7RLQ8+3fChjeo8pWo25nlvgEh5uYXJpdGEuZGFpc3VrZS5uZDRAbmFpc3QuYWMuanAaBk9wZW5BSSABKAEwAgomCgpJM6PPQURQvrjqEgpEYWlzdWtlMTM0GgZHaXRIdWIgASgBMAIKIgoUEDfm7d4TDP8OeBMfo6CTIzCGoN8SBGJhc2UgASgBMAIQAhgBIAA="
raw = base64.b64decode(data)

# Hand-rolled protobuf parser (varint + length-delimited)
def read_varint(buf, i):
    n, shift = 0, 0
    while True:
        b = buf[i]; i += 1
        n |= (b & 0x7F) << shift
        if not (b & 0x80): break
        shift += 7
    return n, i

def parse_otp_params(buf):
    fields = {}
    i = 0
    while i < len(buf):
        tag, i = read_varint(buf, i)
        wire = tag & 7
        fnum = tag >> 3
        if wire == 0:
            v, i = read_varint(buf, i)
            fields[fnum] = v
        elif wire == 2:
            ln, i = read_varint(buf, i)
            fields[fnum] = buf[i:i+ln]
            i += ln
        else:
            raise ValueError(f"unsupported wire={wire}")
    return fields

i = 0
entries = []
while i < len(raw):
    tag, i = read_varint(raw, i)
    wire = tag & 7
    fnum = tag >> 3
    if wire == 2:
        ln, i = read_varint(raw, i)
        sub = raw[i:i+ln]
        i += ln
        if fnum == 1:
            f = parse_otp_params(sub)
            secret_bytes = f.get(1, b"")
            name = f.get(2, b"").decode("utf-8", "replace")
            issuer = f.get(3, b"").decode("utf-8", "replace")
            algorithm = f.get(4, 1)  # SHA1
            digits = f.get(5, 1)
            otp_type = f.get(6, 2)
            secret_b32 = base64.b32encode(secret_bytes).decode().rstrip("=")
            entries.append({
                "name": name,
                "issuer": issuer,
                "secret_base32": secret_b32,
                "algorithm": ["UNSPECIFIED","SHA1","SHA256","SHA512","MD5"][algorithm] if algorithm < 5 else str(algorithm),
                "digits": [6,6,8][digits] if digits < 3 else "?",
                "otp_type": ["UNSPECIFIED","HOTP","TOTP"][otp_type] if otp_type < 3 else "?",
            })
    elif wire == 0:
        v, i = read_varint(raw, i)

import json
print(json.dumps(entries, ensure_ascii=False, indent=2))
