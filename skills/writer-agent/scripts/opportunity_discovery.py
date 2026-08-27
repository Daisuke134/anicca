#!/usr/bin/env python3
"""Discover new paid-writing programs from indexes, then verify official pages."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import sqlite3
import sys
import tempfile
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from claim_store import _timestamp, canonicalize_url  # noqa: E402
from opportunity_pitch import model_choose, run_pitch_prep  # noqa: E402
from opportunity_store import OpportunityStore  # noqa: E402
from opportunity_watch import fetch_official, model_review, run_watch  # noqa: E402


class CandidateUnavailable(RuntimeError):
    pass


def _public_https_candidate(value: str) -> bool:
    """Reject index-controlled targets that can address the local machine/network."""
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower().rstrip(".")
        port = parsed.port
    except ValueError:
        return False
    if parsed.scheme.lower() != "https" or not host or port not in (None, 443):
        return False
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return address.is_global


def _money(text: str) -> tuple[float | None, float | None, str | None]:
    values = [float(value.replace(",", "")) for value in re.findall(r"\$([0-9][0-9,]*(?:\.\d+)?)", text)]
    if not values:
        return None, None, None
    lowered = text.lower()
    if len(values) >= 2:
        return min(values), max(values), "USD"
    if any(token in lowered for token in ("up to", "upto")):
        return None, values[0], "USD"
    if any(token in lowered for token in ("from ", "over ", "+")):
        return values[0], None, "USD"
    return values[0], values[0], "USD"


def parse_index(payload: bytes) -> list[dict[str, Any]]:
    text = payload.decode("utf-8", errors="replace")
    lines = text.splitlines()
    in_opportunities = False
    raw: list[dict[str, Any]] = []
    for index, line in enumerate(lines):
        if re.match(r"^##\s+Writing Opportunities\s*$", line, re.I):
            in_opportunities = True
            continue
        if in_opportunities and line.startswith("## "):
            break
        if not in_opportunities:
            continue
        match = re.match(r"^\[([^]]+)]\((https://[^)]+)\)\s*-\s*(.+?)\s*$", line)
        if match is None:
            continue
        publisher, url, compensation = match.groups()
        if not _public_https_candidate(url):
            continue
        try:
            canonical_url = canonicalize_url(url, "rss")
        except ValueError:
            continue
        description = ""
        if index + 1 < len(lines) and lines[index + 1].lstrip().startswith(">"):
            description = lines[index + 1].lstrip()[1:].strip()
        fee_min, fee_max, currency = _money(compensation)
        raw.append(
            {
                "publisher": " ".join(publisher.split()),
                "official_program_url": canonical_url,
                "index_compensation": " ".join(compensation.split()),
                "index_description": " ".join(description.split()),
                "claimed_fee_min": fee_min,
                "claimed_fee_max": fee_max,
                "claimed_currency": currency,
                "evidence_status": "discovery index only; not official evidence",
                "index_position": len(raw),
            }
        )
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw:
        if item["official_program_url"] in seen:
            continue
        seen.add(item["official_program_url"])
        unique.append(item)
    return unique


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    return connection


def _initialize(path: Path) -> None:
    OpportunityStore(path)
    with _connect(path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS opportunity_candidates (
                candidate_id TEXT PRIMARY KEY,
                official_program_url TEXT NOT NULL UNIQUE,
                publisher TEXT NOT NULL,
                index_compensation TEXT NOT NULL,
                index_description TEXT NOT NULL,
                claimed_fee_min REAL,
                claimed_fee_max REAL,
                claimed_currency TEXT,
                index_position INTEGER NOT NULL,
                source_url TEXT NOT NULL,
                source_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                first_seen_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                last_attempt_at TEXT,
                opportunity_id TEXT,
                reason TEXT NOT NULL DEFAULT ''
            )
            """
        )


