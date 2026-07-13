#!/usr/bin/env python3
"""ig_public_check.py — deterministic, LOGGED-OUT Instagram public-surface check (feature
reality-gate, growth-engine IG adapter, 2026-07-13 real-run-verified method).

Structurally incapable of authenticated access: a fresh `instagrapi.Client()` is constructed
per invocation, `.login(...)` is NEVER called, no session/cookie file is ever loaded or written
— every check goes through instagrapi's public (unauthenticated) code path.

This tool does NOT reimplement HMAC signing/canonicalization — it imports
`canonical_row_for_signing`/`compute_row_hmac`/`create_trail_dir_exclusive`/`classify_network_error`
from public_artifact_snapshot.py (same directory) so a row from either tool is signed and
verified identically (`reality-verdict-schema.mjs`'s `verifyRowHmac`, same secret convention:
read from STDIN only, never argv/env, never written under the trail directory).

Method (real-run-verified 2026-07-13, this is the ONLY method this tool uses — see docstring on
`check_ig_post` for why the tempting single-call `media_info(code)` shortcut is deliberately not
used):
  1. uid = client.user_id_from_username(<account>)              # logged-out
  2. codes = [m.code for m in client.user_medias_gql(uid, N)]    # logged-out, N=12 default —
     this IS the "fixed public surface" (mirrors REQ-015's fixed-surface concept: the account's
     own recent-media GraphQL page, not a caller-chosen URL).
  3. claimed post code in codes            -> PASS material  (post is publicly visible)
  4. surface fetched OK, code NOT in codes -> FAIL material   (a positive contradiction — the
     loop claimed a post that this deterministic surface does not show)
  5. surface itself raised/unreachable     -> CANNOT_VERIFY material (honest "could not read")

Usage:
  echo -n "<hmac-secret>" | python3 ig_public_check.py --pass-id <passId|-> \
      --trail-dir <dir> --account <username> --claimed-code <shortcode> [--sample-size 12]
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time

_SELF_DIR = os.path.dirname(os.path.abspath(__file__))
_PAS_PATH = os.path.join(_SELF_DIR, "public_artifact_snapshot.py")

_spec = importlib.util.spec_from_file_location("public_artifact_snapshot", _PAS_PATH)
_pas = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("public_artifact_snapshot", _pas)
_spec.loader.exec_module(_pas)

canonical_row_for_signing = _pas.canonical_row_for_signing
compute_row_hmac = _pas.compute_row_hmac
generate_pass_id = _pas.generate_pass_id
create_trail_dir_exclusive = _pas.create_trail_dir_exclusive
classify_network_error = _pas.classify_network_error

TOOL_NAME = "ig_public_check"
MAX_EXCERPT_CHARS = 2000
DEFAULT_SAMPLE_SIZE = 12


def _default_client_factory():
    from instagrapi import Client

    return Client()  # NEVER call .login(...) here — logged-out, structurally, by construction.


def check_ig_post(account: str, claimed_code: str, sample_size: int = DEFAULT_SAMPLE_SIZE, client_factory=None) -> dict:
    """Deliberately does NOT call the tempting single-call shortcut `client.media_info(code)`:
    that call raises the SAME exception class (e.g. LoginRequired) both when the post genuinely
    does not exist/is private AND when Instagram is merely rate-limiting this run — it cannot
    distinguish "the loop lied" from "we got throttled", so it cannot be used as FAIL evidence.
    The fixed-public-surface membership check below can: a rate limit or account-not-found
    failure surfaces while fetching the SURFACE itself (caught below, -> CANNOT_VERIFY), while a
    successfully-fetched surface that simply omits the claimed code is a real, structural
    contradiction (-> FAIL) — the same CONTRADICTION-vs-INCONCLUSIVE split this feature's
    provenance backstop (`validateArtifactProvenance`) uses everywhere else.
    Returns a partial row dict WITHOUT tool/passId/ts/rowHmac (caller fills those in)."""
    factory = client_factory or _default_client_factory
    surface_url = f"https://www.instagram.com/{account}/"

    try:
        client = factory()
        uid = client.user_id_from_username(account)
        medias = client.user_medias_gql(uid, sample_size)
        codes = [m.code for m in medias]
    except Exception as e:  # noqa: BLE001 — any exception fetching the surface itself -> CANNOT_VERIFY
        return {
            "requestedUrl": surface_url,
            "finalUrl": None,
            "httpStatus": None,
            "account": account,
            "claimedCode": claimed_code,
            "surfaceCodes": None,
            "found": None,
            "verdictMaterial": "cannot_verify",
            "domExcerpt": "",
            "contentHash": None,
            "networkError": classify_network_error(e),
        }

    found = claimed_code in codes
    excerpt = f"codes={codes}"[:MAX_EXCERPT_CHARS]
    content_hash = hashlib.sha256(json.dumps(codes, sort_keys=True).encode("utf-8")).hexdigest()

    return {
        "requestedUrl": surface_url,
        "finalUrl": surface_url,
        "httpStatus": 200,
        "account": account,
        "claimedCode": claimed_code,
        "surfaceCodes": codes,
        "found": found,
        "verdictMaterial": "pass" if found else "fail",
        "domExcerpt": excerpt,
        "contentHash": content_hash,
    }


def capture_and_sign(pass_id: str, account: str, claimed_code: str, sample_size: int, secret: str, client_factory=None) -> dict:
    partial = check_ig_post(account, claimed_code, sample_size, client_factory=client_factory)
    row = {
        "tool": TOOL_NAME,
        "passId": pass_id,
        "ts": int(time.time() * 1000),
        **partial,
    }
    row["rowHmac"] = compute_row_hmac(secret, row)
    return row


def append_row(trail_dir: str, row: dict) -> str:
    path = os.path.join(trail_dir, "artifacts.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False))
        f.write("\n")
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Deterministic logged-out Instagram public-surface check.")
    parser.add_argument("--pass-id", required=True, help='pass id, or "-" to generate a fresh CSPRNG one')
    parser.add_argument("--trail-dir", required=True, help="directory to exclusively create and write artifacts.jsonl into")
    parser.add_argument("--account", required=True, help="Instagram username to check (public profile)")
    parser.add_argument("--claimed-code", required=True, help="the post shortcode the loop claims it published")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE, help="how many recent public medias define the fixed surface (default 12)")
    args = parser.parse_args(argv)

    secret = sys.stdin.read().rstrip("\n")
    if not secret:
        print("ig_public_check.py: refusing to run with an empty HMAC secret (read from stdin)", file=sys.stderr)
        return 1

    pass_id = generate_pass_id() if args.pass_id == "-" else args.pass_id

    try:
        create_trail_dir_exclusive(args.trail_dir)
    except FileExistsError:
        print(
            f"ig_public_check.py: trail dir already exists: {args.trail_dir} "
            "(refusing to reuse or append — a pre-existing directory at a path this run "
            "claimed is not a collision to silently tolerate)",
            file=sys.stderr,
        )
        return 2

    row = capture_and_sign(pass_id, args.account, args.claimed_code, args.sample_size, secret)
    path = append_row(args.trail_dir, row)
    print(json.dumps({
        "passId": pass_id,
        "trailPath": path,
        "verdictMaterial": row["verdictMaterial"],
        "found": row["found"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
