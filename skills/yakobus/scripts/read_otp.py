#!/usr/bin/env python3
"""read_otp.py — read the NEWEST 3-D Secure OTP (認証コード) from Gmail for a card payment.

VERIFIED 2026-06-25: read code 067987 for 高速バスドットコム JPY 5,200 and cleared MUFG Visa Secure.

CRITICAL (verified gotcha): MUFG/issuer 認証コード emails GROUP into one Gmail thread. `gog gmail get
<thread>` returns the OLDEST (dead) code. So use MESSAGE-LEVEL search, take the NEWEST message id,
get THAT message, and VALIDATE merchant/amount before trusting the code.

Usage: read_otp.py [--account a@b.com] [--merchant 高速バス] [--minutes 15]
Prints JSON: {code, merchant, amount, msgId}. Exits 1 if no fresh code.
Requires `gog` CLI (with ~/.openclaw/.env sourced for account auth).
"""
import sys, json, re, subprocess

def arg(flag, default):
    return sys.argv[sys.argv.index(flag)+1] if flag in sys.argv else default

ACCT = arg("--account", "keiodaisuke@gmail.com")
MERCH = arg("--merchant", "")
MIN = arg("--minutes", "15")

def gog(*a):
    return subprocess.run(["gog", *a], capture_output=True, text=True, timeout=40).stdout

def main():
    out = gog("gmail", "messages", "search", "--account", ACCT, "--json", "--limit", "6",
              f"認証コード newer_than:{MIN}m")
    try:
        msgs = (json.loads(out).get("messages") or [])
    except Exception:
        msgs = []
    if not msgs:
        print(json.dumps({"error": "no fresh 認証コード message"})); sys.exit(1)
    # newest first; scan for one matching merchant (if given) with a code
    for m in msgs:
        mid = m.get("id")
        body = ""
        raw = gog("gmail", "get", mid, "--account", ACCT, "--json")
        try:
            d = json.loads(raw); body = d.get("body") or (d.get("messages", [{}])[-1].get("body") or "")
        except Exception:
            body = raw
        code = re.search(r"認証コード[：:\s]*([0-9]{4,8})", body)
        merch = re.search(r"(?:加盟店名|ご利用加盟店)[：:\s]*([^\n]{0,30})", body)
        amt = re.search(r"ご利用金額[：:\s]*([^\n]{0,20})", body)
        mtext = (merch.group(1).strip() if merch else "")
        if code and (not MERCH or MERCH in body):
            print(json.dumps({"code": code.group(1), "merchant": mtext,
                              "amount": (amt.group(1).strip() if amt else ""), "msgId": mid},
                             ensure_ascii=False))
            return
    print(json.dumps({"error": "no matching code", "checked": len(msgs)})); sys.exit(1)

if __name__ == "__main__":
    main()
