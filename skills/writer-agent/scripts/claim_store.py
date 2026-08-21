#!/usr/bin/env python3
"""Durable, receipted claims discovered by Writer Agent collectors.

Collectors and models may propose claim records.  This module owns only the
mechanical boundary: schema validation, URL normalization, deduplication,
observation receipts, and one-time topic consumption.  It deliberately does
not decide whether a subject is in a preferred niche.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


SOURCE_KINDS = frozenset({"x", "github", "rss"})
SOURCE_FAMILIES = frozenset(
    {"paid_market", "reader_demand", "publisher_opportunity", "owned_funnel"}
)
TRACKING_QUERY_KEYS = frozenset(
    {"fbclid", "gclid", "mc_cid", "mc_eid", "ref", "ref_src", "source"}
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PERCENT_ESCAPE_RE = re.compile(r"%([0-9A-Fa-f]{2})")
UNRESERVED_URL_BYTES = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~"
)


def _decode_unreserved_url_escapes(value: str) -> str:
    """Normalize RFC 3986 unreserved percent escapes without changing delimiters."""

    def replace(match: re.Match[str]) -> str:
        character = chr(int(match.group(1), 16))
        return character if character in UNRESERVED_URL_BYTES else match.group(0)

    return PERCENT_ESCAPE_RE.sub(replace, value)


def _remove_dot_segments(path: str) -> str:
    """Apply RFC 3986 dot-segment removal to an already decoded path."""

    absolute = path.startswith("/")
    trailing = path.endswith(("/", "/.", "/.."))
    segments: list[str] = []
    for segment in path.split("/"):
        if segment in {"", "."}:
            continue
        if segment == "..":
            if segments:
                segments.pop()
            continue
        segments.append(segment)
    normalized = "/".join(segments)
    if absolute:
        normalized = "/" + normalized
    if not normalized and absolute:
        normalized = "/"
    if trailing and normalized not in {"", "/"}:
        normalized += "/"
    return normalized


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return unicodedata.normalize("NFKC", " ".join(value.split()))


def _timestamp(value: Any, field: str, *, optional: bool = False) -> str | None:
    if optional and (value is None or value == ""):
        return None
    normalized = _text(value, field)
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone")
    return normalized


def canonicalize_url(value: Any, source_kind: str) -> str:
    raw = _text(value, "url")
    parsed = urlsplit(raw)
    if parsed.scheme.lower() != "https":
        raise ValueError("claim URL must use HTTPS")
    if parsed.username or parsed.password or not parsed.hostname:
        raise ValueError("claim URL authority is invalid")
    host = _decode_unreserved_url_escapes(parsed.hostname.lower().rstrip("."))
    if "%" in host:
        raise ValueError("claim URL host contains an invalid escape")
    if source_kind == "x":
        if host not in {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}:
            raise ValueError("X source URL must use x.com or twitter.com")
        host = "x.com"
    elif source_kind == "github":
        if host not in {"github.com", "www.github.com", "api.github.com"}:
            raise ValueError("GitHub source URL must use github.com")
        host = "github.com" if host == "www.github.com" else host
    port = parsed.port
    netloc = host if port in (None, 443) else f"{host}:{port}"
    path = _decode_unreserved_url_escapes(parsed.path or "/")
    path = re.sub(r"/{2,}", "/", path)
    path = _remove_dot_segments(path)
    if path != "/":
        path = path.rstrip("/")
    query = urlencode(
        sorted(
            (key, item)
            for key, item in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in TRACKING_QUERY_KEYS
        ),
        doseq=True,
    )
    return urlunsplit(("https", netloc, path, query, ""))


def _fingerprint(canonical_url: str, claim: str) -> str:
    normalized_claim = unicodedata.normalize("NFKC", " ".join(claim.split())).casefold()
    return hashlib.sha256(f"{canonical_url}\n{normalized_claim}".encode("utf-8")).hexdigest()


class ClaimStore:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL UNIQUE,
                    source_kind TEXT NOT NULL CHECK(source_kind IN ('x','github','rss')),
                    source_name TEXT NOT NULL,
                    canonical_url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    claim TEXT NOT NULL,
                    evidence_excerpt TEXT NOT NULL,
                    reader_job TEXT NOT NULL,
                    published_at TEXT,
                    first_observed_at TEXT NOT NULL,
                    first_retrieved_sha256 TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS claims_source_url
                    ON claims(source_kind, canonical_url);
                CREATE TABLE IF NOT EXISTS claim_observations (
                    claim_id TEXT NOT NULL REFERENCES claims(claim_id),
                    observed_at TEXT NOT NULL,
                    retrieved_sha256 TEXT NOT NULL,
                    PRIMARY KEY(claim_id, observed_at, retrieved_sha256)
                );
                CREATE TABLE IF NOT EXISTS claim_consumptions (
                    claim_id TEXT PRIMARY KEY REFERENCES claims(claim_id),
                    topic_card TEXT NOT NULL,
                    topic_card_sha256 TEXT NOT NULL,
                    consumed_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS claim_rejections (
                    claim_id TEXT PRIMARY KEY REFERENCES claims(claim_id),
                    reason TEXT NOT NULL,
                    rejected_at TEXT NOT NULL
                );
                """
            )
            existing_columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(claims)").fetchall()
            }
            for column, definition in (
                ("source_family", "TEXT"),
                ("full_body", "TEXT"),
                ("source_sha256", "TEXT"),
                ("capture_method", "TEXT"),
            ):
                if column not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE claims ADD COLUMN {column} {definition}"
                    )

    def ingest(self, candidate: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(candidate, dict):
            raise ValueError("claim candidate must be an object")
        source_kind = _text(candidate.get("source_kind"), "source_kind").lower()
        if source_kind not in SOURCE_KINDS:
            raise ValueError("source_kind must be x, github, or rss")
        source_name = _text(candidate.get("source_name"), "source_name")
        canonical_url = canonicalize_url(candidate.get("url"), source_kind)
        title = _text(candidate.get("title"), "title")
        claim = _text(candidate.get("claim"), "claim")
        evidence_excerpt = _text(candidate.get("evidence_excerpt"), "evidence_excerpt")
        reader_job = _text(candidate.get("reader_job"), "reader_job")
        published_at = _timestamp(candidate.get("published_at"), "published_at", optional=True)
        observed_at = _timestamp(candidate.get("observed_at"), "observed_at")
        retrieved_sha256 = _text(candidate.get("retrieved_sha256"), "retrieved_sha256").lower()
        if SHA256_RE.fullmatch(retrieved_sha256) is None:
            raise ValueError("retrieved_sha256 must be a lowercase SHA-256 digest")
        source_family = candidate.get("source_family")
        if source_family not in (None, ""):
            source_family = _text(source_family, "source_family")
            if source_family not in SOURCE_FAMILIES:
                raise ValueError("source_family is unsupported")
        else:
            source_family = None
        full_body = candidate.get("full_body")
        source_sha256 = candidate.get("source_sha256")
        capture_method = candidate.get("capture_method")
        if full_body not in (None, ""):
            if not isinstance(full_body, str) or not full_body.strip():
                raise ValueError("full_body must be a non-empty string")
            if not isinstance(source_sha256, str):
                raise ValueError("full_body requires source_sha256")
            source_sha256 = source_sha256.lower()
            if SHA256_RE.fullmatch(source_sha256) is None:
                raise ValueError("source_sha256 must be a lowercase SHA-256 digest")
            if hashlib.sha256(full_body.encode("utf-8")).hexdigest() != source_sha256:
                raise ValueError("source_sha256 does not match full_body")
            if not isinstance(capture_method, str) or not capture_method.strip():
                raise ValueError("full_body requires capture_method")
            capture_method = _text(capture_method, "capture_method")
        else:
            full_body = None
            if source_sha256 not in (None, ""):
                source_sha256 = _text(source_sha256, "source_sha256").lower()
                if SHA256_RE.fullmatch(source_sha256) is None:
                    raise ValueError("source_sha256 must be a lowercase SHA-256 digest")
            else:
                source_sha256 = None
            if capture_method not in (None, ""):
                capture_method = _text(capture_method, "capture_method")
        fingerprint = _fingerprint(canonical_url, claim)
        claim_id = f"clm_{fingerprint[:24]}"

        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            inserted = connection.execute(
                """
                INSERT OR IGNORE INTO claims(
                    claim_id,fingerprint,source_kind,source_name,canonical_url,title,claim,
                    evidence_excerpt,reader_job,published_at,first_observed_at,
                    first_retrieved_sha256,created_at,source_family,full_body,
                    source_sha256,capture_method
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    claim_id, fingerprint, source_kind, source_name, canonical_url, title, claim,
                    evidence_excerpt, reader_job, published_at, observed_at,
                    retrieved_sha256, observed_at, source_family, full_body,
                    source_sha256, capture_method,
                ),
            ).rowcount == 1
            row = connection.execute(
                "SELECT claim_id FROM claims WHERE fingerprint=?", (fingerprint,)
            ).fetchone()
            if row is None:  # pragma: no cover - guarded by transaction and schema
                raise RuntimeError("claim insert did not produce a durable row")
            durable_id = str(row["claim_id"])
            connection.execute(
                "INSERT OR IGNORE INTO claim_observations(claim_id,observed_at,retrieved_sha256) "
                "VALUES(?,?,?)",
                (durable_id, observed_at, retrieved_sha256),
            )
        return {"claim_id": durable_id, "inserted": inserted}

    def get(self, claim_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT c.*,COUNT(o.observed_at) AS observation_count,
                       rejected.reason AS rejection_reason,
                       rejected.rejected_at AS rejected_at
                FROM claims c LEFT JOIN claim_observations o USING(claim_id)
                LEFT JOIN claim_rejections rejected USING(claim_id)
                WHERE c.claim_id=? GROUP BY c.claim_id
                """,
                (claim_id,),
            ).fetchone()
        if row is None:
            raise KeyError(claim_id)
        return dict(row)

    def list_unconsumed(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT c.* FROM claims c
                LEFT JOIN claim_consumptions used USING(claim_id)
                LEFT JOIN claim_rejections rejected USING(claim_id)
                WHERE used.claim_id IS NULL AND rejected.claim_id IS NULL
                ORDER BY c.first_observed_at DESC,c.claim_id ASC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def reject(self, claim_id: str, *, reason: str, rejected_at: str) -> None:
        claim_id = _text(claim_id, "claim_id")
        reason = _text(reason, "reason")
        rejected_at = str(_timestamp(rejected_at, "rejected_at"))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            if connection.execute(
                "SELECT 1 FROM claims WHERE claim_id=?", (claim_id,)
            ).fetchone() is None:
                raise KeyError(claim_id)
            prior = connection.execute(
                "SELECT reason,rejected_at FROM claim_rejections WHERE claim_id=?", (claim_id,)
            ).fetchone()
            intended = (reason, rejected_at)
            if prior is not None:
                if tuple(prior) != intended:
                    raise ValueError("claim already has a different rejection receipt")
                return
            connection.execute(
                "INSERT INTO claim_rejections(claim_id,reason,rejected_at) VALUES(?,?,?)",
                (claim_id, reason, rejected_at),
            )

    def consume(
        self, claim_id: str, *, topic_card: str, topic_card_sha256: str, consumed_at: str
    ) -> None:
        topic_card = _text(topic_card, "topic_card")
        if Path(topic_card).name != topic_card or not topic_card.endswith(".md"):
            raise ValueError("topic_card must be a Markdown basename")
        topic_card_sha256 = _text(topic_card_sha256, "topic_card_sha256").lower()
        if SHA256_RE.fullmatch(topic_card_sha256) is None:
            raise ValueError("topic_card_sha256 must be a lowercase SHA-256 digest")
        normalized_time = _timestamp(consumed_at, "consumed_at")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            exists = connection.execute(
                "SELECT 1 FROM claims WHERE claim_id=?", (claim_id,)
            ).fetchone()
            if exists is None:
                raise KeyError(claim_id)
            prior = connection.execute(
                "SELECT topic_card,topic_card_sha256,consumed_at FROM claim_consumptions "
                "WHERE claim_id=?",
                (claim_id,),
            ).fetchone()
            intended = (topic_card, topic_card_sha256, normalized_time)
            if prior is not None:
                if tuple(prior) != intended:
                    raise ValueError("claim already has a different consumption receipt")
                return
            connection.execute(
                "INSERT INTO claim_consumptions(claim_id,topic_card,topic_card_sha256,consumed_at) "
                "VALUES(?,?,?,?)",
                (claim_id, topic_card, topic_card_sha256, normalized_time),
            )


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid JSON on line {number}") from error
            if not isinstance(value, dict):
                raise ValueError(f"line {number} is not a JSON object")
            yield value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)
    ingest = subparsers.add_parser("ingest")
    ingest.add_argument("--input", type=Path, required=True)
    listing = subparsers.add_parser("list-unconsumed")
    listing.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    store = ClaimStore(args.db)
    if args.command == "ingest":
        for candidate in _read_jsonl(args.input):
            print(json.dumps(store.ingest(candidate), ensure_ascii=False, sort_keys=True))
    elif args.command == "list-unconsumed":
        for item in store.list_unconsumed(limit=args.limit):
            print(json.dumps(item, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
