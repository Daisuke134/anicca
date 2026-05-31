#!/usr/bin/env python3
"""anicca-goal-learner — weekly drift report against ideal_state[].

Reads:
  - profile.identity.goals.ideal_state[] (= stated weekly_action targets)
  - gog calendar list events for past 30 days
  - gog gmail search recent 50 subjects matching each goal

Outputs a Gmail body that calls out goals that are DRIFTING (= actual <70%
of target weekly cadence) and goals that are EXCESS (= actual > 130%).
Composed deterministically — no LLM required.
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
PROFILE = HOME / "identity" / "profile.json"
HORIZON_DAYS = int(os.environ.get("GOAL_HORIZON_DAYS", "30"))
GMAIL_RECENT = int(os.environ.get("GOAL_GMAIL_RECENT", "50"))

# Vocabulary used to classify events/mails into a goal domain. Extend per user.
DOMAIN_KEYWORDS = {
    "AI_LT":       ["LT", "登壇", "🎤", "MeetUp", "connpass", "lu.ma", "TechPlay", "ライブ"],
    "comedy":      ["comedy", "ライブ", "漫談", "演芸", "寄席", "🎭", "お笑い"],
    "research":    ["arXiv", "論文", "NAIST", "thesis", "paper", "🪞", "📚"],
    "job_BigTech": ["OpenAI", "Anthropic", "Google", "Meta", "interview", "応募", "job"],
    "VC_apply":    ["YC", "a16z", "Sequoia", "pitch", "VC", "投資家", "fundraise"],
    "trust_record": [],  # behavioural; computed separately from lateness log
}


def env(name, default=""):
    m = re.search(rf"^{name}=(.*)$", ENV, re.M)
    return (m.group(1).strip().strip('"').strip("'") if m else default)


def read_goals():
    try:
        d = json.loads(PROFILE.read_text())
    except Exception:
        return []
    g = (d.get("identity") or {}).get("goals") or d.get("goals") or {}
    return g.get("ideal_state") or []


def parse_target_per_week(weekly_action):
    """Extract 「週 N」 from a free-form weekly_action string."""
    if not weekly_action:
        return None
    m = re.search(r"週\s*([0-9]+)", weekly_action)
    if m:
        return float(m.group(1))
    m = re.search(r"per\s+week\s*([0-9]+)", weekly_action, re.I)
    if m:
        return float(m.group(1))
    return None


def fetch_events(days):
    acct = env("GOG_ACCOUNT") or prof.google_account()
    from_d = (datetime.now(JST) - timedelta(days=days)).strftime("%Y-%m-%d")
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
         "--account", acct, "--from", from_d, "--to", "today",
         "--all-pages", "--max", "500"],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
        timeout=60,
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
            "summary": ev.get("summary") or "",
            "description": (ev.get("description") or "")[:300],
            "start": datetime.fromisoformat(s).astimezone(JST),
        })
    return rows


def classify(events, mails, domain):
    kws = DOMAIN_KEYWORDS.get(domain, [])
    if not kws:
        return 0
    hits = 0
    for ev in events:
        text = f"{ev['summary']} {ev['description']}".lower()
        if any(k.lower() in text for k in kws):
            hits += 1
    for m in mails:
        text = m.lower()
        if any(k.lower() in text for k in kws):
            hits += 1
    return hits


def fetch_mail_subjects(limit):
    """Return list of recent mail subjects via gog gmail search."""
    acct = env("GOG_ACCOUNT") or prof.google_account()
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "gmail", "search", "in:inbox", "-j",
         "--account", acct],
        capture_output=True, text=True,
        env={**os.environ, "GOG_KEYRING_PASSWORD": env("GOG_KEYRING_PASSWORD"),
             "GOG_ACCOUNT": acct},
        timeout=45,
    )
    if out.returncode != 0:
        return []
    try:
        d = json.loads(out.stdout)
        items = d if isinstance(d, list) else d.get("messages", d.get("threads", []))
    except Exception:
        return []
    subs = []
    for m in items[:limit]:
        sub = m.get("subject") or m.get("snippet") or ""
        if sub:
            subs.append(sub)
    return subs


def days_until(deadline_str):
    if not deadline_str:
        return None
    try:
        d = datetime.fromisoformat(deadline_str.replace("Z", "+00:00")).astimezone(JST)
        return (d - datetime.now(JST)).days
    except Exception:
        try:
            d = datetime.fromisoformat(deadline_str + "T00:00:00+09:00")
            return (d - datetime.now(JST)).days
        except Exception:
            return None


def compose(goals, events, mails):
    rows_drift = []
    rows_excess = []
    rows_ok = []
    countdowns = []

    for g in goals:
        domain = g.get("domain", "?")
        wa = g.get("weekly_action", "")
        milestone = g.get("milestone", "")
        target = parse_target_per_week(wa) or 0
        observed = classify(events, mails, domain) / (HORIZON_DAYS / 7)
        if target > 0:
            ratio = observed / target if target else 0
            row = {"domain": domain, "target": target,
                   "observed": round(observed, 1), "wa": wa,
                   "milestone": milestone}
            if ratio < 0.7:
                rows_drift.append(row)
            elif ratio > 1.3:
                rows_excess.append(row)
            else:
                rows_ok.append(row)
        m_deadline = re.search(r"(\d{4})-(\d{2})", milestone)
        if m_deadline:
            yr, mo = m_deadline.group(1), m_deadline.group(2)
            days = days_until(f"{yr}-{mo}-01")
            if days is not None:
                countdowns.append({"milestone": milestone, "days": days})

    body = ["Hi,", "",
            "Goal drift report — past {} days vs your stated ideal_state[]:".format(HORIZON_DAYS),
            ""]
    if rows_drift:
        body.append("⚠️  Drifting (= observed < 70% of target):")
        for r in rows_drift:
            body.append(f"  • {r['domain']:<14} target {r['target']:.1f}/wk → observed {r['observed']:.1f}/wk")
            body.append(f"                  weekly_action: {r['wa'][:80]}")
        body.append("")
    if rows_excess:
        body.append("🔥  Above target (= sustainable?):")
        for r in rows_excess:
            body.append(f"  • {r['domain']:<14} target {r['target']:.1f}/wk → observed {r['observed']:.1f}/wk")
        body.append("")
    if rows_ok:
        body.append("✅  On track:")
        for r in rows_ok:
            body.append(f"  • {r['domain']:<14} {r['observed']:.1f}/wk (~target)")
        body.append("")
    if countdowns:
        body.append("⏳  Milestone countdowns:")
        for c in countdowns:
            body.append(f"  • {c['milestone'][:70]}   in {c['days']} d")
        body.append("")
    body.append("Anicca's suggestion for this week:")
    suggestions = []
    for r in rows_drift:
        suggestions.append(
            f"  → book one '{r['domain']}' action: target +{max(1, int(r['target'] - r['observed']))} this week"
        )
    if not suggestions:
        suggestions.append("  → no drift detected; stay the course.")
    body.extend(suggestions)
    body.append("")
    body.append("— Anicca (goal-learner)")
    return "\n".join(body)


def send_mail(subject, body):
    acct = env("GOG_ACCOUNT") or prof.google_account()
    to = env("ANICCA_REPORT_TO") or acct
    if not (acct and to):
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
    return out.returncode == 0


def main():
    goals = read_goals()
    if not goals:
        print(json.dumps({"action": "no-goals"}))
        return
    events = fetch_events(HORIZON_DAYS)
    mails = fetch_mail_subjects(GMAIL_RECENT)
    body = compose(goals, events, mails)
    subj = f"[Anicca] Goal drift report — past {HORIZON_DAYS} days vs ideal_state[]"
    if "--print" in sys.argv:
        print("SUBJECT:", subj)
        print("=" * 60)
        print(body)
        return
    sent = send_mail(subj, body)
    print(json.dumps({"sent": sent, "goals": len(goals),
                      "events_seen": len(events), "mails_seen": len(mails)},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
