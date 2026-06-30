"""lessons — evidence_id validation (TRAP-4 faithfulness drift).

PROP-C1-evidence (required:true, Tier 0) — REQ-C1: evidence_id must be exactly ONE of
url / payout_id / file path. Paraphrases are forbidden.
"""
from __future__ import annotations

import hashlib
import re


_URL_RE = re.compile(r"^https?://[^\s]+$")
# Payout ids: must start with a letter; allow letters/digits/_-; ≥4 chars; no spaces.
# Accepts caps-only platform formats (e.g. Coconala CN_PAYOUT_...) AND mixed-case
# platform formats (e.g. Stripe STRIPE_po_3ABC).
_PAYOUT_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_\-]{3,}$")
_VALID_TYPES = {"url", "payout_id", "file"}


def validate_evidence_id(value: str, type_tag: str) -> bool:
    """Accept iff value is well-formed for the claimed type AND type is known.

    - url:        must match http(s)://... (full string)
    - payout_id:  must match ^[A-Za-z][A-Za-z0-9_\\-]{3,}$ (letter-led; mixed case OK
                  to accept both caps-only platforms (Coconala CN_PAYOUT_...) and
                  mixed-case platforms (Stripe STRIPE_po_3ABC). FIND-013 doc fix.)
    - file:       must be an absolute path (starts with '/')

    Rejects: paraphrase strings, type mismatches (URL claimed as payout_id, etc),
    empty/whitespace, unknown type tags.
    """
    if type_tag not in _VALID_TYPES:
        return False
    if not isinstance(value, str) or not value or not value.strip():
        return False
    if type_tag == "url":
        return bool(_URL_RE.match(value))
    if type_tag == "payout_id":
        return bool(_PAYOUT_ID_RE.match(value))
    if type_tag == "file":
        return value.startswith("/")
    return False


def dedup_hash(request_id: str, outcome: str) -> str:
    """SHA-256 hex digest used for CROSS-LEARN-SHARE dedup (REQ-D2)."""
    h = hashlib.sha256()
    h.update(request_id.encode("utf-8"))
    h.update(b"\x00")
    h.update(outcome.encode("utf-8"))
    return h.hexdigest()
