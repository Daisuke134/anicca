#!/usr/bin/env python3
"""read_sms_otp.py — read an SMS OTP from the macOS Messages chat.db.

Dais's iPhone (number 08046270314) has Text Message Forwarding ON to this Mac,
so every SMS he receives also lands in ~/Library/Messages/chat.db. We poll it for
a fresh N-digit code → FULLY no-human (no manual relay), FREE (his own real SIM).
Email's read_otp.py has a twin job; this is the SMS twin.

Usage:
  read_sms_otp.py [--since-seconds 180] [--digits 6] [--match Instagram] [--timeout 120]

- --since-seconds: only consider SMS newer than now-N (default 180) so we never
  grab an old code. Call this RIGHT AFTER triggering "send code".
- --digits: code length to extract (default 6; some services use 5 or 8 → set it).
- --match: optional substring the SMS body must contain (e.g. Instagram, TikTok).
- prints the bare code to stdout (empty + exit 1 if none within timeout).

chat.db time = Apple epoch (2001-01-01) in nanoseconds: unix = date/1e9 + 978307200.
"""
import argparse, re, sqlite3, sys, time, os

DB = os.path.expanduser("~/Library/Messages/chat.db")
APPLE_EPOCH = 978307200  # 2001-01-01 → unix


def fetch(since_unix, match):
    """Return recent (unix_ts, text) SMS/iMessage rows newer than since_unix, newest first."""
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        cur = con.execute(
            "SELECT date, text FROM message "
            "WHERE text IS NOT NULL AND date IS NOT NULL "
            "ORDER BY date DESC LIMIT 40"
        )
        out = []
        for ad, text in cur.fetchall():
            ts = ad / 1_000_000_000 + APPLE_EPOCH
            if ts < since_unix:
                continue
            if match and match.lower() not in (text or "").lower():
                continue
            out.append((ts, text))
        return out
    finally:
        con.close()


def extract_code(text, digits):
    # prefer a code that follows a 認証コード/code/OTP cue; else any N-digit run
    cues = re.findall(r"(?:認証コード|コード|code|OTP|verification)[^\d]{0,8}(\d{%d})" % digits, text, re.I)
    if cues:
        return cues[0]
    m = re.findall(r"(?<!\d)(\d{%d})(?!\d)" % digits, text)
    return m[0] if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since-seconds", type=int, default=180)
    ap.add_argument("--digits", type=int, default=6)
    ap.add_argument("--match", default=None)
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()
    if not os.path.exists(DB):
        print("", end=""); sys.stderr.write("chat.db not found\n"); sys.exit(1)
    start = time.time()
    since = start - a.since_seconds
    deadline = start + a.timeout
    while time.time() < deadline:
        for ts, text in fetch(since, a.match):
            code = extract_code(text, a.digits)
            if code:
                print(code)
                return
        time.sleep(4)
    sys.stderr.write("no SMS OTP within timeout\n")
    sys.exit(1)


if __name__ == "__main__":
    main()
