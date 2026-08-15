#!/usr/bin/env python3
"""funnel.py — summarize_gig_funnel(applied_rows) -> {applied, replied, won, paid} (REQ-LV-015).
Pure: input is ONLY the already-collected ~/gig/applied.jsonl rows for the current pass (adds zero
new browser access). Cumulative funnel: a row's status is the FURTHEST stage that
applicant/case reached; each bucket counts every row whose furthest stage is >= that bucket.
受注/成約 are synonyms for `won`; 検収完了/支払 are synonyms for `paid`. Unrecognized/housekeeping
status rows (e.g. pass-log rows that aren't real applications) are ignored entirely.
"""

_WON_STATUSES = {"受注", "成約"}
_PAID_STATUSES = {"検収完了", "支払"}


def summarize_gig_funnel(applied_rows):
    applied = replied = won = paid = 0
    for row in applied_rows or []:
        status = (row or {}).get("status")
        if status == "applied":
            applied += 1
        elif status == "replied":
            applied += 1
            replied += 1
        elif status in _WON_STATUSES:
            applied += 1
            replied += 1
            won += 1
        elif status in _PAID_STATUSES:
            applied += 1
            replied += 1
            won += 1
            paid += 1
        # else: unrecognized/housekeeping rows (e.g. no_new_client_reply) are ignored
    return {"applied": applied, "replied": replied, "won": won, "paid": paid}


def dedupe_latest_status(rows, key_field="requestId"):
    """Phase 5 hardening finding F-VERIF-5 fix (caller-contract side, summarize_gig_funnel itself
    unchanged): applied.jsonl is an APPEND-ONLY log where the SAME requestId gets a NEW row every
    time its status advances (applied -> replied -> 受注, per gig-cli.sh's STARTUP B1/B2 prompt
    text) — passing all those rows straight into summarize_gig_funnel would triple-count a single
    real application. This keeps only the LAST-occurring row per requestId (file order =
    chronological, so "last occurrence" = "most recent status"), which is exactly the "1
    requestId につき最新状態のみ" contract F-VERIF-5 recommends. Rows without a requestId pass
    through unchanged (never dropped, never miscounted against another row).

    `key_field` (REQ-GFV-012) widens this to also dedupe listings.jsonl by `listing_id` — same
    latest-row-wins semantics, reused rather than duplicated. Default stays "requestId" so every
    existing caller/test is unaffected."""
    latest_by_id = {}
    passthrough = []
    order = []
    for row in rows or []:
        rid = (row or {}).get(key_field)
        if rid is None:
            passthrough.append(row)
            continue
        if rid not in latest_by_id:
            order.append(rid)
        latest_by_id[rid] = row
    return [latest_by_id[rid] for rid in order] + passthrough


def summarize_gig_funnel_by_category(rows):
    """REQ-GFV-011 / PROP-012,013 — partitions deduped rows by row.get("category") or
    "uncategorized", then applies the EXISTING summarize_gig_funnel bucketing independently within
    each partition. Pure, in-memory only. Reuses summarize_gig_funnel (and therefore
    _WON_STATUSES/_PAID_STATUSES) rather than redefining the status vocabulary — PROP-013's
    single-definition-site invariant."""
    buckets = {}
    for row in rows or []:
        category = (row or {}).get("category") or "uncategorized"
        buckets.setdefault(category, []).append(row)
    return {category: summarize_gig_funnel(category_rows) for category, category_rows in buckets.items()}


def count_live_listings(listing_rows):
    """REQ-GFV-012 — dedupe listing_rows by listing_id (latest row wins, via dedupe_latest_status's
    widened key_field), then count how many of those latest-status rows are status=="live". Pure,
    in-memory only. Rows missing listing_id are excluded (dedupe_latest_status's passthrough), never
    crash, never counted."""
    deduped = dedupe_latest_status(listing_rows or [], key_field="listing_id")
    return sum(1 for row in deduped if (row or {}).get("listing_id") is not None and (row or {}).get("status") == "live")
