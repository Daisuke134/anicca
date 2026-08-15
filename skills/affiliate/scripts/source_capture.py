#!/usr/bin/env python3
"""Capture official web and GitHub evidence into immutable local artifacts."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from provider_cli import atomic_write


class CaptureError(Exception):
    pass


def load_plan(root, plan_id):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]+", plan_id):
        raise CaptureError("invalid source plan id")
    path = root / "config" / "source-plans" / f"{plan_id}.json"
    try:
        plan = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise CaptureError("invalid source plan") from error
    if plan.get("schema_version") != 1 or plan.get("plan_id") != plan_id:
        raise CaptureError("unsupported source plan")
    return plan


def classify_failure(returncode, output):
    lowered = output.lower()
    if returncode == 0 and output.strip():
        return None
    if "429" in lowered or "rate limit" in lowered:
        return "RATE_LIMIT"
    if "401" in lowered or "403" in lowered or "unauthorized" in lowered:
        return "AUTH"
    if returncode == 0:
        return "EMPTY"
    return "UPSTREAM"


def run_adapter(source):
    adapter = source.get("adapter")
    if adapter == "crwl":
        binary = shutil.which("crwl")
        if not binary:
            raise CaptureError("crwl is unavailable")
        command = [binary, "crawl", source["url"], "-o", "md-fit", "-bc"]
    elif adapter == "gh":
        binary = shutil.which("gh")
        if not binary:
            raise CaptureError("gh is unavailable")
        command = [binary, "api", f"repos/{source['repo']}"]
    else:
        raise CaptureError("unsupported source adapter")
    result = subprocess.run(command, capture_output=True, text=True, timeout=90, check=False)
    output = result.stdout
    failure = classify_failure(result.returncode, output + result.stderr)
    if failure:
        raise CaptureError(failure)
    if adapter == "gh":
        try:
            repo = json.loads(output)
            observed_license = repo.get("license", {}).get("spdx_id")
        except (AttributeError, ValueError) as error:
            raise CaptureError("PARSER") from error
        if observed_license != source["license"]:
            raise CaptureError("POLICY")
        output = json.dumps({
            "archived": repo.get("archived"),
            "default_branch": repo.get("default_branch"),
            "full_name": repo.get("full_name"),
            "html_url": repo.get("html_url"),
            "license": observed_license,
            "pushed_at": repo.get("pushed_at"),
        }, sort_keys=True, separators=(",", ":")) + "\n"
    return output


def append_unique(path, receipt):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("a+", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.seek(0)
        for line in stream:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("source_id") == receipt["source_id"] and row.get("raw_sha256") == receipt["raw_sha256"]:
                return False
        stream.write(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
        return True


def capture(plan, state_root):
    now = datetime.now(timezone.utc)
    receipts = []
    for source in plan["sources"]:
        raw = run_adapter(source)
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        directory = state_root / "sources" / source["id"]
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        suffix = "json" if source["adapter"] == "gh" else "md"
        artifact = directory / f"{digest}.{suffix}"
        if not artifact.exists():
            fd, name = tempfile.mkstemp(prefix=".capture-", dir=directory)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, artifact)
        receipt = {
            "schema_version": 1,
            "receipt_type": "SOURCE_CAPTURE",
            "plan_id": plan["plan_id"],
            "source_id": source["id"],
            "adapter": source["adapter"],
            "locator": source.get("url") or f"https://github.com/{source['repo']}",
            "locale": plan["locale"],
            "evidence_class": source["evidence_class"],
            "license": source["license"],
            "raw_sha256": digest,
            "parser_version": "crwl-md-fit-v1" if source["adapter"] == "crwl" else "gh-api-v1",
            "failure_class": None,
            "observed_at": now.isoformat(),
            "expires_at": (now + timedelta(days=source["freshness_days"])).isoformat(),
        }
        receipt["new_capture"] = append_unique(state_root / "source-captures.jsonl", receipt)
        atomic_write(directory / "latest.json", receipt)
        receipts.append(receipt)
    return receipts


def main():
    parser = argparse.ArgumentParser(prog="affiliate sources")
    parser.add_argument("command", choices=("capture",))
    parser.add_argument("--plan", default="elevenlabs-en")
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    receipts = capture(load_plan(root, args.plan), args.state.expanduser())
    print(json.dumps({"plan_id": args.plan, "captured": len(receipts), "new": sum(row["new_capture"] for row in receipts)}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CaptureError, OSError, ValueError, KeyError, subprocess.SubprocessError):
        print("affiliate sources: failed closed", file=sys.stderr)
        raise SystemExit(1)
