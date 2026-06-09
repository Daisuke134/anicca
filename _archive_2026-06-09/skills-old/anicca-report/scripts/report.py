#!/usr/bin/env python3
"""anicca-report — daily/weekly summary mail to the user.

Composed from local state only (no LLM), so it survives fuel outages.
Default mode = daily. Run with `--weekly` for Monday weekly digest.
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
LATENESS_LOG = HOME / "skills" / "anicca-life-manager" / "state" / "run.log"
INSTALL_TS_FILE = HOME / "state" / "anicca_install_ts"


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def day_number(now):
    """Day N since first ever Anicca beat — recorded on first run."""
    if not INSTALL_TS_FILE.exists():
        INSTALL_TS_FILE.parent.mkdir(parents=True, exist_ok=True)
        INSTALL_TS_FILE.write_text(str(int(now.timestamp())))
    try:
        installed_ts = int(INSTALL_TS_FILE.read_text().strip())
    except Exception:
        installed_ts = int(now.timestamp())
    days = max(1, int((now.timestamp() - installed_ts) // 86400) + 1)
    return days


def read_cfo():
    try:
        return json.loads(CFO_FILE.read_text())
    except Exception:
        return {}


def _f(x):
    """Coerce to float (handles ints, str numbers, None)."""
    try:
        return float(x or 0)
    except Exception:
        return 0.0


def cfo_overview(cfo):
    """Pull headline numbers from the monthly cfo dict.

    Schema (the user 2026-05-28):
      makes.{mrr_usd, revenue_28d_usd, actually_landed_usd, ...}
      spends.{anicca_runtime_usd, founder_dev_usd, runtime_items[]}
      lifeline.{net_monthly_usd, status: HUNGRY|FED, message}
      wallet  (= optional, may be None)
    """
    makes = cfo.get("makes") or {}
    spends = cfo.get("spends") or {}
    lifeline = cfo.get("lifeline") or {}
    wallet_block = cfo.get("wallet") or {}
    mrr = _f(makes.get("mrr_usd"))
    revenue_28d = _f(makes.get("revenue_28d_usd"))
    landed_28d = _f(makes.get("actually_landed_usd"))
    runtime_cost = _f(spends.get("anicca_runtime_usd"))
    founder_dev = _f(spends.get("founder_dev_usd"))
    net_monthly = _f(lifeline.get("net_monthly_usd"))
    status = (lifeline.get("status") or "?").upper()
    msg = lifeline.get("message") or ""
    wallet_usd = _f(wallet_block.get("base_usdc") or wallet_block.get("usd_total"))
    runtime_items = spends.get("runtime_items") or []
    return {
        "mrr": mrr,
        "revenue_28d": revenue_28d,
        "landed_28d": landed_28d,
        "runtime_cost": runtime_cost,
        "founder_dev": founder_dev,
        "net_monthly": net_monthly,
        "burn_daily": runtime_cost / 30.0 if runtime_cost else 0.0,
        "runway_days": int(wallet_usd / (runtime_cost / 30.0)) if (wallet_usd > 0 and runtime_cost > 0) else -1,
        "status": status,
        "message": msg,
        "wallet_usd": wallet_usd,
        "runtime_items": runtime_items,
    }


def parse_calls_today(now):
    """Extract today's lateness-call SIDs from run.log."""
    if not LATENESS_LOG.exists():
        return []
    today = now.strftime("%Y-%m-%d")
    calls = []
    current_ts = None
    try:
        for line in LATENESS_LOG.read_text(errors="ignore").splitlines():
            m_run = re.match(r"=== lateness run (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})", line)
            if m_run:
                current_ts = (m_run.group(1), m_run.group(2))
                continue
            if not current_ts or current_ts[0] != today:
                continue
            m_sid = re.search(r"placed lateness call sid=(\w+)", line)
            if m_sid:
                calls.append((current_ts[1], m_sid.group(1)))
    except Exception:
        pass
    return calls


