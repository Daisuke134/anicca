#!/usr/bin/env python3
"""Read-only inventory of Life Manager candidates in the macOS launchd domain."""

from __future__ import annotations

import argparse
import json
import os
import plistlib
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LM_ROOTS = (
    "/Projects/life-manager-main/",
    "/gig/releases/life-manager/",
    "/loops/life-manager/releases/",
    "/loops/releases/",
    "/loops/current/",
    "/loops/x-social-current/",
    "/loops/connector/releases/",
    "/loops/browser/releases/",
    "/.local/share/life-manager/releases/",
    "/.local/share/anicca/job-search/releases/",
    "/.local/lib/anicca/lancers/releases/",
)


def classify_owner(prior_owner: str | None, command: str) -> str:
    if prior_owner in {"life-manager", "life-manager-runtime", "life-manager-migration"}:
        return "life-manager"
    if prior_owner == "system":
        return "external"
    if any(root in command for root in LM_ROOTS):
        return "life-manager"
    return "ambiguous"


def runtime_state(disabled: bool, loaded: dict | None) -> str:
    if disabled:
        return "disabled"
    if loaded:
        return "loaded-running" if loaded.get("pid") not in {None, "-"} else "loaded-idle"
    return "unloaded"


def extract_release(command: str) -> str | None:
    match = re.search(r"/(?:releases|release)/([0-9a-f]{40})(?:/|$)", command)
    if match:
        return match.group(1)
    match = re.search(r"/releases/[^/]*-([0-9a-f]{8,40})(?:/|$)", command)
    if match:
        return match.group(1)
    if "/Projects/life-manager-main/" in command:
        return "mutable-checkout"
    return None


def parse_loaded(text: str) -> dict[str, dict[str, str | None]]:
    result = {}
    for line in text.splitlines():
        fields = line.split(maxsplit=2)
        if len(fields) == 3 and fields[2].startswith("ai.anicca."):
            result[fields[2]] = {
                "pid": None if fields[0] == "-" else fields[0],
                "last_exit": None if fields[1] == "-" else fields[1],
            }
    return result


def parse_disabled(text: str) -> dict[str, bool]:
    return {
        label: state == "disabled"
        for label, state in re.findall(r'"(ai\.anicca\.[^"]+)"\s*=>\s*(enabled|disabled)', text)
    }


def domain_for(label: str, target: str | None) -> str | None:
    value = f"{label} {target or ''}".lower()
    rules = (
        ("financial", r"cfo|financial|finance|x402|stripe|payout|trade|reinvest|usdc"),
        ("earn", r"gig|bounty|job-search|writer|article|fundraiser|lancers|freelancer|crowdworks|upwork"),
        ("growth", r"marketing|instagram|tiktok|reel|larry|watercolor|x-repost|x-tweeter|affiliate|capafy"),
        ("system", r"health|cleanup|browser|connector|watchdog|monitoring|selfbuild|release-watch|audit"),
    )
    return next((domain for domain, pattern in rules if re.search(pattern, value)), None)


def effect_for(label: str, prior_effect: str | None) -> str:
    if prior_effect in {"none", "publish", "message", "money", "application", "trade", "account_mutation"}:
        return prior_effect
    if re.search(r"trade|reinvest", label):
        return "trade"
    if re.search(r"application|apply|job-search|opportunity-response|fundraiser", label):
        return "application"
    if re.search(r"publish|instagram|tiktok|reel|article|x-repost|x-tweeter|storefront", label):
        return "publish"
    if re.search(r"report|notify|inbox", label):
        return "message"
    return "none"


def launchctl(*args: str) -> str:
    result = subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"launchctl {' '.join(args)} failed")
    return result.stdout


def collect() -> dict:
    prior_doc = json.loads((ROOT / "docs/migrations/openclaw/runtime-inventory.json").read_text())
    prior = {j["legacy_id"]: j for j in prior_doc["jobs"] if j.get("scheduler") == "launchd"}
    loaded = parse_loaded(launchctl("list"))
    disabled = parse_disabled(launchctl("print-disabled", f"gui/{os.getuid()}"))
    plist_dir = Path.home() / "Library/LaunchAgents"
    rows = {}
    for path in sorted(plist_dir.glob("ai.anicca.*.plist")):
        error = None
        try:
            plist = plistlib.load(path.open("rb"))
            label = plist.get("Label") or path.stem
            command = " ".join(map(str, plist.get("ProgramArguments") or []))
        except Exception as exc:
            label, command, error = path.stem, "", type(exc).__name__
        old = prior.get(label, {})
        owner = classify_owner(old.get("owner"), command)
        rows[label] = {
            "label": label,
            "installed": True,
            "owner": owner,
            "domain": domain_for(label, old.get("target_adapter")) if owner == "life-manager" else None,
            "effect_class": effect_for(label, old.get("effect_class")) if owner == "life-manager" else None,
            "launchd_state": runtime_state(disabled.get(label, False), loaded.get(label)),
            "last_exit": loaded.get(label, {}).get("last_exit"),
            "release": extract_release(command),
            "plist": str(path).replace(str(Path.home()), "~"),
            "parse_error": error,
        }
    for label in sorted((set(loaded) | set(disabled)) - set(rows)):
        old = prior.get(label, {})
        owner = classify_owner(old.get("owner"), "")
        rows[label] = {
            "label": label,
            "installed": False,
            "owner": owner,
            "domain": domain_for(label, old.get("target_adapter")) if owner == "life-manager" else None,
            "effect_class": effect_for(label, old.get("effect_class")) if owner == "life-manager" else None,
            "launchd_state": runtime_state(disabled.get(label, False), loaded.get(label)),
            "last_exit": loaded.get(label, {}).get("last_exit"),
            "release": None,
            "plist": None,
            "parse_error": "no-installed-plist",
        }
    values = [rows[label] for label in sorted(rows)]
    return {
        "schema_version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "capture_mode": "read_only",
        "sources": ["~/Library/LaunchAgents/ai.anicca.*.plist", "launchctl list", "launchctl print-disabled gui/<uid>", "docs/migrations/openclaw/runtime-inventory.json"],
        "summary": {
            "labels": len(values),
            "installed": sum(row["installed"] for row in values),
            "owners": dict(Counter(row["owner"] for row in values)),
            "states": dict(Counter(row["launchd_state"] for row in values)),
            "unmanaged_life_manager": sum(row["owner"] == "life-manager" for row in values),
            "ambiguous": sum(row["owner"] == "ambiguous" for row in values),
        },
        "labels": values,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    text = json.dumps(collect(), indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