def _atomic_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def select_due_rechecks(
    database: Path | str, *, observed_at: str, budget: int,
    cadence_days: dict[str, int],
) -> list[dict[str, Any]]:
    if budget < 1:
        raise ValueError("recheck budget must be positive")
    now_text = str(_timestamp(observed_at, "observed_at"))
    now = datetime.fromisoformat(now_text.replace("Z", "+00:00"))
    normalized_cadence: dict[str, int] = {}
    for state, days in cadence_days.items():
        if not isinstance(state, str) or not isinstance(days, int) or isinstance(days, bool) or days < 1:
            raise ValueError("recheck cadence must map states to positive integer days")
        normalized_cadence[state] = days
    if not normalized_cadence:
        return []
    _initialize(Path(database))
    placeholders = ",".join("?" for _ in normalized_cadence)
    with _connect(Path(database)) as connection:
        rows = connection.execute(
            f"SELECT opportunity_id,publisher,official_program_url,application_url,"
            f"supporting_urls_json,state,"
            f"last_verified_at FROM opportunities WHERE state IN ({placeholders})",
            tuple(normalized_cadence),
        ).fetchall()
    due: list[tuple[datetime, dict[str, Any]]] = []
    for raw in rows:
        row = dict(raw)
        row["supporting_urls"] = json.loads(row.pop("supporting_urls_json"))
        verified = datetime.fromisoformat(str(row["last_verified_at"]).replace("Z", "+00:00"))
        due_at = verified + timedelta(days=normalized_cadence[str(row["state"])])
        if due_at > now:
            continue
        row["candidate_id"] = row["opportunity_id"]
        due.append((due_at, row))
    due.sort(key=lambda item: (item[0], item[1]["opportunity_id"]))
    return [row for _due_at, row in due[:budget]]