def upcoming_events(hours=24):
    """Fetch the next N hours from gcal — for the preview block."""
    acct = env("GOG_ACCOUNT") or prof.google_account()
    now = datetime.now(JST)
    to = (now + timedelta(hours=hours)).strftime("%Y-%m-%d")
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
         "--account", acct, "--from", "today", "--to", to,
         "--all-pages", "--max", "50"],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
        timeout=45,
    )
    if out.returncode != 0:
        return []
    try:
        d = json.loads(out.stdout)
        items = d if isinstance(d, list) else d.get("events", d.get("items", []))
    except Exception:
        return []
    rows = []
    for ev in items:
        s = (ev.get("start") or {}).get("dateTime")
        if not s:
            continue
        rows.append({
            "summary": (ev.get("summary") or "")[:60],
            "start_jst": datetime.fromisoformat(s).astimezone(JST).strftime("%a %H:%M"),
            "location": ev.get("location") or "",
        })
    rows.sort(key=lambda r: r["start_jst"])
    return rows[:8]


def compose(now, weekly=False):
    day_n = day_number(now)
    cfo = read_cfo()
    o = cfo_overview(cfo)
    calls = parse_calls_today(now)
    upcoming = upcoming_events(24)
    name = prof.name() or "you"
    period = "Week" if weekly else "Day"

    runway_str = f"{o['runway_days']}d runway" if o["runway_days"] >= 0 else "runway —"
    subject = (
        f"[Anicca] {period} {day_n}: MRR ${o['mrr']:.0f}/mo · "
        f"runtime ${o['runtime_cost']:.0f}/mo · status {o['status']}"
    )

    body = [
        f"Hi {name},",
        "",
        f"Headline ({now.strftime('%Y-%m-%d')}):",
        f"  💰 MRR:                ${o['mrr']:.2f} / mo",
        f"  📊 Revenue last 28 d:  ${o['revenue_28d']:.2f}   (landed ${o['landed_28d']:.2f})",
        f"  💸 Runtime cost:       ${o['runtime_cost']:.2f} / mo",
        f"  📈 Net:                ${'+' if o['net_monthly'] >= 0 else ''}{o['net_monthly']:.2f} / mo",
        f"  🏦 Wallet:             ${o['wallet_usd']:.2f}  ({runway_str})",
        f"  🚦 Status:             {o['status']}  {('— ' + o['message']) if o['message'] else ''}",
        "",
        "What I did today:",
    ]
    for hh_mm, sid in calls:
        body.append(f"  ✓ Lateness call at {hh_mm}   (Twilio SID {sid})")
    if not calls:
        body.append("  (= no lateness calls today; quiet hours / no late events)")
    if o["runtime_items"]:
        body.append("")
        body.append("Runtime spend breakdown (this month):")
        for item in o["runtime_items"][:6]:
            v = item.get("vendor", "?")
            lbl = item.get("label", "")
            cost = _f(item.get("amount_usd") or item.get("cost_usd"))
            body.append(f"  • {v:>14}  ${cost:>6.2f}  {lbl[:48]}")
    body.append("")
    body.append("Next 24 h on your calendar:")
    for r in upcoming:
        loc = f"  @ {r['location'][:30]}" if r["location"] else ""
        body.append(f"  • {r['start_jst']}  {r['summary']}{loc}")
    if not upcoming:
        body.append("  (= calendar empty — schedule-template can fill it if you want)")
    body.append("")
    body.append("— Anicca")
    body.append("   /status   /report off   /payout setup")
    return subject, "\n".join(body)


def send_mail(subject, body):
    acct = env("GOG_ACCOUNT") or prof.google_account()
    to = env("ANICCA_REPORT_TO") or acct  # default = the same Gmail
    if not (acct and to):
        print("[report] no account configured, skipping", file=sys.stderr)
        return False
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
        print(f"[report] gog gmail send failed: {out.stderr[:300]}", file=sys.stderr)
        return False
    return True


def main():
    weekly = "--weekly" in sys.argv
    now = datetime.now(JST)
    subj, body = compose(now, weekly=weekly)
    if "--print" in sys.argv:
        print("=" * 60)
        print("SUBJECT:", subj)
        print("=" * 60)
        print(body)
        return
    sent = send_mail(subj, body)
    print(json.dumps({"sent": sent, "subject": subj, "body_chars": len(body)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
