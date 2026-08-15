#!/usr/bin/env python3
"""Keep the job posting we applied to, and put it in the project we won.

``application_snapshot.py`` reads every posting's ``visible_text`` into a per-pass
evidence file, and nothing ever copies it into the project. Order 91000002, 2026-08-07:
the posting said 枚数 4枚, gave four 希望イメージ sliders and a 納品ファイル形式, and the
builder -- which only ever sees the talkroom -- rebuilt the deck at a size nobody had
asked for. The posting is the only place the buyer wrote the spec down before paying.

Two writes and one copy:

* ``harvest`` takes the pass's ``application-snapshot.json`` and stores every posting
  body it contains, keyed by request id, in a durable store outside the evidence tree.
  This runs at application time, when the project directory does not exist yet.
* ``install`` copies a stored posting into ``<project>/source/posting/`` once the order
  is won and the project directory exists.
* ``backfill`` recovers a posting whose pass evidence has already been garbage-collected,
  from the public request page. No authentication is involved: the page is public.

The store is content-addressed on the body, so re-harvesting the same posting rewrites
nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_STORE = Path(os.environ.get("GIG_POSTING_STORE") or (Path.home() / "gig" / "postings"))
DEFAULT_PROJECTS = Path(os.environ.get("GIG_PROJECTS_ROOT") or (Path.home() / "gig" / "projects"))
REQUEST_ID = re.compile(r"^[0-9]{1,32}$")
REQUEST_URL = "https://coconala.com/requests/{request_id}"
# Everything from here down is the applicant roster: other sellers' display names and
# profile links. It is not the spec, and it changes on every view, so it is cut before
# the body is hashed.
APPLICANT_MARKERS = ("応募者一覧", "募集内容についての質問")
MAX_BODY_BYTES = 256 * 1024


class PostingError(ValueError):
    """The posting could not be stored in a form a builder can trust."""


def canonical_request_id(value: Any) -> str:
    text = str(value or "").strip()
    if not REQUEST_ID.fullmatch(text):
        raise PostingError(f"invalid_request_id:{text[:32]}")
    return text


def normalize_body(value: Any) -> str:
    """Trim trailing space and collapse blank runs, without reflowing the text."""
    lines = [line.rstrip() for line in str(value or "").replace("\r\n", "\n").split("\n")]
    output: list[str] = []
    for line in lines:
        if not line and output and not output[-1]:
            continue
        output.append(line)
    return "\n".join(output).strip()


def strip_applicant_roster(markdown: str) -> str:
    """Cut a fetched page down to the posting itself.

    Two ends. The tail is the applicant roster: other sellers' names and profile links,
    different on every view and not part of the spec. The head is the site breadcrumb,
    which is only recognised as a head when the page really does have a title heading --
    a DOM ``visible_text`` body has no headings and must pass through untouched.
    """
    text = str(markdown or "")
    cut = len(text)
    for marker in APPLICANT_MARKERS:
        found = text.find(marker)
        if found != -1:
            cut = min(cut, found)
    body = text[:cut]
    lines = body.split("\n")
    for index, line in enumerate(lines[:20]):
        if line.startswith("# "):
            body = "\n".join(lines[index:])
            break
    return normalize_body(body)


def posting_document(
    *, request_id: str, title: str, url: str, body: str, observed_at: str, source: str,
    category: str | None = None,
) -> dict[str, Any]:
    identity = canonical_request_id(request_id)
    text = normalize_body(body)
    if not text:
        raise PostingError("empty_posting_body")
    encoded = text.encode("utf-8")
    if len(encoded) > MAX_BODY_BYTES:
        raise PostingError(f"posting_body_too_large:{len(encoded)}")
    return {
        "version": 1,
        "request_id": identity,
        "title": str(title or "").strip()[:300],
        "category": str(category).strip()[:100] if category else None,
        "url": str(url or REQUEST_URL.format(request_id=identity)).strip()[:300],
        "observed_at": str(observed_at or "").strip(),
        "source": str(source or "").strip(),
        "body_sha256": hashlib.sha256(encoded).hexdigest(),
        "body_bytes": len(encoded),
        "body": text,
    }


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def posting_path(root: Path, request_id: str) -> Path:
    return Path(root).expanduser() / f"request-{canonical_request_id(request_id)}.json"


def store_posting(store_root: Path, document: dict[str, Any]) -> dict[str, Any]:
    """Write one posting into the durable store; unchanged bodies are left alone."""
    path = posting_path(store_root, document["request_id"])
    existing = _read_json(path)
    if existing.get("body_sha256") == document["body_sha256"]:
        return {"request_id": document["request_id"], "path": str(path), "written": False}
    atomic_json(path, document)
    return {"request_id": document["request_id"], "path": str(path), "written": True}


def install_posting(
    store_root: Path, project_root: Path, request_id: str,
) -> dict[str, Any] | None:
    """Copy a stored posting into the project. ``None`` when there is nothing to copy."""
    identity = canonical_request_id(request_id)
    source = posting_path(store_root, identity)
    document = _read_json(source)
    if not document.get("body"):
        return None
    root = Path(project_root).expanduser()
    if not root.is_dir():
        return None
    destination = root / "source" / "posting" / f"request-{identity}.json"
    existing = _read_json(destination)
    if existing.get("body_sha256") == document["body_sha256"]:
        return {"request_id": identity, "path": str(destination), "written": False}
    atomic_json(destination, document)
    return {"request_id": identity, "path": str(destination), "written": True}


def harvest_snapshot(
    snapshot: dict[str, Any], store_root: Path, *, only_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Store every posting body the application snapshot carries."""
    details = snapshot.get("request_details")
    if not isinstance(details, list):
        raise PostingError("snapshot_has_no_request_details")
    results: list[dict[str, Any]] = []
    observed_at = str(snapshot.get("observed_at") or "")
    for detail in details:
        if not isinstance(detail, dict):
            continue
        try:
            identity = canonical_request_id(detail.get("request_id"))
        except PostingError:
            continue
        if only_ids is not None and identity not in only_ids:
            continue
        try:
            document = posting_document(
                request_id=identity,
                title=detail.get("title") or "",
                category=detail.get("category"),
                url=detail.get("canonical_url") or "",
                body=detail.get("visible_text") or "",
                observed_at=str(detail.get("observed_at") or observed_at),
                source="application_snapshot",
            )
        except PostingError as error:
            results.append({"request_id": identity, "error": str(error)})
            continue
        results.append(store_posting(store_root, document))
    return results