def run_due_rechecks(
    candidates: list[dict[str, Any]], receipt_path: Path | str, *,
    observed_at: str, verifier: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    observed_at = str(_timestamp(observed_at, "observed_at"))
    attempts: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            result = verifier(candidate)
            if result.get("status") != "OK" or not result.get("opportunity_id"):
                raise CandidateUnavailable(
                    str(result.get("reason") or result.get("status") or "verification failed")
                )
            status = "VERIFIED"
            reason = f"official page reverified as {result.get('state', 'UNKNOWN')}"
            state = str(result.get("state") or "UNKNOWN")
        except CandidateUnavailable as error:
            status = "UNAVAILABLE"
            reason = str(error)
            state = None
        attempts.append(
            {
                "opportunity_id": candidate["opportunity_id"],
                "publisher": candidate["publisher"],
                "official_program_url": candidate["official_program_url"],
                "status": status,
                "state": state,
                "reason": reason,
            }
        )
    verified = sum(item["status"] == "VERIFIED" for item in attempts)
    receipt = {
        "version": 1,
        "observed_at": observed_at,
        "attempts": attempts,
        "totals": {
            "due": len(candidates), "attempted": len(attempts), "verified": verified,
            "unavailable": len(attempts) - verified,
        },
    }
    _atomic_json(Path(receipt_path), receipt)
    return receipt


def run_discovery(
    index_payload: bytes,
    database: Path | str,
    receipt_path: Path | str,
    *,
    source_url: str,
    observed_at: str,
    budget: int,
    verifier: Callable[[dict[str, Any]], dict[str, Any]],
    max_attempts: int = 3,
    retry_hours: int = 24,
) -> dict[str, Any]:
    if budget < 1:
        raise ValueError("budget must be positive")
    if max_attempts < 1:
        raise ValueError("max_attempts must be positive")
    if retry_hours < 1:
        raise ValueError("retry_hours must be positive")
    observed_at = str(_timestamp(observed_at, "observed_at"))
    source_url = canonicalize_url(source_url, "rss")
    source_sha256 = hashlib.sha256(index_payload).hexdigest()
    parsed = parse_index(index_payload)
    database = Path(database)
    _initialize(database)
    with _connect(database) as connection:
        connection.execute("BEGIN IMMEDIATE")
        for item in parsed:
            fingerprint = hashlib.sha256(item["official_program_url"].encode()).hexdigest()
            candidate_id = f"opc_{fingerprint[:24]}"
            connection.execute(
                """
                INSERT OR IGNORE INTO opportunity_candidates(
                    candidate_id,official_program_url,publisher,index_compensation,
                    index_description,claimed_fee_min,claimed_fee_max,claimed_currency,
                    index_position,source_url,source_sha256,status,first_seen_at,last_seen_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,'NEW',?,?)
                """,
                (
                    candidate_id, item["official_program_url"], item["publisher"],
                    item["index_compensation"], item["index_description"],
                    item["claimed_fee_min"], item["claimed_fee_max"], item["claimed_currency"],
                    item["index_position"], source_url, source_sha256, observed_at, observed_at,
                ),
            )
            connection.execute(
                "UPDATE opportunity_candidates SET last_seen_at=?,source_sha256=? WHERE candidate_id=?",
                (observed_at, source_sha256, candidate_id),
            )
        connection.execute(
            """
            UPDATE opportunity_candidates SET status='VERIFIED',opportunity_id=(
                SELECT opportunity_id FROM opportunities o
                WHERE o.official_program_url=opportunity_candidates.official_program_url
            ),reason='already present in official opportunity store'
            WHERE EXISTS(
                SELECT 1 FROM opportunities o
                WHERE o.official_program_url=opportunity_candidates.official_program_url
            )
            """
        )
        candidates = connection.execute(
            """
            SELECT * FROM opportunity_candidates
            WHERE status='NEW' OR (
                status='UNAVAILABLE' AND attempts < ? AND
                (last_attempt_at IS NULL OR
                 (julianday(?) - julianday(last_attempt_at)) * 24 >= ?)
            )
            ORDER BY COALESCE(claimed_fee_max,claimed_fee_min,-1) DESC,
                     attempts ASC,
                     index_position ASC,candidate_id ASC
            LIMIT ?
            """,
            (max_attempts, observed_at, retry_hours, budget),
        ).fetchall()
    attempts: list[dict[str, Any]] = []
    for candidate_row in candidates:
        candidate = dict(candidate_row)
        try:
            result = verifier(candidate)
            if result.get("status") != "OK" or not result.get("opportunity_id"):
                raise CandidateUnavailable(str(result.get("reason") or result.get("status") or "verification failed"))
            status = "VERIFIED"
            reason = f"official page verified as {result.get('state', 'UNKNOWN')}"
            opportunity_id = str(result["opportunity_id"])
        except CandidateUnavailable as error:
            status = (
                "EXHAUSTED"
                if int(candidate.get("attempts") or 0) + 1 >= max_attempts
                else "UNAVAILABLE"
            )
            reason = str(error)
            opportunity_id = None
        with _connect(database) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                "UPDATE opportunity_candidates SET status=?,attempts=attempts+1,last_attempt_at=?,"
                "opportunity_id=?,reason=? WHERE candidate_id=?",
                (status, observed_at, opportunity_id, reason, candidate["candidate_id"]),
            )
        attempts.append(
            {
                "candidate_id": candidate["candidate_id"],
                "publisher": candidate["publisher"],
                "official_program_url": candidate["official_program_url"],
                "status": status,
                "opportunity_id": opportunity_id,
                "reason": reason,
            }
        )
    verified = sum(item["status"] == "VERIFIED" for item in attempts)
    receipt = {
        "version": 1,
        "observed_at": observed_at,
        "source_url": source_url,
        "source_sha256": source_sha256,
        "attempts": attempts,
        "totals": {
            "parsed": len(parsed), "attempted": len(attempts), "verified": verified,
            "unavailable": len(attempts) - verified,
        },
    }
    _atomic_json(Path(receipt_path), receipt)
    return receipt


