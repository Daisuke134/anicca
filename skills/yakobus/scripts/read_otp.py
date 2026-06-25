#!/usr/bin/env python3
"""read_otp.py — read the NEWEST 3-D Secure OTP (認証コード) from Gmail for a card payment.

VERIFIED 2026-06-25: read code 067987 for 高速バスドットコム JPY 5,200 and cleared MUFG Visa Secure.
gog interface confirmed against `gog gmail messages search --help` + the verified working script
~/.openclaw/skills/anicca-music-factory/scripts/04-upload-distrokid-cf.sh:115 (uses `--max`, `-a`, retry 5x).

CRITICAL gotchas (verified):
  * MUFG/issuer 認証コード emails GROUP into one Gmail thread. `gog gmail get <thread>` returns the
    OLDEST (dead) code → use MESSAGE-LEVEL search, take the NEWEST message id, get THAT message.
  * The OTP email arrives with a DELAY → RETRY (the distrokid pattern loops 5x over ~30s). A single
    immediate search usually finds nothing.
  * Flag is `--max` (NOT `--limit`). Validate merchant/amount before trusting the code.

Usage: read_otp.py [--account a@b.com] [--merchant 高速バス] [--amount 5,200] [--minutes 15] [--tries 6]
Prints JSON: {code, merchant, amount, msgId}. Exits 1 if no fresh matching code after retries.
Requires `gog` CLI (with the account already authed).
"""
import sys, json, re, subprocess, time

def arg(flag, default):
    return sys.argv[sys.argv.index(flag)+1] if flag in sys.argv else default

ACCT = arg("--account", "redacted@example.invalid")
MERCH = arg("--merchant", "")
AMOUNT = arg("--amount", "")
MIN = arg("--minutes", "15")
TRIES = int(arg("--tries", "6"))

def gog(*a):
    try:
        return subprocess.run(["gog", *a], capture_output=True, text=True, timeout=40).stdout
    except Exception:
        return ""

def get_body(mid):
    raw = gog("gmail", "get", mid, "-a", ACCT, "--json")
    try:
        d = json.loads(raw)
        b = d.get("body") or (d.get("messages", [{}])[-1].get("body") if d.get("messages") else "")
        if b:
            return b
    except Exception:
        pass
    # fall back to plain text (the verified distrokid pattern reads get as text)
    return gog("gmail", "get", mid, "-a", ACCT)

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
        code = re.search(r"認証コード[：:\s]*([0-9]{4,8})", body)
        if not code:
            continue
        merch = re.search(r"(?:加盟店名|ご利用加盟店)[：:\s]*([^\n]{0,30})", body)
        amt = re.search(r"ご利用金額[：:\s]*([^\n]{0,20})", body)
        mtext = merch.group(1).strip() if merch else ""
        atext = amt.group(1).strip() if amt else ""
        if MERCH and MERCH not in body:
            continue
        if AMOUNT and AMOUNT.replace(",", "") not in atext.replace(",", ""):
            continue
        return {"code": code.group(1), "merchant": mtext, "amount": atext, "msgId": mid}
    return None

def main():
    for t in range(TRIES):
        hit = scan()
        if hit:
            print(json.dumps(hit, ensure_ascii=False))
            return
        if t < TRIES - 1:
            time.sleep(4)
    print(json.dumps({"error": f"no matching 認証コード after {TRIES} tries", "merchant_filter": MERCH}))
    sys.exit(1)

if __name__ == "__main__":
    main()
