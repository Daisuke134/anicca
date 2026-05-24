#!/usr/bin/env python3
"""suffering-detector : pull WorldMonitor INDIVIDUAL findings (real suffering).

MAIN source = WorldMonitor (worldmonitor.app). We extract each individual
finding (Intelligence Findings / Breaking Alerts / Conflict Zones /
Escalation / Instability), NOT a summary of the dashboard. SUB source
(separate step, model-driven) = crisis-news firecrawl to enrich numbers.

HARD RULE #13 + Dais 2026-05-19: never summarize "what WorldMonitor is" —
list the actual events people are suffering from, with place + scale.

Usage: python3 fetch_worldmonitor.py [out.json]
Writes raw findings lines. Exit 0 if >=5 findings captured.
"""
import json, os, re, subprocess, sys, time

WORK = os.path.expanduser("~/.openclaw/workspace/world-suffering-digest")
os.makedirs(WORK, exist_ok=True)
out_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(WORK, "worldmonitor_raw.json")

URLS = ["https://worldmonitor.app/", "https://worldmonitor.app/?region=MENA",
        "https://worldmonitor.app/?region=Africa", "https://worldmonitor.app/?region=Asia"]

KEEP = re.compile(
    r"CRITICAL|HIGH|escalat|conflict|war\b|strike|killed|casualt|famine|"
    r"displaced|refugee|outbreak|earthquake|flood|drought|crisis|attack|"
    r"instability|destabili|debt|sanction|nuclear|shooting|ho{{profile.lateness.stakeholders.senderType}}|"
    r"humanitarian|starv|siege|MENA|Sudan|Gaza|Ukraine|Lebanon|Afghan|"
    r"Yemen|Congo|Haiti|Myanmar|Syria", re.I)
DROP = re.compile(r"shields\.io|badge|Download|Web App|Tech Variant|"
                  r"Finance Variant|Discord|github\.com|stargazers", re.I)

findings, seen = [], set()
for u in URLS:
    try:
        r = subprocess.run(["/opt/homebrew/bin/firecrawl", "scrape", u, "markdown"],
                            capture_output=True, text=True, timeout=90)
        for ln in r.stdout.splitlines():
            ln = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", ln).strip()
            if not ln or DROP.search(ln) or not KEEP.search(ln):
                continue
            if len(ln) < 8 or len(ln) > 240:
                continue
            key = ln.lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            findings.append({"src": u, "finding": ln})
    except Exception as e:  # noqa
        sys.stderr.write(f"{u} ERR {e}\n")
    time.sleep(1)

out = {"fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%S+09:00"),
       "source": "worldmonitor.app individual findings",
       "count": len(findings), "findings": findings}
json.dump(out, open(out_path, "w"), ensure_ascii=False, indent=1)
for f in findings[:40]:
    print("•", f["finding"])
print(f"WM_FINDINGS_DONE count={len(findings)} out={out_path}")
sys.exit(0 if len(findings) >= 5 else 1)
