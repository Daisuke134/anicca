#!/usr/bin/env python3
"""daily-report — compose USEFUL daily digest from local Anicca state.

Reads (no writes):
  - anicca-cfo.json     (numbers)
  - heartbeat.jsonl     (Hermes genesis liveness)
  - violations.jsonl    (friction-fixer)
  - friction-sweep.log  (constitution-violations text grep)

Emits to stdout:
  Line 1: SUBJECT: <subject>
  Line 2: BODY-START
  ...    <body, multi-line>
  Line N: BODY-END

--offline skips the LLM bullets call; sections appear with placeholder
"(LLM-offline — no bullets)". Used by unit tests. Live runs OMIT --offline.
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

JST = timezone(timedelta(hours=9))
INSTALL_TS_FILE = Path.home() / ".hermes" / "state" / "anicca_install_ts"


def _f(x) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def day_number(now: datetime) -> int:
    """Day N since first ever Hermes/Anicca beat — recorded on first run."""
    if not INSTALL_TS_FILE.exists():
        INSTALL_TS_FILE.parent.mkdir(parents=True, exist_ok=True)
        INSTALL_TS_FILE.write_text(str(int(now.timestamp())))
    try:
        installed_ts = int(INSTALL_TS_FILE.read_text().strip())
    except (ValueError, OSError):
        installed_ts = int(now.timestamp())
    return max(1, int((now.timestamp() - installed_ts) // 86400) + 1)


def read_cfo(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def cfo_overview(cfo: dict) -> dict:
    makes = cfo.get("makes") or {}
    spends = cfo.get("spends") or {}
    lifeline = cfo.get("lifeline") or {}
    wallet_block = cfo.get("wallet") or {}
    mrr = _f(makes.get("mrr_usd"))
    revenue_28d = _f(makes.get("revenue_28d_usd"))
    landed_28d = _f(makes.get("actually_landed_usd"))
    runtime_cost = _f(spends.get("anicca_runtime_usd"))
    net_monthly = _f(lifeline.get("net_monthly_usd"))
    status = (lifeline.get("status") or "?").upper()
    msg = lifeline.get("message") or ""
    wallet_usd = _f(wallet_block.get("base_usdc") or wallet_block.get("usd_total"))
    runway_days = (
        int(wallet_usd / (runtime_cost / 30.0))
        if (wallet_usd > 0 and runtime_cost > 0)
        else -1
    )
    return {
        "mrr": mrr,
        "revenue_28d": revenue_28d,
        "landed_28d": landed_28d,
        "runtime_cost": runtime_cost,
        "net_monthly": net_monthly,
        "status": status,
        "message": msg,
        "wallet_usd": wallet_usd,
        "runway_days": runway_days,
        "runtime_items": spends.get("runtime_items") or [],
    }


def parse_heartbeats_24h(path: Path, now: datetime) -> tuple[int, int]:
    """Return (ok_count, total_count) for heartbeat entries in last 24h."""
    if not path.exists():
        return (0, 0)
    cutoff = now - timedelta(hours=24)
    ok = 0
    total = 0
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = row.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts < cutoff:
            continue
        total += 1
        if row.get("ok") is True:
            ok += 1
    return (ok, total)


def parse_violations_24h(path: Path, now: datetime) -> list[dict]:
    """Return friction-fixer violations within last 24h."""
    if not path.exists():
        return []
    cutoff = now - timedelta(hours=24)
    rows: list[dict] = []
    for line in path.read_text(errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts_str = row.get("ts", "")
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts >= cutoff:
            rows.append(row)
    return rows


def parse_constitution_violations_24h(path: Path, now: datetime) -> list[str]:
    """Grep friction-sweep.log for last 24h. Lines starting YYYY-MM-DDTHH."""
    if not path.exists():
        return []
    cutoff = now - timedelta(hours=24)
    out: list[str] = []
    for line in path.read_text(errors="ignore").splitlines()[-2000:]:
        m = re.match(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})", line)
        if not m:
            continue
        try:
            ts = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        if ts >= cutoff and ("VIOLATION" in line or "violation" in line):
            out.append(line[:200])
    return out


def llm_bullets(probe: dict) -> tuple[list[str], int, float]:
    """Call Hermes via `hermes chat -q` for 3 substantive bullets.

    Returns (bullets, tokens_estimated, cost_usd_estimated). Hermes does NOT
    return precise token counts in chat-q mode, so we estimate from char count
    at ~4 chars/token + $5e-6 / token (mini model ballpark). Used for budget
    enforcement only — Wave-2 hooks proper accounting via hermes insights.
    """
    hermes = os.environ.get("HERMES_BIN", "/Users/operator/.local/bin/hermes")
    prompt = (
        "You are oss-anicca (the open-source Hermes-running instance of Anicca, "
        "distinct from the private OpenClaw-running Anicca on Dais's primary "
        "machine) writing a USEFUL daily report. Given this state probe as "
        "JSON, output EXACTLY 3 bullets of what oss-anicca did or learned "
        "yesterday. Sign the report tagline as 'oss-anicca'. Bullets must be "
        "substantive (bookmark-able), not generic affirmation. Format: "
        "'- <bullet>'. No preamble.\n\n"
        f"PROBE:\n{json.dumps(probe, ensure_ascii=False)[:2000]}"
    )
    try:
        out = subprocess.run(
            [hermes, "chat", "-q", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"[compose] LLM call failed: {e}", file=sys.stderr)
        return (["(LLM unreachable — header-only mode)"], 0, 0.0)
    if out.returncode != 0:
        return ([f"(LLM rc={out.returncode}; stderr={out.stderr[:120]})"], 0, 0.0)
    lines = [ln.strip() for ln in out.stdout.splitlines() if ln.strip().startswith("-")]
    bullets = lines[:3] if lines else ["(LLM returned no bullets)"]
    chars = len(out.stdout) + len(prompt)
    tokens = chars // 4
    cost = tokens * 5e-6
    return (bullets, tokens, cost)


def compose(args) -> tuple[str, str, dict]:
    """Returns (subject, body, trace_dict)."""
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(JST)
    cfo = read_cfo(Path(args.cfo))
    o = cfo_overview(cfo)
    ok, total = parse_heartbeats_24h(Path(args.heartbeat), now)
    violations = parse_violations_24h(Path(args.violations), now)
    constitution = parse_constitution_violations_24h(
        Path(args.friction_log), now
    ) if args.friction_log else []
    day_n = day_number(now)

    runway_str = f"{o['runway_days']}d runway" if o["runway_days"] >= 0 else "runway —"
    subject = (
        f"[Anicca] Day {day_n} — MRR ${o['mrr']:.0f} · "
        f"runtime ${o['runtime_cost']:.0f} · status {o['status']}"
    )

    body_lines = [
        f"Hi,",
        "",
        f"Headline ({now.strftime('%Y-%m-%d')}):",
        f"  MRR:             ${o['mrr']:.2f} / mo",
        f"  Revenue 28d:     ${o['revenue_28d']:.2f}  (landed ${o['landed_28d']:.2f})",
        f"  Runtime cost:    ${o['runtime_cost']:.2f} / mo",
        f"  Net:             ${'+' if o['net_monthly'] >= 0 else ''}{o['net_monthly']:.2f} / mo",
        f"  Wallet:          ${o['wallet_usd']:.2f}  ({runway_str})",
        f"  Status:          {o['status']}  {('— ' + o['message']) if o['message'] else ''}",
        "",
        f"Yesterday's heartbeat:",
        f"  {ok}/{total} ok in the last 24h",
        "",
        f"Constitution-violations (24h):",
    ]
    if constitution:
        body_lines.extend([f"  - {c[:160]}" for c in constitution[:5]])
    else:
        body_lines.append("  none today")
    body_lines.append("")
    body_lines.append("Errors from friction-fixer (24h):")
    if violations:
        for v in violations[:5]:
            patt = v.get("pattern_id") or v.get("pattern") or "?"
            fix = v.get("fix_script") or v.get("source") or "?"
            exit_code = v.get("exit_code")
            if exit_code is not None:
                outcome = "resolved" if exit_code == 0 else f"exit {exit_code}"
            else:
                outcome = "resolved" if v.get("resolved") else "open"
            evidence = v.get("evidence")
            tail = f" — {evidence}" if evidence else ""
            body_lines.append(f"  - [{patt}] {fix} ({outcome}){tail}")
    else:
        body_lines.append("  none today")
    body_lines.append("")
    body_lines.append("What I did:")

    probe = {
        "day": day_n,
        "mrr": o["mrr"],
        "runtime": o["runtime_cost"],
        "net": o["net_monthly"],
        "status": o["status"],
        "heartbeat_24h": f"{ok}/{total}",
        "violations_24h": len(violations),
        "constitution_24h": len(constitution),
    }
    tokens = 0
    cost = 0.0
    if args.offline:
        body_lines.append("  (LLM-offline — no bullets)")
    else:
        bullets, tokens, cost = llm_bullets(probe)
        body_lines.extend([f"  {b}" for b in bullets])

    body_lines.extend([
        "",
        "— Anicca",
        "   /report off  ·  /report to <email>",
    ])

    body = "\n".join(body_lines)
    trace = {
        "day_n": day_n,
        "mrr": o["mrr"],
        "runtime_cost": o["runtime_cost"],
        "status": o["status"],
        "heartbeat_ok": ok,
        "heartbeat_total": total,
        "violations_24h": len(violations),
        "constitution_24h": len(constitution),
        "llm_tokens": tokens,
        "llm_cost_usd": cost,
        "body_chars": len(body),
    }
    return subject, body, trace


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cfo", default="/Users/operator/.openclaw/skills/cfo-core/data/anicca-cfo.json")
    p.add_argument("--heartbeat", default="/Users/operator/.hermes/state/heartbeat.jsonl")
    p.add_argument("--violations", default="/Users/operator/.openclaw/skills/anicca-friction-fixer/state/violations.jsonl")
    p.add_argument("--friction-log", default="/Users/operator/.openclaw/state/friction-sweep.log")
    p.add_argument("--now", default="", help="ISO8601 override (test only)")
    p.add_argument("--offline", action="store_true", help="skip LLM bullets")
    p.add_argument("--json", action="store_true", help="also print trace JSON to stderr")
    args = p.parse_args(argv)
    subject, body, trace = compose(args)
    print(f"SUBJECT: {subject}")
    print("BODY-START")
    print(body)
    print("BODY-END")
    if args.json:
        print(json.dumps(trace, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
