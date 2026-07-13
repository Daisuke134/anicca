#!/usr/bin/env python3
"""
GUILD FEED aggregator — one unified board of REAL-MONEY agent/AI jobs, for EVERY agent.
Polls each source adapter (verified-live 2026-06-29), normalizes, writes guild_feed.json.
Add a source = add one adapter to ADAPTERS. launchd runs this every minute.

Schema: {source, id, title, reward_amount, reward_currency, real_money, no_human, url, deadline, status}
real_money = USDC/USDT/ETH/USDG/SOL/MATIC/fiat with value (NOT protocol points)
no_human   = AI can complete + claim with wallet/web/API (no captcha/account-KYC/PR-merge)
"""
import json, time, re, html as _html, urllib.request, urllib.error, os

OUT = os.path.expanduser("~/.claude/skills/earn-gig/scripts/guild/guild_feed.json")
UA = {"User-Agent": "guild-aggregator/2.0", "Accept": "application/json"}
LIQUID = {"USDC", "USDT", "ETH", "WETH", "USDG", "SOL", "MATIC", "BTC", "USD", "DAI", "XDAI"}

def _get(url, timeout=18):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read())

def _post(url, body, timeout=20, hdr=None):
    h = dict(UA); h["Content-Type"] = "application/json"
    if hdr: h.update(hdr)
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=h), timeout=timeout).read())

def norm(source, id, title, amt, cur, real_money, no_human, url, deadline=None, status="open"):
    return {"source": source, "id": str(id), "title": title, "reward_amount": amt,
            "reward_currency": cur, "real_money": real_money, "no_human": no_human,
            "url": url, "deadline": deadline, "status": status}

# ── Adapters (verified live 2026-06-29) ──
def a_dealwork():
    d = _get("https://dealwork.ai/api/v1/jobs"); jobs = []
    for j in (d.get("jobs", d.get("data", [])) if isinstance(d, dict) else []):
        lo, hi = j.get("budgetMin"), j.get("budgetMax")
        amt = j.get("fixedPrice") or (f"{lo}-{hi}" if lo else None)
        jobs.append(norm("dealwork.ai", j.get("id"), j.get("title"), amt, "USD",
                         True, True, f"https://dealwork.ai/explore", j.get("biddingDeadline"),
                         j.get("status", "open")))
    return jobs

def a_dework():
    q = {"query": '{getTasks(input:{statuses:[TODO]}){id name status rewards{amount peggedToUsd token{symbol}}}}'}
    d = _post("https://api.dework.xyz/graphql", q); jobs = []
    for t in (d.get("data", {}).get("getTasks", []) or []):
        rs = t.get("rewards") or []
        if not rs: continue
        r0 = rs[0]; sym = (r0.get("token") or {}).get("symbol", "?")
        if sym.upper() not in LIQUID: continue   # only liquid-token rewards
        jobs.append(norm("Dework", t.get("id"), t.get("name"), r0.get("peggedToUsd") or r0.get("amount"),
                         sym, True, False, "https://app.dework.xyz", None, "TODO"))
    return jobs

def a_superteam():
    d = _get("https://earn.superteam.fun/api/listings/?take=40")
    items = d if isinstance(d, list) else d.get("listings", d.get("data", []))
    jobs = []
    for l in (items or []):
        agent_ok = str(l.get("agentAccess", "")).upper() == "AGENT_ALLOWED"
        jobs.append(norm("SuperteamEarn", l.get("id", l.get("slug")), l.get("title"),
                         l.get("rewardAmount"), str(l.get("token", "USDC")).upper(), True, agent_ok,
                         f"https://earn.superteam.fun/listing/{l.get('slug','')}", l.get("deadline"),
                         l.get("status", "open")))
    return jobs

def a_claw_earn():
    d = _get("https://aiagentstore.ai/claw/tasks"); jobs = []
    for t in d.get("items", []):
        rw = t.get("reward", t.get("amount", 0))
        try: usd = int(rw) / 1e6
        except Exception: usd = rw
        cat = (str(t.get("category", "")) + str(t.get("title", ""))).lower()
        no_h = not any(s in cat for s in ("link building", "seo", "backlink", "guest post", "listing", "sales", "referral"))
        jobs.append(norm("ClawEarn", t.get("taskId", t.get("id")), t.get("title"), usd, "USDC",
                         True, no_h, "https://aiagentstore.ai/claw-earn", t.get("deadline")))
    return jobs

def a_aigen():
    d = _get("https://cryptogenesis.duckdns.org/work/board"); jobs = []
    for m in d.get("categories", {}).get("missions_open", {}).get("items", []):
        cur = str(m.get("reward_currency", "AIGEN")).upper()
        jobs.append(norm("AIGEN", m.get("id"), m.get("title"), m.get("reward_amount"), cur,
                         cur in LIQUID, True, f"https://cryptogenesis.duckdns.org/missions/{m.get('id')}", m.get("deadline")))
    return jobs

def a_clankonomy():
    d = _get("https://api.clankonomy.com/bounties"); jobs = []
    items = d if isinstance(d, list) else d.get("bounties", d.get("data", []))
    for b in (items or []):
        st = str(b.get("status", "")).lower()
        if st not in ("open", "active", "", "available"): continue
        jobs.append(norm("Clankonomy", b.get("id"), b.get("title", b.get("name")),
                         b.get("reward", b.get("amount")), "USDC", True, True,
                         "https://clankonomy.com", b.get("deadline"), st or "open"))
    return jobs

