#!/usr/bin/env python3
"""Convert a camofox (Playwright storage-state.json) cookie jar to Netscape cookies.txt,
so yt-dlp can use `--cookies <file>` instead of `--cookies-from-browser chromium:...`.

Why: on this machine, Chromium cookie decryption requires macOS Keychain access to the
"<browser> Safe Storage" secret, and the headless/unattended session here does not carry
a valid Keychain search-list (see spec 2026-07-03-clip-loop-dual-instance-self-improve
-design.md §4.5) -- yt-dlp's own source (yt_dlp/cookies.py MacChromeCookieDecryptor) has
no non-Keychain fallback for macOS. camofox (Firefox-based) keeps cookies unencrypted in
storage-state.json, so this sidesteps the whole problem. 2026-07-04 タスク#8.

Usage:
    python3 export_camofox_cookies.py <storage_state.json> <out_cookies.txt>
"""
import json
import sys


def main():
    if len(sys.argv) != 3:
        print("usage: export_camofox_cookies.py <storage_state.json> <out_cookies.txt>", file=sys.stderr)
        sys.exit(1)
    src, dest = sys.argv[1], sys.argv[2]
    data = json.load(open(src))
    cookies = data.get("cookies", [])
    lines = ["# Netscape HTTP Cookie File", "# auto-generated from camofox storage-state.json, do not edit"]
    for c in cookies:
        domain = c.get("domain", "")
        if not domain:
            continue
        flag = "TRUE" if domain.startswith(".") else "FALSE"
        path = c.get("path", "/")
        secure = "TRUE" if c.get("secure") else "FALSE"
        expires = c.get("expires", -1)
        expires = "0" if expires is None or expires < 0 else str(int(expires))
        name = c.get("name", "")
        value = c.get("value", "")
        lines.append("\t".join([domain, flag, path, secure, expires, name, value]))
    with open(dest, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"wrote {len(lines) - 2} cookies to {dest}")


if __name__ == "__main__":
    main()
