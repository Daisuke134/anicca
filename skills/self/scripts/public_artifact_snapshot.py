#!/usr/bin/env python3
"""public_artifact_snapshot.py — deterministic, logged-out capture tool (feature reality-gate,
behavioral-spec REQ-012, HMAC signing REQ-016/017).

Structurally incapable of authenticated access: uses a bare `urllib.request.urlopen` call per
URL, no cookie jar, no Authorization header, no session/opener reuse across requests, never
touches CDP:9222. Every captured row is HMAC-signed under a per-run secret read from STDIN
(never argv, never an env var, never written under the trail directory itself — REQ-016/
PROP-051) so `reality-verdict-schema.mjs`'s `enforceVerdict` can recompute the signature and
detect same-uid tampering (REQ-017) after the fact.

Usage:
  echo -n "<hmac-secret>" | python3 public_artifact_snapshot.py --pass-id <passId|-> \
      --trail-dir <dir> <url> [<url2> ...]

  --pass-id -   generate a fresh CSPRNG passId (>=128 bits) instead of accepting a caller value
                (this tool never trusts a caller-chosen passId as authoritative for anything
                beyond labeling its own output row; the wrapper that OWNS trust decisions is
                reality-verify-spawn.sh, out of this tool's scope).

Behavior:
  - <trail-dir> is created via an EXCLUSIVE mkdir (no -p). If it already exists, this tool
    refuses to write anything and exits non-zero — a pre-existing directory at a path this run
    was about to claim is not a "collision to tolerate", it is something to disclose upward
    (REQ-012/017; the classification of that fact as `artifact_trail_tampered` is
    `enforceVerdict`'s job, not this tool's).
  - One JSONL row per requested URL is appended to `<trail-dir>/artifacts.jsonl`:
      {tool, passId, ts, requestedUrl, finalUrl, httpStatus, domExcerpt, contentHash,
       networkError?, rowHmac}
  - A network-level failure (timeout / connection refused / DNS failure — no real HTTP response
    ever received) records `httpStatus: null` plus `networkError: "<class>"`; it NEVER defaults
    to, or is conflated with, a real in-range status code.
  - A soft-404 (real HTTP 200 with a not-found-looking body) is NOT special-cased: the tool
    records the real, accurate httpStatus/domExcerpt it observed and lets `enforceVerdict`'s
    taxonomy (never this tool) decide what that means.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.request

TOOL_NAME = "public_artifact_snapshot"
MAX_EXCERPT_CHARS = 2000


def canonical_row_for_signing(row: dict) -> str:
    """Deterministic, cross-language-compatible serialization: sorted keys, `rowHmac` always
    excluded, no extra whitespace, unicode left un-escaped — MUST byte-for-byte match
    reality-verdict-schema.mjs's canonicalRowForSigning (sorted-key JSON.stringify)."""
    rest = {k: v for k, v in row.items() if k != "rowHmac"}
    return json.dumps(rest, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_row_hmac(secret: str, row: dict) -> str:
    payload = canonical_row_for_signing(row).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def generate_pass_id() -> str:
    # >=128 bits of CSPRNG entropy (REQ-012/FIND-Q) — never time+PID-derived.
    return f"realitygate-{secrets.token_hex(16)}"


def classify_network_error(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.URLError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, OSError):
            errno_name = {
                61: "connection_refused",
                60: "connection_timed_out",
                8: "dns_failure",
                -2: "dns_failure",
            }.get(getattr(reason, "errno", None))
            if errno_name:
                return errno_name
        reason_str = str(reason) if reason is not None else str(exc)
        if "timed out" in reason_str.lower():
            return "connection_timed_out"
        if "refused" in reason_str.lower():
            return "connection_refused"
        if "name or service not known" in reason_str.lower() or "nodename nor servname" in reason_str.lower():
            return "dns_failure"
        return "url_error"
    if isinstance(exc, TimeoutError):
        return "connection_timed_out"
    return type(exc).__name__


def fetch_one(url: str, timeout_s: float = 15.0) -> dict:
    """Bare, logged-out GET: no cookies, no auth headers, no opener reuse. Returns a partial row
    dict WITHOUT tool/passId/ts/rowHmac (the caller fills those in)."""
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"User-Agent": "anicca-reality-gate-public-artifact-snapshot/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 (deliberate: public HTTP fetch)
            body = resp.read(MAX_EXCERPT_CHARS * 8)
            final_url = resp.geturl()
            status = resp.status if hasattr(resp, "status") else resp.getcode()
    except urllib.error.HTTPError as e:
        # A genuine, server-returned non-2xx status IS a real HTTP response — never a network
        # error sentinel. Record it accurately (REQ-012: server_confirmed_absent territory).
        body = e.read() if hasattr(e, "read") else b""
        final_url = e.geturl() if hasattr(e, "geturl") else url
        status = e.code
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {
            "requestedUrl": url,
            "finalUrl": None,
            "httpStatus": None,
            "domExcerpt": "",
            "contentHash": None,
            "networkError": classify_network_error(e),
        }

    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001 — never crash the capture on a decode edge case
        text = ""
    excerpt = text.strip()[:MAX_EXCERPT_CHARS]
    content_hash = hashlib.sha256(body).hexdigest() if body else None

    return {
        "requestedUrl": url,
        "finalUrl": final_url,
        "httpStatus": status,
        "domExcerpt": excerpt,
        "contentHash": content_hash,
    }


def capture_and_sign(pass_id: str, urls: list[str], secret: str) -> list[dict]:
    rows = []
    for url in urls:
        partial = fetch_one(url)
        row = {
            "tool": TOOL_NAME,
            "passId": pass_id,
            "ts": int(time.time() * 1000),
            **partial,
        }
        row["rowHmac"] = compute_row_hmac(secret, row)
        rows.append(row)
    return rows


def create_trail_dir_exclusive(trail_dir: str) -> None:
    """REQ-012/PROP-048: exclusive create — fails (does not reuse) if the directory already
    exists. A pre-existing directory at a path this run was about to claim is not this tool's
    to silently accept."""
    os.mkdir(trail_dir)  # no `-p`: raises FileExistsError if it already exists (deliberate)


def append_rows(trail_dir: str, rows: list[dict]) -> str:
    path = os.path.join(trail_dir, "artifacts.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False))
            f.write("\n")
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Deterministic logged-out public-artifact capture tool.")
    parser.add_argument("--pass-id", required=True, help='pass id, or "-" to generate a fresh CSPRNG one')
    parser.add_argument("--trail-dir", required=True, help="directory to exclusively create and write artifacts.jsonl into")
    parser.add_argument("urls", nargs="+", help="one or more URLs to capture")
    args = parser.parse_args(argv)

    secret = sys.stdin.read().rstrip("\n")
    if not secret:
        print("public_artifact_snapshot.py: refusing to run with an empty HMAC secret (read from stdin)", file=sys.stderr)
        return 1

    pass_id = generate_pass_id() if args.pass_id == "-" else args.pass_id

    try:
        create_trail_dir_exclusive(args.trail_dir)
    except FileExistsError:
        print(
            f"public_artifact_snapshot.py: trail dir already exists: {args.trail_dir} "
            "(refusing to reuse or append — this is a pre-existing directory at a path this run "
            "claimed, not a collision to silently tolerate)",
            file=sys.stderr,
        )
        return 2

    rows = capture_and_sign(pass_id, args.urls, secret)
    path = append_rows(args.trail_dir, rows)
    print(json.dumps({"passId": pass_id, "trailPath": path, "rowsWritten": len(rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
