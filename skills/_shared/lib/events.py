"""events — runner-side earn-event verification (INV-13 active half).

PROP-G2-runtime (required:true, Tier 1 integration) — REQ-G2 step (b): three checks
that ALL must pass before earnings.jsonl gets a row:
  1. Endpoint allowlist (= settled-payout endpoint only, not benign reads)
  2. Hash-fidelity (= re-fetched body sha256 matches event's response_sha256)
  3. Field-equality (= receipt_id / amount / payer all appear at allowlist-declared
     JSON paths AND values equal after unit canonicalization)
Closes FIND-015 + ROUND-2-001 critical + ROUND-3-003 (off-by-0.005 epsilon).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    failed_check: str | None = None  # e.g. "endpoint-not-allowlisted", "field-mismatch:receipt_id"


def _sha256(s: str | bytes) -> str:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return hashlib.sha256(s).hexdigest()


def _jsonpath_get(obj: Any, path: str) -> Any:
    """Minimal $.a.b.c style lookup. No filters, no slices. Returns None if
    any segment missing.
    """
    if not path.startswith("$"):
        return None
    cur = obj
    for seg in path.lstrip("$").lstrip(".").split("."):
        if not seg:
            continue
        if not isinstance(cur, dict) or seg not in cur:
            return None
        cur = cur[seg]
    return cur


def _allowlist_lookup(allowlist: dict, platform: str, endpoint: str) -> dict | None:
    """Return the allowlist entry matching (platform, endpoint) using simple
    {receipt_id} template matching, else None.
    """
    if platform not in allowlist:
        return None
    for entry in allowlist[platform].get("endpoints", []):
        tmpl = entry["endpoint"]
        if "{receipt_id}" in tmpl:
            # Replace template token with a wildcard match
            prefix, _, suffix = tmpl.partition("{receipt_id}")
            if endpoint.startswith(prefix) and endpoint.endswith(suffix):
                return entry
        elif endpoint == tmpl:
            return entry
    return None


def _amount_equal(claim: Any, observed: Any, unit: str, comparison: str) -> bool:
    """Per-unit equality. unit = jpy_int (exact) | usdc_float_6dp (epsilon).
    comparison = 'exact' | 'epsilon:<value>'.
    """
    if unit == "jpy_int":
        return isinstance(claim, int) or isinstance(claim, float) and float(claim).is_integer() \
            if False else int(claim) == int(observed)
    if unit == "usdc_float_6dp":
        if comparison.startswith("epsilon:"):
            eps = float(comparison.split(":", 1)[1])
        else:
            eps = 0.0
        return abs(float(claim) - float(observed)) <= eps
    # Unknown unit fails closed.
    return False


def verify_earn_event(
    event: dict,
    allowlist: dict,
    refetch_fn: Callable[..., str],
) -> VerifyResult:
    """Three-check verify (REQ-G2 step b)."""
    platform = event.get("platform")
    api_call = event.get("platform_api_call") or {}
    endpoint = api_call.get("endpoint")
    declared_sha = api_call.get("response_sha256")

    # ── Step 1: endpoint allowlist ──────────────────────────────────
    entry = _allowlist_lookup(allowlist, platform, endpoint)
    if entry is None:
        return VerifyResult(ok=False, failed_check="endpoint-not-allowlisted")

    # ── Step 2: hash-fidelity ──────────────────────────────────────
    body = refetch_fn(endpoint=endpoint, platform=platform)
    body_sha = _sha256(body)
    if body_sha != declared_sha:
        return VerifyResult(ok=False, failed_check="response-hash-mismatch")

    # ── Step 3: field-equality ─────────────────────────────────────
    try:
        parsed = json.loads(body) if entry.get("response_format", "json") == "json" else None
    except (json.JSONDecodeError, TypeError):
        return VerifyResult(ok=False, failed_check="field-mismatch:body-unparseable")

    # receipt_id
    observed_rid = _jsonpath_get(parsed, entry["receipt_id_path"])
    if observed_rid is None or str(observed_rid) != str(event.get("receipt_id")):
        return VerifyResult(ok=False, failed_check="field-mismatch:receipt_id")

    # amount
    observed_amount = _jsonpath_get(parsed, entry["amount_path"])
    if observed_amount is None:
        return VerifyResult(ok=False, failed_check="field-mismatch:amount-missing")
    unit = entry["unit"]
    comparison = entry.get("comparison", "exact")
    if unit == "jpy_int":
        claim = event.get("amount_jpy")
    elif unit == "usdc_float_6dp":
        claim = event.get("amount_usdc")
    else:
        return VerifyResult(ok=False, failed_check=f"field-mismatch:unknown-unit:{unit}")
    if claim is None or not _amount_equal(claim, observed_amount, unit, comparison):
        return VerifyResult(ok=False, failed_check="field-mismatch:amount")

    # payer
    observed_payer = _jsonpath_get(parsed, entry["payer_path"])
    if observed_payer is None or str(observed_payer) != str(event.get("payer")):
        return VerifyResult(ok=False, failed_check="field-mismatch:payer")

    return VerifyResult(ok=True)