def fetch_posting_markdown(request_id: str, *, timeout: int = 180) -> str:
    """Read the public request page. Public URL, no session, no browser lease."""
    url = REQUEST_URL.format(request_id=canonical_request_id(request_id))
    completed = subprocess.run(
        ["crwl", "crawl", url, "-o", "markdown"],
        stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout,
    )
    if completed.returncode != 0:
        raise PostingError(f"posting_fetch_failed:{completed.returncode}")
    body = strip_applicant_roster(completed.stdout)
    if not body:
        raise PostingError("posting_fetch_empty")
    return body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store-root", type=Path, default=DEFAULT_STORE)
    subparsers = parser.add_subparsers(dest="command", required=True)

    harvest = subparsers.add_parser("harvest", help="store postings from a pass snapshot")
    harvest.add_argument("--snapshot", required=True, type=Path)
    harvest.add_argument("--request-id", action="append", default=[])

    install = subparsers.add_parser("install", help="copy a stored posting into a project")
    install.add_argument("--request-id", required=True)
    install.add_argument("--project-root", type=Path)
    install.add_argument("--projects-root", type=Path, default=DEFAULT_PROJECTS)

    backfill = subparsers.add_parser("backfill", help="recover a posting from the public page")
    backfill.add_argument("--request-id", required=True)
    backfill.add_argument("--body-file", type=Path)
    backfill.add_argument("--title", default="")
    backfill.add_argument("--observed-at", default="")
    backfill.add_argument("--install", action="store_true")
    backfill.add_argument("--projects-root", type=Path, default=DEFAULT_PROJECTS)

    args = parser.parse_args(argv)
    if args.command == "harvest":
        snapshot = _read_json(args.snapshot)
        if not snapshot:
            raise SystemExit("application snapshot is missing or unreadable")
        rows = harvest_snapshot(
            snapshot, args.store_root,
            only_ids={canonical_request_id(value) for value in args.request_id} or None,
        )
        print(json.dumps({
            "ok": True,
            "stored": sum(1 for row in rows if row.get("written")),
            "unchanged": sum(1 for row in rows if row.get("written") is False),
            "errors": [row for row in rows if row.get("error")],
        }, ensure_ascii=False, separators=(",", ":")))
        return 0
    if args.command == "install":
        project_root = args.project_root or (
            Path(args.projects_root).expanduser() / canonical_request_id(args.request_id)
        )
        result = install_posting(args.store_root, project_root, args.request_id)
        print(json.dumps({"ok": result is not None, "result": result},
                         ensure_ascii=False, separators=(",", ":")))
        return 0 if result is not None else 1
    body = (
        args.body_file.read_text(encoding="utf-8")
        if args.body_file is not None
        else fetch_posting_markdown(args.request_id)
    )
    document = posting_document(
        request_id=args.request_id,
        title=args.title,
        url=REQUEST_URL.format(request_id=canonical_request_id(args.request_id)),
        body=strip_applicant_roster(body),
        observed_at=args.observed_at,
        source="public_request_page" if args.body_file is None else "operator_body_file",
    )
    stored = store_posting(args.store_root, document)
    installed = None
    if args.install:
        installed = install_posting(
            args.store_root,
            Path(args.projects_root).expanduser() / canonical_request_id(args.request_id),
            args.request_id,
        )
    print(json.dumps({"ok": True, "stored": stored, "installed": installed},
                     ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
