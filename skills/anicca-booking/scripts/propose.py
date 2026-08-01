#!/usr/bin/env python3
"""
propose — for each empty slot from scan_gcal_horizon, find candidate events
from profile.goals.ideal_state[] sources via Firecrawl search. Apply 3-gate
filter (anti_goals / blocklistApply / physical conflict).

Output: candidates JSON [{slot, domain, title, url, organizer_mail?, status}]
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(os.environ.get("LIFE_MANAGER_REPO", Path(__file__).resolve().parents[3]))
sys.path.insert(0, str(REPO_ROOT / "skills/_shared"))
import anicca_profile as prof  # noqa: E402

JST = timezone(timedelta(hours=9))


def load_goals():
    p = prof.load_profile()
    return p.get("goals", {}), p.get("lateness", {})


def firecrawl_search(query, limit=5):
    """firecrawl CLI v1.6.2 has no --format json. Parse the human text output:
        <title>
          URL: <url>
          <snippet>
    Blank line separates results."""
    try:
        out = subprocess.run(
            ["/opt/homebrew/bin/firecrawl", "search", query,
             "--limit", str(limit)],
            capture_output=True, text=True, timeout=45,
        )
        if out.returncode != 0:
            print(f"[propose] firecrawl rc={out.returncode}: {out.stderr[:200]}", file=sys.stderr)
            return []
        results = []
        current = {}
        for raw in (out.stdout or "").splitlines():
            line = raw.rstrip()
            if not line:
                if current.get("url"):
                    results.append({
                        "title": current.get("title", "")[:300],
                        "url": current["url"],
                        "markdown": current.get("snippet", "")[:600],
                    })
                current = {}
                continue
            stripped = line.lstrip()
            if stripped.startswith("URL:"):
                current["url"] = stripped[4:].strip()
            elif "title" not in current and not raw.startswith(" "):
                current["title"] = stripped
            else:
                current["snippet"] = (current.get("snippet", "") + " " + stripped).strip()
        if current.get("url"):
            results.append({
                "title": current.get("title", "")[:300],
                "url": current["url"],
                "markdown": current.get("snippet", "")[:600],
            })
        return results[:limit]
    except Exception as e:
        print(f"[propose] firecrawl failed: {e}", file=sys.stderr)
        return []


def per_domain_query(domain, slot):
    """Build a Firecrawl query for a (domain, slot) combo."""
    date_str = slot["date"]
    if domain == "AI_LT":
        return f"AI 東京 LT {date_str} inurl:lu.ma"
    if domain == "comedy":
        return f"お笑い ライブ 出演者募集 {date_str} site:twoplus.tokyo OR site:tokyocomedybar.com OR site:pechka.tokyo"
    if domain == "research":
        # 研究系は slot 埋めに使わない (論文は応募対象でない)。スキップ。
        return ""
    if domain == "job_BigTech":
        # job board page は時間 slot に応募する性質ではない。スキップ。
        return ""
    if domain == "VC_apply":
        # apply-to-funder cron で個別に処理。slot 埋めに使わない。
        return ""
    return ""


# NOTE (BP §0.5.3): URL whitelist regex は削除。
# 各サイト構造は違うので、event-page 判定は SKILL.md の自然言語で Anicca に任せる。
# propose.py の責務 = 3-gate filter のみ。candidates は SKILL.md 経由で投入されるか、
# scaffold fallback firecrawl が生成する。


def looks_like_event_page(url):
    """Soft heuristic — discard obviously generic landing pages.
    Strict event-detail判定は SKILL.md の Anicca に任せる (BP §0.5.3)。
    ここでは「明らかに event ではない」だけ弾く。"""
    if not url:
        return False
    lowered = url.lower()
    # Generic landing/calendar/career/article pages
    if any(b in lowered for b in ["/calendar/", "/careers/", "/blog/", "/jobs/", "/news/", "/about"]):
        return False
    # Event detail pages typically contain /event/ or /e/ or specific id segment
    if any(b in lowered for b in ["/event/", "/events/", "/e/", "lu.ma/"]):
        return True
    # Otherwise let Anicca decide via SKILL.md
    return True


def extract_email(text):
    if not text:
        return None
    m = re.search(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)
    return m.group(0) if m else None


# ── GATE 3 (BP §0.5.4) — 既存 gcal event と時刻 overlap 絶対禁止 ─────────────
# A user cannot be in two places at once; never override this deterministic gate.
TRAVEL_BUFFER_MIN = 30


def fetch_gcal_events_for_gate3(from_iso, to_iso):
    """Re-read gcal at propose time to detect events inserted after scan_gcal_horizon.
    Returns list of (start_dt, end_dt, summary) tuples."""
    acct = os.environ.get("GOG_ACCOUNT", "")
    out = subprocess.run(
        ["/opt/homebrew/bin/gog", "calendar", "events", "list", "-j",
         "--account", acct, "--from", from_iso, "--to", to_iso,
         "--all-pages", "--max", "500"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        print(f"[gate3] gog failed: {out.stderr[:200]}", file=sys.stderr)
        return []
    try:
        data = json.loads(out.stdout)
    except json.JSONDecodeError:
        return []
    items = data if isinstance(data, list) else data.get("events", data.get("items", []))
    busy = []
    for ev in items:
        s = ev.get("start", {}).get("dateTime")
        e = ev.get("end", {}).get("dateTime")
        if not s or not e:
            continue
        try:
            sd = datetime.fromisoformat(s).astimezone(JST)
            ed = datetime.fromisoformat(e).astimezone(JST)
        except ValueError:
            continue
        busy.append((sd, ed, ev.get("summary", "(no title)")[:60]))
    return busy


def gate3_physical_conflict(candidate, gcal_busy):
    """Reject if slot ± TRAVEL_BUFFER_MIN overlaps any existing gcal event."""
    slot = candidate.get("slot") or {}
    try:
        s = datetime.fromisoformat(slot["startIso"]).astimezone(JST)
    except (KeyError, ValueError):
        return "physical_conflict: invalid slot startIso"
    duration = slot.get("duration_min", 60)
    e = s + timedelta(minutes=duration)
    check_start = s - timedelta(minutes=TRAVEL_BUFFER_MIN)
    check_end = e + timedelta(minutes=TRAVEL_BUFFER_MIN)
    for ev_s, ev_e, ev_title in gcal_busy:
        if ev_s < check_end and ev_e > check_start:
            return f"physical_conflict with: {ev_title}"
    return None


def gate1_anti_goals(candidate, slot, goals):
    """Return None if pass, else reason str."""
    anti = goals.get("anti_goals") or []
    start = datetime.fromisoformat(slot["startIso"]).astimezone(JST)
    # "深夜 02:00 以降 — sleep protect"
    if 2 <= start.hour < 9 and any("深夜" in a or "sleep" in a.lower() for a in anti):
        return "anti_goals: late-night sleep protect"
    # "MUFG/MUIT 業務時間 09:00-17:00 Mon-Fri"
    if start.weekday() < 5 and 9 <= start.hour < 17 and any("MUIT" in a or "MUFG" in a for a in anti):
        return "anti_goals: MUIT working hours"
    return None


def gate2_blocklist(candidate, lateness):
    blockl = lateness.get("blocklistApply") or []
    text = f"{candidate.get('url','')} {candidate.get('organizer_mail','')} {candidate.get('title','')}"
    for b in blockl:
        if b in text:
            return f"blocklistApply hit: {b}"
    return None


def main():
    goals, lateness = load_goals()
    ideal = goals.get("ideal_state") or []
    # Read slots from stdin OR call scan_gcal_horizon if no stdin
    if not sys.stdin.isatty():
        slots = json.loads(sys.stdin.read() or "[]")
    else:
        out = subprocess.run(
            ["python3", str(Path(__file__).parent / "scan_gcal_horizon.py")],
            capture_output=True, text=True,
        )
        slots = json.loads(out.stdout or "[]")

    # GATE 3 pre-fetch: re-read gcal so we catch events inserted after scan_gcal_horizon
    # (race condition protection; BP §0.5.4 deterministic trust gate)
    if slots:
        all_starts = [s["startIso"] for s in slots if s.get("startIso")]
        from_iso = min(all_starts)[:10]
        to_iso = (datetime.fromisoformat(max(all_starts)) + timedelta(days=1)).date().isoformat()
        gcal_busy = fetch_gcal_events_for_gate3(from_iso, to_iso)
    else:
        gcal_busy = []

    candidates = []
    for slot in slots[:5]:  # cap to top 5 slots/day to avoid Firecrawl quota burn
        for state in ideal:
            domain = state.get("domain")
            q = per_domain_query(domain, slot)
            if not q:
                continue
            results = firecrawl_search(q, limit=5)
            for r in results:
                url = r.get("url", "")
                # gate 0 (soft): obviously generic landing pages を弾く (BP §0.5.3 — strict判定は SKILL.md)
                if not looks_like_event_page(url):
                    continue
                cand = {
                    "slot": slot,
                    "domain": domain,
                    "title": r.get("title", "")[:200],
                    "url": url,
                    "organizer_mail": extract_email(r.get("markdown", "") or ""),
                    "status": "pending",
                }
                # 3-gate filter (ALL must pass — BP §0.5.4)
                reason = gate1_anti_goals(cand, slot, goals)
                if reason:
                    cand["status"] = f"blocked: {reason}"
                    candidates.append(cand)
                    continue
                reason = gate2_blocklist(cand, lateness)
                if reason:
                    cand["status"] = f"blocked: {reason}"
                    candidates.append(cand)
                    continue
                # GATE 3 = absolute user-trust protection (no double-booking, ever)
                reason = gate3_physical_conflict(cand, gcal_busy)
                if reason:
                    cand["status"] = f"blocked: {reason}"
                    candidates.append(cand)
                    continue
                cand["status"] = "approved"
                candidates.append(cand)
                break  # 1 candidate per (slot, domain) is enough
    print(json.dumps(candidates, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
