#!/usr/bin/env python3
"""Prepare one claim-bound pitch for each verified compatible writing program."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from claim_store import ClaimStore, _text, _timestamp  # noqa: E402
from claim_supply import _extract_json  # noqa: E402
from opportunity_store import OpportunityStore, TransitionError  # noqa: E402


class PitchUnavailable(RuntimeError):
    pass


def build_pitch_prompt(opportunity: dict[str, Any], claims: list[dict[str, Any]]) -> str:
    compact_claims = [
        {
            "claim_id": row["claim_id"],
            "source_url": row.get("canonical_url") or row.get("url"),
            "title": row["title"],
            "claim": row["claim"],
            "evidence_excerpt": row["evidence_excerpt"],
            "reader_job": row["reader_job"],
        }
        for row in claims
    ]
    return f"""Prepare one paid-article pitch using the official publisher terms and exactly
one durable new claim below. Select only a claim that fits the named audience and gives the
reader a concrete job or decision. Do not invent compensation, policy, product behavior,
sources, claim IDs, URLs, or reader jobs. Copy claim_id, source_url, and reader_job exactly.
Return exactly one JSON object and no prose:
{{"claim_id":"clm_...","source_url":"https://...","reader_job":"...",
  "title":"specific article title","angle":"specific evidence-led reader outcome"}}

Official verified opportunity:
{json.dumps(opportunity, ensure_ascii=False, sort_keys=True, default=str)}

Available durable claims:
{json.dumps(compact_claims, ensure_ascii=False, sort_keys=True)}
"""


def model_choose(
    opportunity: dict[str, Any], claims: list[dict[str, Any]], *,
    runner: Path, run_id: str, timeout: int = 300,
) -> dict[str, Any]:
    try:
        result = subprocess.run(
            [str(runner), "judge", "--prompt-file", "-"],
            input=build_pitch_prompt(opportunity, claims),
            capture_output=True,
            text=True,
            env={**os.environ, "ARTICLE_RUN_ID": run_id},
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise PitchUnavailable(type(error).__name__) from error
    if result.returncode != 0:
        raise PitchUnavailable(f"model runner returned {result.returncode}")
    try:
        value = _extract_json(result.stdout)
    except Exception as error:
        raise PitchUnavailable("model returned no pitch JSON") from error
    if not isinstance(value, dict):
        raise PitchUnavailable("model pitch is not an object")
    return value


def _eligible(database: Path, budget: int) -> list[dict[str, Any]]:
    if budget < 1:
        raise ValueError("pitch budget must be positive")
    OpportunityStore(database)
    with sqlite3.connect(database, timeout=30) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT * FROM opportunities WHERE state='POLICY_CLEAR' "
            "AND active_pitch_id IS NULL ORDER BY updated_at,opportunity_id LIMIT ?",
            (budget,),
        ).fetchall()
    return [dict(row) for row in rows]


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


def _validate_proposal(
    proposal: dict[str, Any], available: list[dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    required = {"claim_id", "source_url", "reader_job", "title", "angle"}
    if not isinstance(proposal, dict) or set(proposal) != required:
        raise PitchUnavailable("pitch JSON fields differ from the contract")
    values = {key: _text(proposal.get(key), key) for key in required}
    by_id = {row["claim_id"]: row for row in available}
    claim = by_id.get(values["claim_id"])
    if claim is None:
        raise PitchUnavailable("pitch selected an unavailable claim_id")
    if values["source_url"] != claim["canonical_url"]:
        raise PitchUnavailable("pitch source_url differs from durable claim")
    if values["reader_job"] != claim["reader_job"]:
        raise PitchUnavailable("pitch reader_job differs from durable claim")
    return values, claim


def run_pitch_prep(
    opportunity_database: Path | str, claim_database: Path | str,
    receipt_path: Path | str, *, observed_at: str, budget: int,
    chooser: Callable[[dict[str, Any], list[dict[str, Any]]], dict[str, Any]],
) -> dict[str, Any]:
    observed_at = str(_timestamp(observed_at, "observed_at"))
    opportunity_database = Path(opportunity_database)
    store = OpportunityStore(opportunity_database)
    claims = ClaimStore(claim_database)
    eligible = _eligible(opportunity_database, budget)
    used = store.used_pitch_claim_ids()
    available = [row for row in claims.list_unconsumed(limit=100) if row["claim_id"] not in used]
    pitches: list[dict[str, Any]] = []
    for opportunity in eligible:
        if not available:
            pitches.append(
                {
                    "opportunity_id": opportunity["opportunity_id"],
                    "publisher": opportunity["publisher"],
                    "status": "NO_NEW_CLAIM",
                    "reason": "no unused durable claim is available",
                }
            )
            continue
        try:
            proposal, claim = _validate_proposal(chooser(opportunity, available), available)
            created = store.create_pitch(
                opportunity["opportunity_id"],
                title=proposal["title"], angle=proposal["angle"],
                claim_id=claim["claim_id"], claim_url=claim["canonical_url"],
                claim_sha256=claim["first_retrieved_sha256"], reader_job=claim["reader_job"],
                created_at=observed_at,
            )
            if not created["inserted"]:
                raise PitchUnavailable("duplicate pitch refused")
            store.advance(
                opportunity["opportunity_id"], "PITCH_READY",
                observed_at=observed_at, pitch_id=created["pitch_id"],
                reason="claim-bound proposal passed deterministic validation",
            )
            available = [row for row in available if row["claim_id"] != claim["claim_id"]]
            pitches.append(
                {
                    "opportunity_id": opportunity["opportunity_id"],
                    "publisher": opportunity["publisher"],
                    "status": "PITCH_READY",
                    "pitch_id": created["pitch_id"],
                    "claim_id": claim["claim_id"],
                    "source_url": claim["canonical_url"],
                    "title": proposal["title"],
                    "angle": proposal["angle"],
                }
            )
        except (PitchUnavailable, TransitionError, ValueError) as error:
            pitches.append(
                {
                    "opportunity_id": opportunity["opportunity_id"],
                    "publisher": opportunity["publisher"],
                    "status": "INVALID_PROPOSAL",
                    "reason": str(error),
                }
            )
    prepared = sum(item["status"] == "PITCH_READY" for item in pitches)
    receipt = {
        "version": 1,
        "observed_at": observed_at,
        "pitches": pitches,
        "totals": {
            "eligible": len(eligible), "prepared": prepared,
            "unavailable": len(eligible) - prepared,
        },
    }
    _atomic_json(Path(receipt_path), receipt)
    return receipt
