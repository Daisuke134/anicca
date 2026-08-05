from __future__ import annotations

import argparse
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .state import canonical_url


class TerminalResultError(RuntimeError):
    pass


class CandidateQueue:
    def __init__(self, database: Path):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.connection = sqlite3.connect(self.database)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS candidate_links (
                canonical_url TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                query_family TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('discovered', 'eligible', 'rejected')),
                reason TEXT,
                discovered_at TEXT NOT NULL,
                verified_at TEXT
            )
            """
        )
        self.connection.commit()
        os.chmod(self.database, 0o600)

    def close(self) -> None:
        self.connection.close()

    def discover(self, links: Iterable[dict[str, Any]]) -> dict[str, int]:
        inserted = 0
        observed = 0
        now = datetime.now(timezone.utc).isoformat()
        for link in links:
            if not isinstance(link, dict):
                raise ValueError("candidate link must be an object")
            url = canonical_url(str(link.get("url", "")).strip())
            source = str(link.get("source", "")).strip()
            query_family = str(link.get("query_family", "")).strip()
            if not url or not source or not query_family:
                raise ValueError("candidate link requires url, source, and query_family")
            observed += 1
            cursor = self.connection.execute(
                """
                INSERT OR IGNORE INTO candidate_links (
                    canonical_url, source, query_family, status, discovered_at
                ) VALUES (?, ?, ?, 'discovered', ?)
                """,
                (url, source, query_family, now),
            )
            inserted += cursor.rowcount
        self.connection.commit()
        return {"observed_count": observed, "inserted_count": inserted}

    def mark_verified(self, url: str, *, eligible: bool, reason: str) -> None:
        normalized = canonical_url(url)
        reason = reason.strip()
        if not reason:
            raise ValueError("verification reason is required")
        cursor = self.connection.execute(
            """
            UPDATE candidate_links
            SET status = ?, reason = ?, verified_at = ?
            WHERE canonical_url = ? AND status = 'discovered'
            """,
            (
                "eligible" if eligible else "rejected",
                reason,
                datetime.now(timezone.utc).isoformat(),
                normalized,
            ),
        )
        if cursor.rowcount != 1:
            raise ValueError("candidate link is missing or already verified")
        self.connection.commit()

    def summary(self) -> dict[str, int]:
        counts = {
            row["status"]: row["count"]
            for row in self.connection.execute(
                "SELECT status, COUNT(*) AS count FROM candidate_links GROUP BY status"
            )
        }
        discovered = sum(counts.values())
        remaining = counts.get("discovered", 0)
        return {
            "discovered_count": discovered,
            "verified_count": discovered - remaining,
            "eligible_count": counts.get("eligible", 0),
            "rejected_count": counts.get("rejected", 0),
            "remaining_unverified_count": remaining,
        }

    def pending(self, *, limit: int) -> list[dict[str, str]]:
        if limit <= 0:
            raise ValueError("pending limit must be positive")
        return [
            {
                "url": row["canonical_url"],
                "source": row["source"],
                "query_family": row["query_family"],
            }
            for row in self.connection.execute(
                """
                SELECT canonical_url, source, query_family
                FROM candidate_links
                WHERE status = 'discovered'
                ORDER BY discovered_at, canonical_url
                LIMIT ?
                """,
                (limit,),
            )
        ]

    def validate_terminal(self, result: dict[str, Any]) -> dict[str, Any]:
        summary = self.summary()
        reported_remaining = result.get("remaining_unverified_count")
        if reported_remaining != summary["remaining_unverified_count"]:
            raise TerminalResultError(
                "reported remaining count does not match durable candidate queue"
            )
        if result.get("status") == "no_eligible_job_found":
            remaining = summary["remaining_unverified_count"]
            if remaining:
                raise TerminalResultError(
                    f"{remaining} unverified candidate links remain"
                )
            if result.get("verified_link_count") != summary["verified_count"]:
                raise TerminalResultError(
                    "reported verified count does not match durable candidate queue"
                )
            return {"status": "exhausted", **summary}
        return {"status": "accepted", **summary}


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path | None, value: dict[str, Any]) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n"
    if path is None:
        print(encoded, end="")
        return
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.write_text(encoded, encoding="utf-8")
    os.chmod(path, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("discover", "pending", "verify", "summary", "validate-terminal")
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--result", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--url")
    parser.add_argument("--eligible", choices=("true", "false"))
    parser.add_argument("--reason")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    queue = CandidateQueue(args.database)
    try:
        if args.action == "discover":
            if args.input is None:
                parser.error("discover requires --input")
            payload = _read_json(args.input)
            links = payload.get("links") if isinstance(payload, dict) else payload
            if not isinstance(links, list):
                raise ValueError("discovery input must contain a links array")
            receipt = {"status": "recorded", **queue.discover(links), **queue.summary()}
        elif args.action == "pending":
            receipt = {
                "status": "ok",
                "links": queue.pending(limit=args.limit),
                **queue.summary(),
            }
        elif args.action == "verify":
            if not args.url or args.eligible is None or not args.reason:
                parser.error("verify requires --url, --eligible, and --reason")
            queue.mark_verified(
                args.url, eligible=args.eligible == "true", reason=args.reason
            )
            receipt = {"status": "verified", **queue.summary()}
        elif args.action == "summary":
            receipt = {"status": "ok", **queue.summary()}
        else:
            if args.result is None:
                parser.error("validate-terminal requires --result")
            receipt = queue.validate_terminal(_read_json(args.result))
    finally:
        queue.close()
    _write_json(args.output, receipt)


if __name__ == "__main__":
    main()
