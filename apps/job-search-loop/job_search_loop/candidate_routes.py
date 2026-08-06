from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .ledger import FenceError, Ledger
from .playwright_ats import ranked_pre_submit_candidates


def materialize_canonical_routes(
    ledger_path: Path, prefilter_result: Path
) -> list[dict[str, Any]]:
    payload = json.loads(Path(prefilter_result).read_text(encoding="utf-8"))
    candidates = ranked_pre_submit_candidates(payload, limit=3)
    ledger = Ledger(Path(ledger_path))
    materialized: list[dict[str, Any]] = []
    try:
        for candidate in candidates:
            official_url = str(candidate.get("official_url") or "")
            url_sha256 = hashlib.sha256(official_url.encode("utf-8")).hexdigest()
            try:
                application_id = ledger.add_application(
                    str(candidate.get("company") or ""),
                    str(candidate.get("title") or ""),
                    official_url,
                )
            except FenceError as error:
                if "canonical posting is already owned by " not in str(error):
                    raise
                materialized.append({"status": "skipped_cross_owner", "reason": "canonical_posting_owned_elsewhere", "url_sha256": url_sha256})
                continue
            source_material = json.dumps(
                {
                    "official_url": official_url,
                    "source_spans": list(candidate.get("source_spans") or []),
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            route_id = ledger.register_application_route(
                application_id,
                route_kind="canonical_ats",
                endpoint=official_url,
                ordinal=1,
                source_url=official_url,
                source_sha256=hashlib.sha256(source_material.encode("utf-8")).hexdigest(),
                recipient_acceptance="not_applicable",
            )
            materialized.append(
                {
                    "application_id": application_id,
                    "route_id": route_id,
                    "url_sha256": url_sha256,
                }
            )
    finally:
        ledger.close()
    return materialized
