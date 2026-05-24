#!/usr/bin/env python3
"""TCB open-mic: build a PREFILLED Google-Form link and {{profile.lateness.stakeholders.channel}} it to Dais.

The TCB sign-up Google Form is reCAPTCHA-v2-image gated — no {{profile.lateness.stakeholders.channel}} (camofox,
CloakBrowser headed/headless, fresh profile) passes it, and audio-solve is off the
table. So we do the ONLY thing left that keeps Dais's work to ~5 seconds:

  fetch live form schema  →  pick free nights (gcal day-lock)  →  build a prefilled
  viewform URL (all fields filled)  →  {{profile.lateness.stakeholders.channel}} Dais the link.

Dais opens the link (everything pre-filled), solves the captcha, clicks submit. Done.

The form's date questions + entry IDs change weekly, so we parse FB_PUBLIC_LOAD_DATA_
live every run — never hardcode entry IDs.

Usage:
  tcb-prefill-notify.py [--form-url <viewform>] [--name Aniicha] [--{{profile.lateness.stakeholders.senderType}} Aniicha]
                        [--note "..."] [--days 14] [--to {{profile.contact.personalEmail}}] [--dry-run]
Stdout last line: TCB_PREFILL: {"sent":bool,"nights":[...],"url":...}
"""
import argparse, json, os, re, subprocess, sys, urllib.parse, urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
DEFAULT_FORM = "https://docs.google.com/forms/d/e/1FAIpQLScJjbXcw3YFni1FWc3TqXGKoYofpeq9uPm9LVATXewPtSMCoA/viewform"
SHARED = os.path.expanduser("~/.openclaw/skills/_shared/gcal-day.sh")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def parse_schema(html):
    m = re.search(r"FB_PUBLIC_LOAD_DATA_\s*=\s*(\[.*?\]);</script>", html, re.S)
    if not m:
        raise SystemExit("ERR: FB_PUBLIC_LOAD_DATA_ not found")
    data = json.loads(m.group(1))
    title = data[3] if len(data) > 3 else ""
    out = []
    for q in data[1][1]:
        qtext = q[1] or ""
        qtype = q[3]
        entries = []
        if q[4]:
            for sub in q[4]:
                opts = [o[0] for o in sub[1]] if sub[1] else []
                entries.append({"id": sub[0], "opts": opts})
        out.append({"text": qtext, "type": qtype, "entries": entries})
    return title, out


def gcal_busy(date_iso):
    """True if that night already has a booking (day-lock). Uses _shared/gcal-day.sh."""
    try:
        r = subprocess.run(["bash", "-c",
                            'source "%s"; gcal_day_has_event "%s"' % (SHARED, date_iso)],
                           capture_output=True, timeout=40)
        return r.returncode == 0
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--form-url", default=DEFAULT_FORM)
    ap.add_argument("--name", default="Aniicha")
    ap.add_argument("--{{profile.lateness.stakeholders.senderType}}", default="Aniicha")
    ap.add_argument("--note", default="First time at a TCB mic, performed stand-up before. Pin comedian, open to 2 spots.")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--to", default=os.environ.get("DAIS_EMAIL", "{{profile.contact.personalEmail}}"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    view = a.form_url if "/viewform" in a.form_url else a.form_url.rstrip("/") + "/viewform"
    title, qs = parse_schema(fetch(view))

    params = {"usp": "pp_url"}
    chosen, skipped = [], []
    for q in qs:
        low = q["text"].lower()
        if q["type"] == 0 and q["entries"]:
            eid = q["entries"][0]["id"]
            if "{{profile.lateness.stakeholders.senderType}} name" in low:
                params["entry.%d" % eid] = a.{{profile.lateness.stakeholders.senderType}}
            elif "first & surname" in low:
                params["entry.%d" % eid] = a.name
            continue
        if q["type"] == 4 and "first time at a tcb" in low and q["entries"]:
            opts = q["entries"][0]["opts"]
            pick = next((o for o in opts if "elsewhere" in o.lower()), None)
            if pick:
                params["entry.%d" % q["entries"][0]["id"]] = pick
            continue
        if q["type"] == 1 and "special requests" in low and q["entries"]:
            params["entry.%d" % q["entries"][0]["id"]] = a.note
            continue
        m = re.search(r"(\d{4}-\d{2}-\d{2})", q["text"])
        if m and q["type"] == 7:
            iso = m.group(1)
            if gcal_busy(iso):
                skipped.append(iso); continue
            for sub in q["entries"]:
                yes = next((o for o in sub["opts"] if o.lower() == "yes"), "Yes")
                params["entry.%d" % sub["id"]] = yes
            chosen.append(iso)

    prefilled = view + "?" + urllib.parse.urlencode(params, encoding="utf-8")
    result = {"sent": False, "week": title, "nights": chosen, "skipped": skipped, "url": prefilled}

    if not chosen:
        result["note"] = "no free nights to apply (all day-locked) — no mail sent"
        print("TCB_PREFILL:", json.dumps(result, ensure_ascii=False))
        return

    body = (
        "TCB オープンマイク サインアップ（{week}）\n\n"
        "下のリンクは全部記入済みです。開いて → reCAPTCHA を解いて → 送信 だけお願い（5秒）。\n"
        "（フォームが reCAPTCHA で自動送信できないため、ここだけ手動）\n\n"
        "申込予定の夜: {nights}\n"
        "{skipline}"
        "氏名: {name} / 芸名: {{{profile.lateness.stakeholders.senderType}}}\n\n"
        "▼ 記入済みリンク（クリック→captcha→送信）\n{url}\n\n"
        "メール最後に届いた=その週の枠が開いた合図。期限は前週水曜深夜。\n"
    ).format(week=title, nights=", ".join(chosen),
             skipline=("既に予定あり(申込しない): %s\n" % ", ".join(skipped)) if skipped else "",
             name=a.name, {{profile.lateness.stakeholders.senderType}}=a.{{profile.lateness.stakeholders.senderType}}, url=prefilled)

    if a.dry_run:
        result["dry_run"] = True
        print(body)
        print("TCB_PREFILL:", json.dumps(result, ensure_ascii=False))
        return

    p = subprocess.run(["gog", "gmail", "send", "--to", a.to,
                        "--subject", "【TCB オープンマイク】記入済みリンク（captcha+送信だけ） %s" % title,
                        "--body-file", "-"],
                       input=body.encode("utf-8"), capture_output=True, timeout=60)
    ok = p.returncode == 0
    result["sent"] = ok
    if not ok:
        result["error"] = p.stderr.decode("utf-8", "replace")[:200]
    print("TCB_PREFILL:", json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
