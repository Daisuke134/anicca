# The Measurement Ledger

One append-only ledger that every metric flows into, so "where are we right
now?" is always answerable from primary data — and so a broken measurement
is itself visible in the data.

## Design

- **One file**: `measurement-ledger.jsonl` — one JSON object per line,
  appended, never edited in place.
- **One script per metric**, each small and independently runnable, each
  appending rows of one `type`:
  - `aso` — app-store keyword ranks (from the free, no-auth iTunes Search
    API; the rank is the relevance order, a standard free proxy — labeled as
    such, not confused with popularity scores).
  - `seo_bing` / `seo_google` — search-result positions for target queries.
    The engine is recorded on every row; a Bing position is never reported
    as a Google position.
  - `geo` — whether AI answers mention or cite the brand, for a fixed prompt
    set, via a free no-key text API. The answering engine is recorded on
    every row.
  - `apify` — public stats of a published automation (runs, users, reviews,
    30-day run success rate) from the platform's unauthenticated public API.
    Earnings need an authenticated route and are a separate row type when
    available.
  - …one row type per platform you sell or publish on, including
    per-listing funnels (impressions → detail views → purchases), not just
    account totals.
- **Failure is a row too.** On error a script appends
  `{"type": ..., "ts": ..., "error": "..."}` and exits non-zero. A missing
  row and an error row are different facts; silence is the only
  unacceptable outcome. (This rule is what surfaced a chronic intermittent
  API failure that had been waved away as "provider instability" — see the
  loop repair playbook.)
- **A snapshot builder** reads the latest row of each type and regenerates a
  single `rankings-latest.json` that dashboards consume, so the dashboard's
  only source of truth is the published snapshot, and ledgers stay inputs.
- **Cadence**: a scheduler runs the whole chain every 15 minutes; diffs
  against the previous row are the change report. Reports carry changes,
  anomalies, and new artifacts — unchanged metrics get one line.

## Row schema (example)

```json
{"type": "apify", "ts": "2026-01-01T00:00:00+00:00",
 "actor": "your-name/your-actor", "total_runs": 0, "total_users": 0,
 "runs30d_total": 0, "runs30d_succeeded": 0, "runs30d_timed_out": 0,
 "success_rate30d_computed": null, "reviews": 0, "bookmarks": 0}
```

Conventions: timestamps are UTC ISO-8601; computed fields carry a
`_computed` suffix so measured and derived values are never confused;
routes and engines that produced a value are named on the row itself.

## Example script

[`examples/public_stats_to_ledger.py`](examples/public_stats_to_ledger.py)
is a runnable, generalized version of the pattern: fetch a public stats
endpoint with bounded retries and backoff, append a typed row, and append
an error row instead of failing silently. Copy it, change the endpoint and
field mapping, and you have a new metric in the ledger.

## Provenance

**Proven**: this design runs in production — multiple metric types appended
every 15 minutes, a snapshot regenerated from the ledger, and at least one
real fault (an actor whose public runs were 100% timing out, and a
measurement API failing intermittently) found *because* the ledger made the
absence and the errors visible.
