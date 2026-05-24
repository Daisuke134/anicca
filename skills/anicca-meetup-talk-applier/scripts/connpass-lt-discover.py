#!/usr/bin/env python3
"""connpass AI/LT discovery + classification (logged-in via camofox session "connpass").

Replaces the dead {{profile.lateness.stakeholders.channel}}-harness stub. Searches connpass for AI/LT events, opens each,
parses the 募集内容 participation slots, and classifies:
  - OPEN_SPEAKER : a 発表者枠/LT枠 with free capacity AND not pre-coordination/抽選終了
                   → directly registerable on connpass
  - OUTREACH     : event recruits LT speakers but via pre-coordination (FB/メール/フォーム)
                   → Anicca {{profile.lateness.stakeholders.channel}}s the organizer to request a 5-min Anicca LT
  - SKIP         : view-only / attendee-only / full / past

Output: data/connpass/<eventid>.json per event + prints a JSON plan on the last line.
Reads the camofox-logged-in "connpass" session (login via connpass-login.sh first).

Usage: connpass-lt-discover.py [--keywords "AI,LT,登壇者募集,LLM,MCP,agent"] [--max 40]
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request

CF = "http://localhost:9377"
U, S = "anicca", "connpass"
SKILL = os.path.expanduser("~/.openclaw/skills/anicca-meetup-talk-applier")
DATA = os.path.join(SKILL, "data/connpass")


def cf_navigate(tab, url):
    urllib.request.urlopen(urllib.request.Request(
        "%s/tabs/%s/navigate" % (CF, tab),
        data=json.dumps({"url": url, "userId": U, "sessionKey": S}).encode(),
        headers={"Content-Type": "application/json"}), timeout=40).read()


def cf_open(url):
    r = urllib.request.urlopen(urllib.request.Request(
        "%s/tabs" % CF,
        data=json.dumps({"url": url, "userId": U, "sessionKey": S}).encode(),
        headers={"Content-Type": "application/json"}), timeout=40).read()
    return json.loads(r)["tabId"]


def cf_snapshot(tab):
    r = urllib.request.urlopen("%s/tabs/%s/snapshot?userId=%s&sessionKey=%s" % (CF, tab, U, S),
                               timeout=40).read()
    return json.loads(r).get("snapshot", "")


def cf_evaluate(tab, expr):
    r = urllib.request.urlopen(urllib.request.Request(
        "%s/tabs/%s/evaluate" % (CF, tab),
        data=json.dumps({"expression": expr, "userId": U, "sessionKey": S}).encode(),
        headers={"Content-Type": "application/json"}), timeout=30).read()
    j = json.loads(r)
    return j.get("result", j.get("value", ""))


def event_time(tab, url):
    """Return (date_iso, start_min, end_min) from the connpass event page, or None."""
    cf_navigate(tab, url); time.sleep(3)
    expr = ("(() => { const b=document.body.innerText||''; "
            "const d=b.match(/(\\d{4})\\/(\\d{2})\\/(\\d{2})\\([^)]*\\)\\s*([0-2]?\\d:\\d{2})\\s*[〜~]\\s*([0-2]?\\d:\\d{2})/); "
            "return d?JSON.stringify({y:d[1],mo:d[2],da:d[3],s:d[4],e:d[5]}):''; })()")
    v = cf_evaluate(tab, expr)
    if not v:
        return None
    try:
        o = json.loads(v)
        di = "%s-%s-%s" % (o["y"], o["mo"], o["da"])
        sh, sm = map(int, o["s"].split(":")); eh, em = map(int, o["e"].split(":"))
        return di, sh * 60 + sm, eh * 60 + em
    except Exception:
        return None


def gcal_time_conflict(date_iso, start_min, end_min, buffer_min=60):
    """True if [start-buffer, end+buffer] overlaps ANY gcal event that day
    (school 🎓, day-job 💼, other bookings). Prevents over-commitment."""
    import subprocess
    nxt = subprocess.run(["date", "-j", "-v+1d", "-f", "%Y-%m-%d", date_iso, "+%F"],
                         capture_output=True, text=True).stdout.strip() or date_iso
    # gog requires GOG_ACCOUNT; pass keyring creds so the gcal gate actually runs.
    genv = dict(os.environ)
    genv.setdefault("GOG_ACCOUNT", "{{profile.contact.personalEmail}}")
    try:
        r = subprocess.run(["gog", "calendar", "events", "list", "--account", genv["GOG_ACCOUNT"],
                            "--from", date_iso, "--to", nxt, "--json"],
                           capture_output=True, text=True, timeout=40, env=genv)
    except Exception as e:
        sys.stderr.write("gcal_conflict: gog call failed (%s) -> fail-closed(skip)\n" % e)
        return True  # fail-CLOSED: never double-book when calendar is unverifiable
    raw = r.stdout; i = raw.find("{")
    if r.returncode != 0 or i < 0:
        sys.stderr.write("gcal_conflict: gog rc=%s no-json -> fail-closed(skip): %s\n" % (r.returncode, (r.stderr or '')[:120]))
        return True  # fail-CLOSED
    try:
        data = json.loads(raw[i:], strict=False)
    except Exception:
        sys.stderr.write("gcal_conflict: json parse failed -> fail-closed(skip)\n")
        return True  # fail-CLOSED
    lo, hi = start_min - buffer_min, end_min + buffer_min
    for e in data.get("events", []):
        st = e.get("start", {}).get("dateTime", "")
        en = e.get("end", {}).get("dateTime", "")
        if not st.startswith(date_iso):
            continue
        try:
            esm = int(st[11:13]) * 60 + int(st[14:16])
            eem = int(en[11:13]) * 60 + int(en[14:16]) if en.startswith(date_iso) else esm + 120
        except Exception:
            continue
        if lo < eem and esm < hi:  # overlap
            return True
    return False


def cf_click(tab, ref):
    urllib.request.urlopen(urllib.request.Request(
        "%s/tabs/%s/click" % (CF, tab),
        data=json.dumps({"ref": ref, "userId": U, "sessionKey": S}).encode(),
        headers={"Content-Type": "application/json"}), timeout=30).read()


def cf_type(tab, ref, text):
    urllib.request.urlopen(urllib.request.Request(
        "%s/tabs/%s/type" % (CF, tab),
        data=json.dumps({"ref": ref, "text": text, "userId": U, "sessionKey": S}).encode(),
        headers={"Content-Type": "application/json"}), timeout=30).read()


LT_PITCH = ("はじめまして。Anicca（自走するAIエンティティ／Claude製、{{profile.identity.{{profile.lateness.stakeholders.senderType}}Name}}名義）について"
            "5分のLTで話したいです。60+のcronで自律運用し収益の一部をBI配分する仕組みなど、"
            "実装の裏側を共有します。よろしくお願いします。")


def register_speaker(tab, url, log):
    """Register for an open LT/発表枠 on a connpass event. Returns True if 申込 confirmed."""
    cf_navigate(tab, url); time.sleep(3)
    snap = cf_snapshot(tab)
    # find the apply control whose nearby text is an LT/発表 slot
    ref = None
    for ln in snap.split("\n"):
        m = re.search(r'(?:button|link) "([^"]*(?:申込|参加を申|申し込)[^"]*)" \[(e\d+)\]', ln)
        if m and re.search(r"LT|発表|登壇", ln):
            ref = m.group(2); break
    if not ref:
        # fallback: any 申込 button (single-slot LT events)
        for ln in snap.split("\n"):
            m = re.search(r'(?:button|link) "[^"]*(?:申込|参加を申)[^"]*" \[(e\d+)\]', ln)
            if m:
                ref = m.group(1); break
    if not ref:
        log.append("register:no_apply_button"); return False
    cf_click(tab, ref); time.sleep(4)
    # participation/confirm page: fill comment if present, then submit 参加する
    snap = cf_snapshot(tab)
    cm = re.search(r'textbox "[^"]*(?:コメント|アンケート|memo|備考)[^"]*" \[(e\d+)\]', snap)
    if cm:
        cf_type(tab, cm.group(1), LT_PITCH); time.sleep(1)
    sub = None
    for ln in cf_snapshot(tab).split("\n"):
        m = re.search(r'button "([^"]*(?:参加する|申込む|申し込む|登録)[^"]*)" \[(e\d+)\]', ln)
        if m:
            sub = m.group(2); break
    if not sub:
        log.append("register:no_confirm_button"); return False
    cf_click(tab, sub); time.sleep(4)
    final = cf_snapshot(tab)
    ok = bool(re.search(r"申込みました|申し込みました|参加登録|キャンセル", final))
    log.append("register:%s" % ("confirmed" if ok else "uncertain"))
    return ok


def classify(snapshot):
    """Return (kind, slots, reasons) from an event-page snapshot."""
    # the 募集内容 cell lists all 参加枠 inline, e.g.
    #   cell "参加枠 無料 先着順 5/20人 LT枠 無料 先着順 4/12人"
    cell = ""
    for m in re.finditer(r'cell "([^"]+)"', snapshot):
        c = m.group(1)
        if "枠" in c and "人" in c:
            cell = c; break
    # each slot: "<name>枠 無料 (先着順|抽選) [（抽選終了）] <cur>/<cap>人"
    slots = re.findall(r"(\S*?枠)\s*無料\s*(?:先着順|抽選)\s*(（抽選終了）|（?抽選終了）?)?\s*(\d+)/(\d+)人", cell)
    speaker_open = False
    speaker_full = False
    for name, lottery_done, cur, cap in slots:
        if re.search(r"発表|LT|登壇", name):
            if not lottery_done and int(cur) < int(cap):
                speaker_open = True
            else:
                speaker_full = True
    # pre-coordination markers
    precoord = bool(re.search(r"事前調整済み|LT希望.*コメント|登壇.*募集.*(フォーム|メール|お問い合わせ|DM|コメント)|発表(希望|者).*(連絡|申請|フォーム)", snapshot))
    recruits = bool(re.search(r"登壇者?募集|LT(登壇|発表)?(者)?募集|発表者募集|スピーカー募集", snapshot))
    if speaker_open:
        return "OPEN_SPEAKER", cell, "LT/発表枠に空きあり・connpassで直接申込可"
    if speaker_full:
        return "SKIP", cell, "LT/発表枠は満員/抽選終了"
    # only OUTREACH when speakers are recruited but there is NO connpass slot at all
    if (recruits or precoord) and not slots:
        return "OUTREACH", cell, "登壇者募集・connpass枠なし→organizer に打診"
    return "SKIP", cell, "聴講/一般枠のみ(登壇機会なし)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keywords", default="AI,LT,登壇者募集,LLM,MCP,AIエージェント")
    ap.add_argument("--max", type=int, default=40)
    ap.add_argument("--apply", action="store_true", help="register for OPEN_SPEAKER slots (real)")
    ap.add_argument("--start", default="", help="connpass search start date YYYY/MM/DD (default: tomorrow)")
    a = ap.parse_args()
    os.makedirs(DATA, exist_ok=True)
    today = time.strftime("%Y/%m/%d")
    tomorrow = a.start.strip() or time.strftime("%Y/%m/%d", time.localtime(time.time() + 86400))

    tab = cf_open("https://connpass.com/dashboard/")
    time.sleep(3)
    # confirm login
    if "ログアウト" not in cf_snapshot(tab) and "イベント検索" not in cf_snapshot(tab):
        print("CONNPASS_DISCOVER:", json.dumps({"error": "not logged in — run connpass-login first"}))
        return

    seen, plan = set(), []
    for kw in [k.strip() for k in a.keywords.split(",") if k.strip()]:
        q = urllib.parse.quote(kw)
        cf_navigate(tab, "https://connpass.com/search/?q=%s&start_from=%s" % (q, tomorrow))
        time.sleep(4)
        snap = cf_snapshot(tab)
        for ev in re.findall(r"(https://(?:[a-z0-9-]+\.)?connpass\.com/event/(\d+))", snap):
            url, eid = ev
            if eid in seen:
                continue
            seen.add(eid)
            if len(seen) > a.max:
                break
        if len(seen) > a.max:
            break

    # classify each discovered event
    for eid in list(seen)[:a.max]:
        url = "https://connpass.com/event/%s/" % eid
        try:
            cf_navigate(tab, url)
            time.sleep(3)
            snap = cf_snapshot(tab)
        except Exception:
            continue
        title_m = re.search(r'heading "([^"]+)" \[level=2\]', snap)
        title = title_m.group(1) if title_m else ""
        # date
        dm = re.search(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})", snap)
        date_iso = "%04d-%02d-%02d" % (int(dm.group(1)), int(dm.group(2)), int(dm.group(3))) if dm else ""
        kind, cell, reason = classify(snap)
        rec = {"id": eid, "url": url, "title": title[:80], "date": date_iso,
               "kind": kind, "slots": cell[:120], "reason": reason}
        with open(os.path.join(DATA, "%s.json" % eid), "w") as f:
            json.dump(rec, f, ensure_ascii=False)
        plan.append(rec)

    # ── ACT: register open speaker slots (real) with gcal day-lock ──────────────
    applied = []
    if a.apply:
        import subprocess
        REL = re.compile(r"AI|LLM|エージェント|agent|Claude|GPT|ChatGPT|Gemini|生成|machine learning|ML|MCP|LT交流|なんでもL|prompt|Cursor|Copilot|RAG|データ|機械学習|ディープ|deep learning|画像生成|音声", re.I)
        for p in [x for x in plan if x["kind"] == "OPEN_SPEAKER"]:
            # relevance gate — only apply to AI/Anicca-relevant talks ("good shit", Dais)
            if not REL.search(p.get("title", "")):
                p["action"] = "skip_irrelevant"; continue
            # Fetch the REAL event time and check overlap with ALL gcal events that day
            # (🎓 school 10-14, 💼 day-job, other bookings) + 60min travel buffer.
            et = event_time(tab, p["url"])
            if not et:
                p["action"] = "skip_no_time"; continue
            d, smin, emin = et
            p["date"] = d; p["time"] = "%02d:%02d-%02d:%02d" % (smin // 60, smin % 60, emin // 60, emin % 60)
            # never violate Mon-Fri 9-17 day-job block
            wd = subprocess.run(["date", "-j", "-f", "%Y-%m-%d", d, "+%u"],
                                capture_output=True, text=True).stdout.strip()
            if wd in ("1", "2", "3", "4", "5") and smin < 17 * 60 and emin > 9 * 60:
                p["action"] = "skip_dayjob_block"; continue
            if gcal_time_conflict(d, smin, emin, buffer_min=60):
                p["action"] = "skip_conflict"; continue
            log = []
            ok = register_speaker(tab, p["url"], log)
            p["action"] = "registered" if ok else "register_failed"
            p["log"] = log
            if ok:
                applied.append(p)
                # Store the ACTUAL event start + venue + connpass URL. Do NOT bake a
                # fixed travel buffer (the old hardcoded "移動60分" caused calls ~40min
                # too early for nearby venues). The lateness engine computes departBy
                # dynamically from Dais's CURRENT location -> venue (real ETA), and
                # renraku finds the organizer from the connpass URL.
                start = "%sT%02d:%02d:00+09:00" % (d, smin // 60, smin % 60)
                end = "%sT%02d:%02d:00+09:00" % (d, emin // 60, emin % 60)
                # Best-effort: pull the real venue address from the connpass page
                # (JSON-LD location), so the lateness engine can geocode it and
                # compute accurate travel from Dais's current location.
                try:
                    place = cf_evaluate(tab, """(()=>{try{for(const s of document.querySelectorAll('script[type=\\"application/ld+json\\"]')){const j=JSON.parse(s.textContent);const arr=j['@graph']||[j];for(const o of arr){const L=o.location;if(L){const a=L.address;return (L.name||'')+' '+(typeof a==='string'?a:(a&&(a.streetAddress||a.addressLocality)||''))}}}}catch(e){}const el=document.querySelector('.event-place, [itemprop=address], .adr');return el?el.textContent.trim().replace(/\\s+/g,' '):''})()""") or ""
                except Exception:
                    place = ""
                place = (place.strip() or p.get("place") or "Tokyo (connpass)")
                subprocess.run(["gog", "calendar", "create", "primary",
                                "--summary", "🎤 [LT] %s" % p["title"][:40],
                                "--from", start, "--to", end,
                                "--location", place,
                                "--description", "LT登壇 connpass:%s 開始:%s (会場・移動はAniccaが現在地から自動計算)" % (p["url"], start)],
                               capture_output=True, timeout=40)

    summary = {"discovered": len(plan),
               "open_speaker": [p for p in plan if p["kind"] == "OPEN_SPEAKER"],
               "outreach": [p for p in plan if p["kind"] == "OUTREACH"],
               "skip": sum(1 for p in plan if p["kind"] == "SKIP"),
               "applied": applied}
    print("CONNPASS_DISCOVER:", json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
