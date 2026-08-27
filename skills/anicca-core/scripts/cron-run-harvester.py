#!/usr/bin/env python3
"""cron-run-harvester — turn OpenClaw's existing cron run records into structured
event_log entries + a failure/crime brief, for ALL crons at once.

WHY: OpenClaw already writes every cron run to $ANICCA_HOME/cron/runs/<jobId>.jsonl
with {status, error, summary, deliveryStatus, durationMs, ...}. Instead of editing
208 cron scripts to add logging (#39 the dumb way), we HARVEST those records:
read new ones since last cursor, classify each, and emit one event_log line.
This instantly gives WHY-tagged, jq-able error tracking across every cron, and it
is where "fake/dry-run is an ERROR" (#33) lives — a status=ok run whose summary
says "would post"/"exit code 1"/"denied" is reclassified as a failure/crime.

Run from the heartbeat (§2). Prints a brief of NEW failures+crimes to stdout so
§3.5 can pick the highest-value fix; emits events for everything.

Usage:
  cron-run-harvester.py            # harvest since cursor, emit events, print brief
  cron-run-harvester.py --since 6h # ignore cursor, harvest a fixed window
"""
from __future__ import annotations
import json, os, re, sys, time
from pathlib import Path

ANICCA_HOME = Path(os.environ.get("ANICCA_HOME", str(Path.home() / ".openclaw")))
RUNS_DIR = ANICCA_HOME / "cron" / "runs"
JOBS = ANICCA_HOME / "cron" / "jobs.json"
CURSOR = ANICCA_HOME / "state" / "harvester-cursor.json"
sys.path.insert(0, str(ANICCA_HOME / "skills" / "_shared"))
try:
    from event_log import log_event
except Exception:
    def log_event(kind, **f):  # fallback no-op
        pass

# ---- classification patterns -------------------------------------------------
# transient = model quota / cooldown / network. NOT a code bug — heartbeat must NOT
# try to "fix" these with code; they self-heal when quota returns.
TRANSIENT = re.compile(r"rate.?limit|cooldown|usage limit|All models failed|ETIMEDOUT|ECONNRESET|timed? out", re.I)
# crime = faking success / never actually doing the work (HARD RULE #14).
# PRECISE machine markers only — NOT loose English (a "no recipients, sent nothing" honest
# no-op must NOT be flagged). Real fakes emit bracketed DRY markers or carry a DRY_RUN flag.
CRIME = re.compile(r"\[would-run\]|\[DRY[\s|\]]|DRY_RUN=true|DRY_RUN=1|--dry-run|would transfer \$", re.I)
# a cron whose PAYLOAD hardcodes a dry-run flag is a crime regardless of output (politician×12, donation, bip).
PAYLOAD_DRY = re.compile(r"_DRY_RUN=true|DRY_RUN=1|--dry-run|\bMODE=dry\b", re.I)
# false-ok = status says ok but the narrative betrays a real failure.
FALSE_OK = re.compile(r"exit code [1-9]|denied|実行できませんでした|Message failed|failed to|error:", re.I)
# #72 content false-ok: cron claims "posted TT+YT" or "posted TikTok/IG/YT" but no matching
# *_POST_ID=cm... in the summary = LLM agent lied about calling Postiz curl (今日 reelclaw
# 5/27-28 17本 / 5/28 reelclaw 全6本 がこのパターン). We expect orchestrator output
# "TT_POST_ID=cm..." / "IG_POST_ID=cm..." / "YT_POST_ID=cm..." for each platform claimed.
CONTENT_CLAIM = re.compile(r"posted (TT|TikTok|IG|Instagram|YT|YouTube)", re.I)
CONTENT_PROOF = re.compile(r"(TT|IG|YT)_POST_ID\s*=\s*cm[a-z0-9]+", re.I)
CONTENT_EXPLICIT_FAIL = re.compile(r"(TT|IG|YT)_POST_ID\s*=\s*(NONE|FAILED)", re.I)
# delivery config error — known, cron-doctor auto-fixable.
DELIVERY = re.compile(r"Delivering to Slack requires target|delivery", re.I)


def load_jobs():
    try:
        d = json.loads(JOBS.read_text())
        jobs = d if isinstance(d, list) else d.get("jobs", [])
        out = {}
        for j in jobs:
            jid = j.get("id") or j.get("name")
            p = j.get("payload", {}) or {}
            body = " ".join(str(p.get(k, "")) for k in ("message", "prompt", "command"))
            out[jid] = {"name": j.get("name", jid), "enabled": j.get("enabled", True), "payload": body}
        return out
    except Exception:
        return {}


def load_cursor():
    try:
        return json.loads(CURSOR.read_text())
    except Exception:
        return {}


def save_cursor(c):
    CURSOR.parent.mkdir(parents=True, exist_ok=True)
    CURSOR.write_text(json.dumps(c))


