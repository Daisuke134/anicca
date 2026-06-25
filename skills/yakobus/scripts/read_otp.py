#!/usr/bin/env python3
"""read_otp.py — read the NEWEST 3-D Secure OTP (認証コード) from Gmail for a card payment.

VERIFIED 2026-06-25: code 067987 for 高速バスドットコム JPY 5,200 (MUFG Visa Secure).
gog interface confirmed against `gog gmail messages search --help` + verified working ref
~/.openclaw/skills/anicca-music-factory/scripts/04-upload-distrokid-cf.sh:115 (`--max`,`-a`,retry 5x).

Gotchas (verified + hardened after adversary review):
  * 認証コード emails GROUP into one thread → use MESSAGE-LEVEL search, NEWEST message (not thread).
  * Email arrives DELAYED → retry (default 6× × 4s).
  * Flag is `--max` (NOT --limit).
  * AMOUNT match is INTEGER-EQUALITY (substring would let ¥5,200 match ¥15,200 → wrong-charge OTP).
  * MERCHANT validated against the PARSED merchant field, not the whole body.
  * Body may be HTML (認証コード：<b>067987</b>) → strip tags before regex; accept 認証番号/ワンタイムパスワード.

Usage: read_otp.py [--account a@b] [--merchant 高速バス] [--amount 5200] [--minutes 15] [--tries 6]
Prints JSON {code, merchant, amount, msgId}; exits 1 if no fresh MATCHING code.
"""
import sys, json, re, subprocess, time

def arg(flag, default):
    return sys.argv[sys.argv.index(flag)+1] if flag in sys.argv else default

ACCT = arg("--account", "keiodaisuke@gmail.com")
MERCH = arg("--merchant", "")
AMOUNT = re.sub(r"\D", "", arg("--amount", ""))   # requested amount as bare integer string
MIN = arg("--minutes", "15")
TRIES = int(arg("--tries", "6"))

def gog(*a):
    try:
        return subprocess.run(["gog", *a], capture_output=True, text=True, timeout=40).stdout
    except Exception:
        return ""

def get_body(mid):
    raw = gog("gmail", "get", mid, "-a", ACCT, "--json")
    body = ""
    try:
        d = json.loads(raw)
        body = d.get("body") or (d.get("messages", [{}])[-1].get("body") if d.get("messages") else "")
    except Exception:
        body = ""
    if not body:
        body = gog("gmail", "get", mid, "-a", ACCT)   # plain-text fallback (verified distrokid pattern)
    return re.sub(r"<[^>]+>", " ", body)              # strip HTML tags so <b>code</b> doesn't break regex

def as_int(s):
    s = re.sub(r"\D", "", s or "")
    return int(s) if s else None

def scan():
    out = gog("gmail", "messages", "search", "-a", ACCT, "--json", "--max", "6",
              f"認証コード newer_than:{MIN}m")
    try:
        msgs = json.loads(out).get("messages") or []
    except Exception:
        msgs = []
    for m in msgs:  # newest first
        mid = m.get("id")
        if not mid:
            continue
        body = get_body(mid)
        code = re.search(r"(?:認証コード|認証番号|ワンタイムパスワード)[：:\s]*([0-9]{4,8})", body)
        if not code:
            continue
        merch = re.search(r"(?:加盟店名|ご利用加盟店)[：:\s]*([^\n　]{1,30})", body)
        amt = re.search(r"ご利用金額[：:\s]*([^\n]{0,20})", body)
        mtext = merch.group(1).strip() if merch else ""
        atext = amt.group(1).strip() if amt else ""
        # validate against PARSED fields, not whole body
        if MERCH and MERCH not in mtext:
            continue
        if AMOUNT and as_int(atext) != int(AMOUNT):   # INTEGER equality, not substring
            continue
        return {"code": code.group(1), "merchant": mtext, "amount": atext, "msgId": mid}
    return None

def main():
    for t in range(TRIES):
        hit = scan()
        if hit:
            print(json.dumps(hit, ensure_ascii=False)); return
        if t < TRIES - 1:
            time.sleep(4)
    print(json.dumps({"error": f"no matching 認証コード after {TRIES} tries",
                      "merchant_filter": MERCH, "amount_filter": AMOUNT})); sys.exit(1)

if __name__ == "__main__":
    main()
