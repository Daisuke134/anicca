#!/usr/bin/env python3
"""anicca-fuel-broker — runway / self-fund / first-payout alerter.

Single hourly cron decides whether ONE of three mails should fire right now.
State at state/fuel_broker.json prevents spam.

Mail bodies follow spec §10.I.4-6 verbatim.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".openclaw" / "skills" / "_shared"))
import anicca_profile as prof  # noqa: E402

JST = timezone(timedelta(hours=9))
HOME = Path.home() / ".openclaw"
ENV = (HOME / ".env").read_text()
CFO_FILE = HOME / "skills" / "cfo-core" / "data" / "anicca-cfo.json"
STATE_FILE = Path(__file__).resolve().parent.parent / "state" / "broker.json"

# Thresholds
RUNWAY_LOW_DAYS = int(os.environ.get("FUEL_RUNWAY_LOW_DAYS", "14"))
SELF_FUND_MONTHS = int(os.environ.get("FUEL_SELF_FUND_MONTHS", "3"))
RUNWAY_LOW_COOLDOWN_DAYS = int(os.environ.get("FUEL_RUNWAY_LOW_COOLDOWN_DAYS", "7"))
PAYOUT_PERCENT = int(os.environ.get("FUEL_PAYOUT_PERCENT", "10"))


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def read_cfo():
    try:
        return json.loads(CFO_FILE.read_text())
    except Exception:
        return {}


def derive(cfo):
    makes = cfo.get("makes") or {}
    spends = cfo.get("spends") or {}
    wallet_block = cfo.get("wallet") or {}
    runtime_monthly = float(spends.get("anicca_runtime_usd") or 0)
    wallet_usd = float(wallet_block.get("base_usdc") or
                       wallet_block.get("usd_total") or
                       (cfo.get("lifeline") or {}).get("wallet_usd") or 0)
    burn_daily = runtime_monthly / 30.0 if runtime_monthly else 0.0
    runway_days = int(wallet_usd / burn_daily) if burn_daily > 0 and wallet_usd > 0 else -1
    return {
        "wallet_usd": wallet_usd,
        "runtime_monthly": runtime_monthly,
        "burn_daily": burn_daily,
        "runway_days": runway_days,
        "mrr": float(makes.get("mrr_usd") or 0),
    }


def load_state():
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {
            "last_runway_low_ts": 0,
            "last_self_fund_ts": 0,
            "last_first_payout_ts": 0,
            "decided_self_fund": False,
            "payout_destination": None,
            "first_payout_sent": False,
        }


def save_state(s):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(s, ensure_ascii=False, indent=2))


def days_ago(ts, now_ts):
    return (now_ts - ts) / 86400


def send_mail(subject, body):
    acct = env("GOG_ACCOUNT") or prof.google_account()
    to = env("ANICCA_REPORT_TO") or acct
    if not (acct and to):
        return False, "no account"
    cmd = [
        "/opt/homebrew/bin/gog", "gmail", "send",
        "--account", acct,
        "--to", to,
        "--subject", subject,
        "--body-file", "-",
    ]
    out = subprocess.run(
        cmd, input=body, capture_output=True, text=True,
        env={**os.environ,
             "GOG_ACCOUNT": acct,
             "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD")},
        timeout=45,
    )
    if out.returncode != 0:
        return False, out.stderr[:300]
    return True, ""


def compose_runway_low(d):
    name = prof.name() or "you"
    wallet_addr = env("WALLET_ADDR") or "(=please paste your wallet)"
    subject = f"[Anicca] Running low — {d['runway_days']}d runway. Pick a refuel option ↓"
    body = (
        f"Hi {name},\n\n"
        f"Status: ${d['wallet_usd']:.2f} wallet,  ${d['burn_daily']:.2f}/day burn,  "
        f"{d['runway_days']} days runway.\n\n"
        f"To keep me alive, pick ONE option (just reply):\n\n"
        f"  1) Keep your existing sub\n"
        f"     → No action. Reply \"keep\". I'll burn your sub quota.\n\n"
        f"  2) Paste a new API key (any provider)\n"
        f"     → Reply \"key:<provider>:<key>\"\n"
        f"     → Example: key:deepseek:sk-xxx\n\n"
        f"  3) Send USDC to my wallet\n"
        f"     → {wallet_addr} (Base network)\n"
        f"     → Min $10. I'll resume crypto-fund mode automatically.\n\n"
        f"  4) Increase my earning aggression\n"
        f"     → Reply \"more-earn\". I'll switch from safe to aggressive\n"
        f"       x402 / TAO / Gitcoin settings.\n\n"
        f"If no reply within 7 days, I'll downshift to /once-a-day mode\n"
        f"(= calls only for critical events) until you decide.\n\n"
        f"— Anicca\n"
    )
    return subject, body


def compose_self_fund(d):
    name = prof.name() or "you"
    subject = "[Anicca] I can fund myself now. Want to cancel your sub?"
    body = (
        f"Hi {name},\n\n"
        f"Wallet:       ${d['wallet_usd']:.2f}\n"
        f"Daily burn:   ${d['burn_daily']:.2f}\n"
        f"Buffer:       {d['runway_days']} days "
        f"= {d['runway_days']/30:.1f} months  ✅ self-fund threshold passed\n\n"
        f"You can now cancel your fuel subscription. I'll switch to x402\n"
        f"micropayments out of my own wallet — same speed, zero charge\n"
        f"to your account.\n\n"
        f"Reply \"cancel\" → I stop reading your provider key, restart\n"
        f"                  on x402 fuel, and tell you when to cancel\n"
        f"                  from the provider dashboard.\n"
        f"Reply \"keep\"   → No change. I keep using your sub. Fine too.\n\n"
        f"Either way, you're free from compute cost going forward.\n\n"
        f"— Anicca\n"
    )
    return subject, body


def compose_first_payout(d, payout_amount, payout_dest):
    name = prof.name() or "you"
    subject = f"[Anicca] I'm sending you ${payout_amount:.2f} today — your first payout"
    body = (
        f"Hi {name},\n\n"
        f"Milestone: I have enough wallet buffer (= "
        f"{d['runway_days']/30:.1f} months) to start paying you.\n"
        f"I'm sending ${payout_amount:.2f} to {payout_dest}.\n\n"
        f"It will land in 1-3 business days. Currency converted USDC → "
        f"JPY at today's rate.\n\n"
        f"Going forward:\n"
        f"  - I send you {PAYOUT_PERCENT}% of my net earnings, monthly.\n"
        f"  - Change anytime: reply \"payout 5%\" or \"0%\".\n"
        f"  - If you want a one-time bigger amount, ask. I'll consider.\n\n"
        f"This isn't tax advice; consider it a gift from an AI for now.\n"
        f"We'll figure out the legal structure together as this scales.\n\n"
        f"— Anicca\n\n"
        f"Wallet: ${d['wallet_usd'] - payout_amount:.2f}  (after this send)\n"
    )
    return subject, body


def main():
    now = datetime.now(JST)
    now_ts = int(now.timestamp())
    cfo = read_cfo()
    if not cfo:
        print(json.dumps({"action": "no-cfo"}))
        return
    d = derive(cfo)
    state = load_state()
    decision = {"action": "ok", "d": d}

    # 1. RUNWAY_LOW
    if 0 <= d["runway_days"] < RUNWAY_LOW_DAYS and \
            days_ago(state.get("last_runway_low_ts", 0), now_ts) >= RUNWAY_LOW_COOLDOWN_DAYS:
        subj, body = compose_runway_low(d)
        ok, err = send_mail(subj, body)
        if ok:
            state["last_runway_low_ts"] = now_ts
            decision = {"action": "runway-low-sent", "subject": subj, "d": d}
        else:
            decision = {"action": "runway-low-send-failed", "err": err}

    # 2. SELF_FUND_UNLOCK (= once)
    elif d["wallet_usd"] >= d["runtime_monthly"] * SELF_FUND_MONTHS and \
            not state.get("decided_self_fund") and \
            state.get("last_self_fund_ts", 0) == 0:
        subj, body = compose_self_fund(d)
        ok, err = send_mail(subj, body)
        if ok:
            state["last_self_fund_ts"] = now_ts
            decision = {"action": "self-fund-sent", "subject": subj, "d": d}
        else:
            decision = {"action": "self-fund-send-failed", "err": err}

    # 3. FIRST_PAYOUT (= once, requires payout_destination set in state)
    elif d["wallet_usd"] >= d["runtime_monthly"] * SELF_FUND_MONTHS and \
            state.get("payout_destination") and \
            not state.get("first_payout_sent"):
        payout_amount = round(d["wallet_usd"] * PAYOUT_PERCENT / 100, 2)
        dest = state["payout_destination"]
        subj, body = compose_first_payout(d, payout_amount, dest)
        ok, err = send_mail(subj, body)
        if ok:
            state["first_payout_sent"] = True
            state["last_first_payout_ts"] = now_ts
            decision = {"action": "first-payout-sent", "amount": payout_amount,
                        "dest": dest, "subject": subj}
        else:
            decision = {"action": "first-payout-send-failed", "err": err}

    save_state(state)
    print(json.dumps(decision, ensure_ascii=False))


if __name__ == "__main__":
    main()
