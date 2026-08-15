#!/usr/bin/env python3
"""Deliver one immutable Affiliate article to aniccaai.com and read it back."""

import argparse
import hashlib
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from job_journal import JobStateError, reconcile_effect, start_effect, verify_effect
from provider_cli import atomic_write


class PublishError(Exception):
    pass


def git(root, *args):
    result = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True, check=False)
    if result.returncode:
        raise PublishError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def load_artifact(state, slug):
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,100}", slug):
        raise PublishError("invalid article slug")
    path = state / "content" / f"{slug}.json"
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise PublishError("article artifact is unavailable") from error
    if artifact.get("slug") != slug or artifact.get("state") != "READY_FOR_PUBLICATION":
        raise PublishError("article artifact is not publishable")
    markdown = artifact.get("markdown", "")
    if hashlib.sha256(markdown.encode()).hexdigest() != artifact.get("content_sha256"):
        raise PublishError("article artifact hash mismatch")
    if artifact.get("disclosure") == "affiliate_link":
        try:
            policy = json.loads((state / "policy" / f"{slug}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise PublishError("affiliate article policy receipt is unavailable") from error
        if policy.get("decision") != "PASS" or policy.get("content_sha256") != artifact.get("content_sha256"):
            raise PublishError("affiliate article policy receipt does not match")
    return artifact


def public_row(artifact):
    markdown = artifact["markdown"]
    published_date = datetime.fromisoformat(artifact["built_at"]).date().isoformat()
    return {
        "slug": artifact["slug"],
        "title": artifact["title"],
        "date": published_date,
        "project": artifact.get("project", "AI VOICE EVALUATION"),
        "n_papers_cited": len(artifact["source_hashes"]),
        "word_count": len(re.findall(r"\b[\w'-]+\b", markdown)),
        "markdown": markdown,
        "mirrors": {},
    }


def fetch_readback(artifact, base_url):
    url = f"{base_url.rstrip('/')}/blog/{artifact['slug']}"
    request = urllib.request.Request(url, headers={"User-Agent": "Life-Manager-Affiliate/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            markup = response.read().decode("utf-8")
    except Exception:
        return None
    visible = html.unescape(re.sub(r"<[^>]+>", " ", markup))
    decoded_markup = html.unescape(markup)
    if (
        artifact["title"] not in visible
        or any(marker not in visible for marker in artifact["readback_markers"])
        or any(link not in decoded_markup for link in artifact.get("readback_links", []))
    ):
        return None
    return {
        "public_url": url,
        "rendered_sha256": hashlib.sha256(markup.encode()).hexdigest(),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def publish(args):
    state = args.state.expanduser()
    root = args.landing_root.resolve()
    artifact = load_artifact(state, args.slug)
    receipt_path = state / "owned-publications" / f"{args.slug}.json"
    receipt = {}
    if receipt_path.is_file():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("content_sha256") != artifact["content_sha256"]:
            raise PublishError("publication receipt conflicts with artifact")
        live = fetch_readback(artifact, args.base_url)
        if live:
            reconcile_effect(state, "OWNED_GIT_PUSH", args.slug, {
                "state": "LIVE", "public_url": live["public_url"],
                "rendered_sha256": live["rendered_sha256"],
            })
            receipt.update(state="LIVE", **live)
            atomic_write(receipt_path, receipt)
            return receipt
    if git(root, "rev-parse", "--show-toplevel") != str(root):
        raise PublishError("landing root is not the exact git worktree")
    target_relative = f"apps/landing/data/research/{args.slug}.json"
    target = root / target_relative
    expected = json.dumps(public_row(artifact), ensure_ascii=False, indent=2) + "\n"
    dirty = {line[3:] for line in git(root, "status", "--porcelain", "--untracked-files=all").splitlines() if len(line) >= 4}
    if dirty and dirty != {target_relative}:
        raise PublishError("landing worktree has unrelated changes")
    if target.exists() and target.read_text(encoding="utf-8") != expected:
        raise PublishError("public slug conflicts with different content")
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
        temporary.write_text(expected, encoding="utf-8")
        os.replace(temporary, target)
    if not receipt:
        receipt = {
            "schema_version": 1,
            "receipt_type": "OWNED_PUBLICATION",
            "slug": args.slug,
            "content_sha256": artifact["content_sha256"],
            "state": "INTENT",
            "target": target_relative,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_write(receipt_path, receipt)
    if git(root, "status", "--porcelain", "--", target_relative):
        git(root, "add", "--", target_relative)
        if git(root, "diff", "--cached", "--name-only") != target_relative:
            raise PublishError("git index contains a non-publication target")
        git(root, "commit", "-m", f"feat(blog): publish {args.slug}")
    commit = git(root, "rev-parse", "HEAD")
    ref = f"refs/heads/{args.branch}"
    remote_row = git(root, "ls-remote", args.remote, ref)
    remote_head = remote_row.split()[0] if remote_row else None
    job = start_effect(
        state, "OWNED_GIT_PUSH", args.slug,
        {"content_sha256": artifact["content_sha256"], "commit": commit,
         "remote": args.remote, "branch": args.branch},
        {"remote": args.remote, "branch": args.branch, "head": remote_head}, 300,
    )
    git(root, "push", args.remote, f"HEAD:refs/heads/{args.branch}")
    verify_effect(state, job["job_id"], {
        "state": "DELIVERED", "remote": args.remote, "branch": args.branch, "head": commit,
    })
    receipt.update(state="DELIVERED", commit=commit, remote=args.remote, branch=args.branch)
    atomic_write(receipt_path, receipt)
    live = fetch_readback(artifact, args.base_url)
    if live:
        receipt.update(state="LIVE", **live)
        atomic_write(receipt_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(prog="affiliate owned")
    parser.add_argument("command", choices=("publish",))
    parser.add_argument("--slug", required=True)
    parser.add_argument("--landing-root", type=Path, required=True)
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--base-url", default="https://aniccaai.com")
    parser.add_argument("--state", type=Path, default=Path("~/.local/state/life-manager/affiliate"))
    args = parser.parse_args()
    result = publish(args)
    print(json.dumps({key: result.get(key) for key in ("slug", "state", "commit", "public_url", "rendered_sha256")}, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (PublishError, JobStateError, OSError, ValueError, KeyError, json.JSONDecodeError):
        print("affiliate owned: failed closed", file=sys.stderr)
        raise SystemExit(1)
