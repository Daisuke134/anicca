from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from .mercor_provider import MercorListing, is_approved_mercor_url, ready_for_submit


class MercorSubmitGuardError(ValueError):
    pass


@dataclass(frozen=True)
class MercorSubmitClaim:
    listing_id: str
    title: str
    url: str
    claim_token: str
    pre_submit_evidence_sha256: str


def claim_ready_submission(
    listing: MercorListing,
    *,
    submitted_listing_ids: set[str],
    pre_submit_evidence: Path,
) -> MercorSubmitClaim | None:
    """Create the one-click claim only after ready state and fresh evidence exist."""
    if listing.listing_id in submitted_listing_ids:
        return None
    if not is_approved_mercor_url(listing.url):
        raise MercorSubmitGuardError("listing URL is outside the approved Mercor domain")
    if not ready_for_submit(listing):
        raise MercorSubmitGuardError("listing is not in the live 3/3 ready state")
    evidence_path = Path(pre_submit_evidence).expanduser().resolve()
    if not evidence_path.is_file():
        raise MercorSubmitGuardError("pre-submit evidence is missing")
    evidence_sha256 = hashlib.sha256(evidence_path.read_bytes()).hexdigest()
    claim_token = hashlib.sha256(
        f"{listing.listing_id}\n{listing.url}\n{evidence_sha256}".encode("utf-8")
    ).hexdigest()
    return MercorSubmitClaim(
        listing_id=listing.listing_id,
        title=listing.title,
        url=listing.url,
        claim_token=claim_token,
        pre_submit_evidence_sha256=evidence_sha256,
    )


def classify_submit_readback(*, page_url: str, visible_text: str) -> str:
    """Classify only an authoritative visible result; ambiguous means no retry."""
    text = visible_text.casefold()
    if (
        is_approved_mercor_url(page_url)
        and "your application has been submitted" in text
        and "/jobs/apply/" in page_url
    ):
        return "submitted_pending_review"
    return "submit_unknown"
