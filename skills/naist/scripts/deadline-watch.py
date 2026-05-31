#!/usr/bin/env python3
"""deadline-watch.py — produce ~/.openclaw/workspace/naist/<slug>/deadlines.ics.

Sources merged into the single ICS:
  1. schedule-*.json (per-class meetings + 健康診断 / other_events)
  2. triaged-*.json   (Gmail-extracted homework / bureaucracy / event deadlines)

Output is atomic (write tmp, mv into place). Each VEVENT carries DESCRIPTION
with course / instructor / room / topic when available.

The user subscribes to the ICS in macOS Calendar / Google Calendar.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

SLUG = os.environ.get("SLUG", "")
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"

WORKSPACE = Path.home() / ".openclaw" / "workspace" / "naist"
STATE_ROOT = Path.home() / ".openclaw" / "state" / "naist"


def fail(msg: str) -> None:
    print(f"deadline-watch[{SLUG}] FATAL: {msg}", file=sys.stderr)
    sys.exit(1)


def md5(s: str) -> str:
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def fmt_dt(date_str: str, hhmm: str) -> str:
    """2026-05-13 + '09:20' → '20260513T092000' (no Z, used with TZID=Asia/Tokyo)"""
    d = date_str.replace("-", "")
    return f"{d}T{hhmm.replace(':','')}00"


def class_vevents(schedule_files: list[Path]) -> list[str]:
    out: list[str] = []
    for sf in schedule_files:
        sched = json.loads(sf.read_text())
        for course in sched.get("courses", []):
            for s in course.get("sessions", []):
                start_t, end_t = s["time"].split("-")
                ds = fmt_dt(s["date"], start_t)
                de = fmt_dt(s["date"], end_t)
                uid = md5(f"class-{course['code']}-{s['n']}-{s['date']}")
                summary = f"[NAIST] {course['name']} #{s['n']}: {s['topic'][:50]}"
                desc = (
                    f"科目: {course['name']} ({course['code']})\\n"
                    f"第{s['n']}回 / {s['date']} {s['time']} / {s['period']}限\\n"
                    f"教員: {s['instructor']}\\n"
                    f"教室: {course['default_room']}\\n"
                    f"テーマ: {s['topic']}"
                )
                location = course["default_room"]
                out.append(
                    "BEGIN:VEVENT\n"
                    f"UID:{uid}@naist.openclaw\n"
                    f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n"
                    f"DTSTART;TZID=Asia/Tokyo:{ds}\n"
                    f"DTEND;TZID=Asia/Tokyo:{de}\n"
                    f"SUMMARY:{summary}\n"
                    f"DESCRIPTION:{desc}\n"
                    f"LOCATION:{location.replace(',', '')}\n"
                    "CATEGORIES:NAIST,授業\n"
                    "END:VEVENT"
                )
        for ev in sched.get("other_events", []):
            d = ev["date"].replace("-", "")
            uid = md5(f"other-{ev['title']}-{ev['date']}")
            out.append(
                "BEGIN:VEVENT\n"
                f"UID:{uid}@naist.openclaw\n"
                f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n"
                f"DTSTART;VALUE=DATE:{d}\n"
                f"SUMMARY:[NAIST] {ev['title']}\n"
                "CATEGORIES:NAIST,行事\n"
                "END:VEVENT"
            )
    return out


def triaged_deadline_vevents(slug_dir: Path) -> list[str]:
    """Pull deadline-bearing items from latest triaged-*.json (homework / bureaucracy)."""
    out: list[str] = []
    triaged_files = sorted(WORKSPACE.glob("triaged-*.json"))
    if not triaged_files:
        triaged_files = sorted(slug_dir.glob("triaged-*.json"))
    if not triaged_files:
        return out
    latest = triaged_files[-1]
    try:
        items = json.loads(latest.read_text())
    except Exception:
        return out
    if not isinstance(items, list):
        items = items.get("threads") or []
    for it in items:
        bucket = it.get("bucket", "")
        if bucket not in ("homework", "bureaucracy", "ta-task", "professor-task"):
            continue
        text = (it.get("subject", "") + " " + it.get("snippet", ""))
        m = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", text)
        if not m:
            m2 = re.search(r"(\d{1,2})月(\d{1,2})日", text)
            if m2:
                year = date.today().year
                d_str = f"{year}-{int(m2.group(1)):02d}-{int(m2.group(2)):02d}"
            else:
                continue
        else:
            d_str = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
        d_compact = d_str.replace("-", "")
        uid = md5(f"deadline-{it.get('id','?')}-{d_str}")
        out.append(
            "BEGIN:VEVENT\n"
            f"UID:{uid}@naist.openclaw\n"
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}\n"
            f"DTSTART;VALUE=DATE:{d_compact}\n"
            f"SUMMARY:[NAIST/{bucket}] {it.get('subject','')[:60]}\n"
            f"DESCRIPTION:{(it.get('snippet','')[:300]).replace(chr(10),' ')}\n"
            "CATEGORIES:NAIST,締切\n"
            "END:VEVENT"
        )
    return out


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".deadlines-", suffix=".ics", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
        shutil.move(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    if not SLUG:
        fail("SLUG env required")
    slug_dir = WORKSPACE / SLUG
    schedule_files = sorted(slug_dir.glob("schedule-*.json"))

    vevents: list[str] = []
    vevents.extend(class_vevents(schedule_files))
    vevents.extend(triaged_deadline_vevents(slug_dir))

    ical = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//openclaw//naist v2//EN\r\n"
        "CALSCALE:GREGORIAN\r\n"
        f"X-WR-CALNAME:NAIST ({SLUG})\r\n"
        "BEGIN:VTIMEZONE\r\n"
        "TZID:Asia/Tokyo\r\n"
        "BEGIN:STANDARD\r\n"
        "DTSTART:19700101T000000\r\n"
        "TZOFFSETFROM:+0900\r\n"
        "TZOFFSETTO:+0900\r\n"
        "TZNAME:JST\r\n"
        "END:STANDARD\r\n"
        "END:VTIMEZONE\r\n"
        + "\r\n".join(vevents) + "\r\n"
        "END:VCALENDAR\r\n"
    )

    out = slug_dir / "deadlines.ics"
    write_atomic(out, ical)
    print(f"deadline-watch[{SLUG}]: wrote {out} with {len(vevents)} events")
    return 0


if __name__ == "__main__":
    sys.exit(main())