def fetch_index(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "Writer-Agent-Opportunity-Discovery/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            body = response.read(2 * 1024 * 1024 + 1)
    except OSError as error:
        raise CandidateUnavailable(type(error).__name__) from error
    if not body or len(body) > 2 * 1024 * 1024:
        raise CandidateUnavailable("index response empty or over byte cap")
    return body


def verify_candidate(
    candidate: dict[str, Any], *, database: Path, receipts: Path,
    runner: Path, observed_at: str,
) -> dict[str, Any]:
    source = {
        "id": candidate["candidate_id"],
        "publisher": candidate["publisher"],
        "official_program_url": candidate["official_program_url"],
        "application_url": candidate["official_program_url"],
        "supporting_urls": candidate.get("supporting_urls", []),
    }
    run_id = f"opportunity-candidate-{candidate['candidate_id']}-{observed_at.replace(':', '')}"
    try:
        receipt = run_watch(
            {"version": 1, "sources": [source]}, database,
            receipts / f"{candidate['candidate_id']}.json",
            observed_at=observed_at,
            fetcher=fetch_official,
            reviewer=lambda item, body: model_review(
                item, body, runner=runner, run_id=run_id
            ),
        )
    except Exception as error:
        raise CandidateUnavailable(type(error).__name__) from error
    return receipt["sources"][0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SCRIPT_DIR.parent / "config/opportunity-discovery.json")
    parser.add_argument("--db", type=Path, default=SCRIPT_DIR.parent / "state/opportunities.sqlite3")
    parser.add_argument("--claims-db", type=Path, default=SCRIPT_DIR.parent / "state/claims.sqlite3")
    parser.add_argument("--receipt", type=Path, default=SCRIPT_DIR.parent / "state/opportunity-discovery-latest.json")
    parser.add_argument("--runner", type=Path, default=SCRIPT_DIR.parent / "runtime/shared-model-runner.py")
    parser.add_argument(
        "--observed-at", default=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    args = parser.parse_args(argv)
    observed_at = args.observed_at() if callable(args.observed_at) else args.observed_at
    config = json.loads(args.config.read_text(encoding="utf-8"))
    state = args.db.parent
    state.mkdir(parents=True, exist_ok=True)
    with (state / ".opportunity-discovery.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"status": "LOCK_BUSY", "observed_at": observed_at}))
            return 0
        recheck_candidates = select_due_rechecks(
            args.db,
            observed_at=observed_at,
            budget=int(config.get("recheck_budget", 5)),
            cadence_days=dict(config.get("recheck_cadence_days", {})),
        )
        rechecks = run_due_rechecks(
            recheck_candidates,
            state / "opportunity-recheck-latest.json",
            observed_at=observed_at,
            verifier=lambda row: verify_candidate(
                row, database=args.db,
                receipts=state / "opportunity-verifications",
                runner=args.runner, observed_at=observed_at,
            ),
        )
        index_payload = fetch_index(config["index_url"])
        discovery = run_discovery(
            index_payload, args.db, args.receipt,
            source_url=config["index_url"], observed_at=observed_at,
            budget=int(config.get("verification_budget", 5)),
            max_attempts=int(config.get("candidate_max_attempts", 3)),
            retry_hours=int(config.get("candidate_retry_hours", 24)),
            verifier=lambda row: verify_candidate(
                row, database=args.db,
                receipts=state / "opportunity-verifications",
                runner=args.runner, observed_at=observed_at,
            ),
        )
        pitches = run_pitch_prep(
            args.db, args.claims_db,
            state / "opportunity-pitch-latest.json",
            observed_at=observed_at,
            budget=int(config.get("pitch_budget", 2)),
            chooser=lambda opportunity, claims: model_choose(
                opportunity, claims, runner=args.runner,
                run_id=f"opportunity-pitch-{observed_at.replace(':', '')}",
            ),
        )
        receipt = {
            "version": 1, "observed_at": observed_at,
            "rechecks": rechecks, "discovery": discovery, "pitches": pitches,
        }
        _atomic_json(state / "opportunity-loop-latest.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
