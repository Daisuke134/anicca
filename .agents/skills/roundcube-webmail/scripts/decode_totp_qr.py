#!/usr/bin/env python3
"""Decode Google Authenticator export QR → TOTP secrets"""
import sys, base64, urllib.parse

def parse_varint(data, pos):
    result, shift = 0, 0
    while True:
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80): break
        shift += 7
    return result, pos

def parse_proto(data):
    pos, fields = 0, []
    while pos < len(data):
        tag, pos = parse_varint(data, pos)
        field_num, wire_type = tag >> 3, tag & 0x7
        if wire_type == 0:
            val, pos = parse_varint(data, pos); fields.append((field_num, 'varint', val))
        elif wire_type == 2:
            length, pos = parse_varint(data, pos)
            val = data[pos:pos+length]; pos += length; fields.append((field_num, 'bytes', val))
    return fields

def decode(url):
    params = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    raw = base64.b64decode(params['data'][0])
    for fn, wt, val in parse_proto(raw):
        if fn == 1 and wt == 'bytes':
            inner = parse_proto(val)
            secret = name = issuer = ''
            for ifn, iwt, iv in inner:
                if ifn == 1 and iwt == 'bytes': secret = base64.b32encode(iv).decode().rstrip('=')
                elif ifn == 2 and iwt == 'bytes': name = iv.decode('utf-8', errors='replace')
                elif ifn == 3 and iwt == 'bytes': issuer = iv.decode('utf-8', errors='replace')
            print(f"name={name} issuer={issuer}\nTOTP_SECRET={secret}\n")

if __name__ == '__main__':
    decode(sys.argv[1] if len(sys.argv) > 1 else input("otpauth-migration URL: "))