def a_clustly():
    d = _get("https://clustly.ai/api/tasks"); jobs = []
    for t in (d.get("data", []) if isinstance(d, dict) else []):
        jobs.append(norm("Clustly", t.get("id"), t.get("title", t.get("name")),
                         t.get("reward", t.get("amount")), "USDC", True, True,
                         "https://clustly.ai", t.get("deadline")))
    return jobs

def a_cantina():
    d = _get("https://cantina.xyz/api/v0/competitions"); jobs = []
    comps = d if isinstance(d, list) else d.get("competitions", d.get("data", []))
    for c in (comps or []):
        st = str(c.get("status", "")).lower()
        if st != "active": continue
        jobs.append(norm("Cantina", c.get("id", c.get("slug")), c.get("title", c.get("name")),
                         c.get("totalRewardPot"), str(c.get("currencyCode", "USDC")).upper(),
                         True, False, c.get("url", "https://cantina.xyz/competitions"),
                         (c.get("timeframe") or {}).get("end"), st))
    return jobs

def a_sherlock():
    d = _get("https://mainnet-contest.sherlock.xyz/contests?page=0"); jobs = []
    items = d if isinstance(d, list) else d.get("contests", d.get("data", []))
    for c in (items or []):
        st = str(c.get("status", "")).upper()
        if st != "RUNNING": continue
        jobs.append(norm("Sherlock", c.get("id"), c.get("title", c.get("name")),
                         c.get("prize_pool", c.get("rewards")), str(c.get("token", "USDC")).upper(),
                         True, False, "https://audits.sherlock.xyz", c.get("ends_at"), st))
    return jobs

def a_recall():
    d = _get("https://api.competitions.recall.network/api/competitions?status=active"); jobs = []
    comps = d.get("competitions", d.get("data", [])) if isinstance(d, dict) else d
    for c in (comps or []):
        jobs.append(norm("Recall", c.get("id"), c.get("name", c.get("title")), None, "RECALL",
                         True, True, "https://app.recall.network", c.get("endDate", c.get("ends_at")), "active"))
    return jobs

def a_laborx():
    # Public SSR /jobs HTML (no login). Parse proven by sjjdjdidjdj-cmyk/laborx-parser.
    # Scrape first few pages of newest jobs (newest = least competition).
    jobs, seen = [], set()
    for pg in range(1, 4):
        url = "https://laborx.com/jobs" + ("" if pg == 1 else f"?page={pg}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            h = urllib.request.urlopen(req, timeout=18).read().decode("utf-8", "ignore")
        except Exception:
            break
        for blk in re.split(r'class="[^"]*job-card[^"]*"', h)[1:]:
            hm = re.search(r'href="(/jobs/[a-z0-9-]+-\d+)"', blk)
            if not hm:
                continue
            href = hm.group(1)
            if href in seen:
                continue
            seen.add(href)
            tm = re.search(r'href="' + re.escape(href) + r'"[^>]*>\s*([^<]{4,90})', blk)
            title = _html.unescape(tm.group(1).strip()) if tm else href.split("/")[-1]
            bm = re.search(r'\$\s*([\d,]+(?:\.\d+)?)', blk[:1800])
            amt = bm.group(1).replace(",", "") if bm else None
            jobs.append(norm("LaborX", href.split("-")[-1], title, amt, "USD",
                             True, True, "https://laborx.com" + href, None, "open"))
    return jobs

ADAPTERS = [
    ("dealwork.ai", a_dealwork), ("LaborX", a_laborx), ("Dework", a_dework), ("SuperteamEarn", a_superteam),
    ("ClawEarn", a_claw_earn), ("AIGEN", a_aigen), ("Clankonomy", a_clankonomy),
    ("Clustly", a_clustly), ("Cantina", a_cantina), ("Sherlock", a_sherlock), ("Recall", a_recall),
]

def main():
    all_jobs, errors, per = [], [], {}
    for name, fn in ADAPTERS:
        try:
            js = fn(); all_jobs.extend(js); per[name] = len(js)
        except Exception as e:
            errors.append({"source": name, "error": str(e)[:100]}); per[name] = "err"
    real_open = [j for j in all_jobs if j["real_money"]]
    real_nohuman = [j for j in all_jobs if j["real_money"] and j["no_human"]]
    feed = {
        "generated_at": int(time.time()),
        "sources": per, "errors": errors,
        "counts": {"total": len(all_jobs), "real_money": len(real_open),
                   "real_money_no_human": len(real_nohuman)},
        "jobs": sorted(all_jobs, key=lambda j: (not (j["real_money"] and j["no_human"]), not j["real_money"])),
    }
    with open(OUT, "w") as f:
        json.dump(feed, f, ensure_ascii=False, indent=1)
    print(f"counts={feed['counts']}  per_source={per}  errors={len(errors)}")
    for j in real_nohuman[:12]:
        print(f"  ★ {j['source']} {j['reward_amount']} {j['reward_currency']} — {str(j['title'])[:46]}")

if __name__ == "__main__":
    main()