def classify(rec, payload):
    """Return (kind, severity, why). kind ∈ cron.ok|cron.failed|crime.detected."""
    status = rec.get("status", "?")
    err = str(rec.get("error") or "")
    summary = str(rec.get("summary") or "")
    blob = f"{err} {summary} {payload}"
    why = (err or summary or "").strip().replace("\n", " ")[:300]
    # 1. crime: faking it (even if status=ok). Highest priority — Dais's #1 concern.
    #    Either the payload hardcodes a dry-run flag, OR the output carries a bracketed DRY marker.
    if PAYLOAD_DRY.search(payload) or CRIME.search(f"{err} {summary}"):
        return "crime.detected", "crime", (why or "dry-run flag/marker — not doing real work")
    # 2. hard error
    if status == "error":
        sev = "transient" if TRANSIENT.search(blob) else "real"
        return "cron.failed", sev, why or "status=error (no detail)"
    # 3. false-ok: status=ok but narrative shows failure
    if status == "ok" and FALSE_OK.search(blob) and not DELIVERY.search(blob):
        return "cron.failed", "false-ok", why or "status=ok but summary shows failure"
    # 3b. #72 content false-ok: cron claims "posted X" but no *_POST_ID=cm... proof
    if status == "ok":
        if CONTENT_EXPLICIT_FAIL.search(blob):
            return "cron.failed", "false-ok", "summary explicitly says *_POST_ID=NONE/FAILED"
        if CONTENT_CLAIM.search(blob) and not CONTENT_PROOF.search(blob):
            return "cron.failed", "false-ok", "summary claims 'posted X' but no *_POST_ID=cm... proof — LLM agent likely skipped Postiz curl"
    # 4. genuinely ok (or ok-with-delivery-warning, which cron-doctor handles)
    if status == "skipped":
        return "cron.ok", "skipped", "skipped"
    return "cron.ok", "ok", ""


def main():
    since_arg = None
    if len(sys.argv) > 2 and sys.argv[1] == "--since":
        m = re.match(r"(\d+)([hd])", sys.argv[2])
        if m:
            n, unit = int(m.group(1)), m.group(2)
            since_arg = time.time() * 1000 - n * (3600 if unit == "h" else 86400) * 1000

    jobs = load_jobs()
    cursor = load_cursor()
    first_run = not cursor and since_arg is None
    default_floor = time.time() * 1000 - 24 * 3600 * 1000  # first run: only last 24h, avoid huge backfill

    new_fail, new_crime, counts = [], [], {"ok": 0, "failed": 0, "crime": 0}
    if not RUNS_DIR.exists():
        print("cron-run-harvester: no runs dir")
        return

    # v2026.6.1 migration renamed some run records to *.jsonl.migrated.
    # Harvest both spellings and normalize the job id back to the original basename.
    run_files = list(RUNS_DIR.glob("*.jsonl")) + list(RUNS_DIR.glob("*.jsonl.migrated"))
    for f in sorted({p.resolve(): p for p in run_files}.values(), key=lambda p: p.name):
        if f.name.endswith(".jsonl.migrated"):
            jid = f.name[: -len(".jsonl.migrated")]
        else:
            jid = f.stem
        meta = jobs.get(jid, {"name": jid, "payload": ""})
        floor = since_arg if since_arg is not None else (default_floor if first_run else cursor.get(jid, 0))
        last_ts = cursor.get(jid, 0)
        try:
            lines = f.read_text().splitlines()
        except Exception:
            continue
        for line in lines:
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("action") != "finished":
                continue
            ts = rec.get("ts", 0)
            if ts <= floor:
                continue
            kind, sev, why = classify(rec, meta["payload"])
            log_event(kind, cron=meta["name"], jobId=jid, severity=sev,
                      why=why, durationMs=rec.get("durationMs"), deliveryStatus=rec.get("deliveryStatus"))
            if kind == "crime.detected":
                counts["crime"] += 1
                new_crime.append(f"🔴 {meta['name']} [{sev}] {why[:120]}")
            elif kind == "cron.failed":
                counts["failed"] += 1
                # transient (quota) failures are noise — note but don't escalate as fixable
                tag = "⏳transient" if sev == "transient" else ("⚠️false-ok" if sev == "false-ok" else "❌real")
                new_fail.append(f"{tag} {meta['name']}: {why[:120]}")
            else:
                counts["ok"] += 1
            last_ts = max(last_ts, ts)
        cursor[jid] = last_ts

    save_cursor(cursor)

    # brief for the heartbeat
    print(f"cron-run-harvester: new ok={counts['ok']} failed={counts['failed']} crime={counts['crime']}")
    if new_crime:
        print("CRIME (fake/dry-run = HARD RULE #14 — fix or kill in §3.5):")
        for c in new_crime[:20]:
            print("  " + c)
    real = [x for x in new_fail if x.startswith("❌") or x.startswith("⚠️")]
    if real:
        print("FAILURES (real / false-ok — fix root cause in §3.5):")
        for x in real[:25]:
            print("  " + x)
    trans = [x for x in new_fail if x.startswith("⏳")]
    if trans:
        # #42: LIST the transient items (not just a count) so §3.5 can RECONCILE them once the
        # provider cooldown clears. Do NOT code-fix; instead re-run unposted CONTENT crons via
        # `openclaw cron run <id>` under the (a)/(b)/(c) dup-post guard in HEARTBEAT §3.5.
        print(f"TRANSIENT/QUOTA ({len(trans)} — do NOT code-fix; RECONCILE unposted content crons after cooldown clears, §3.5 dup-guard):")
        for x in trans[:25]:
            print("  " + x)


if __name__ == "__main__":
    main()
