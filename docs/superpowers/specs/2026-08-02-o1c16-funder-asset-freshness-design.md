# O1C-16 Funder Asset Freshness Design

## Goal

No funder form may open with stale company facts, traction, MRR, deck, or founder video. The exact submission attempt must carry one immutable, tenant-bound freshness receipt.

## Boundary

The agent reads current company material and decides which exact claims and revenue sources are semantically applicable. Deterministic code owns timestamps, JSON pointers, arithmetic, content hashes, source/artifact ordering, media constraints, and the append-only receipt.

```text
providers -> dashboard ----+----> traction / MRR citations
current KIT documents ------+----> company-fact citations
deck source -> PDF ----------+----> artifact attestation
selected founder video ------+----> media attestation
                            v
                 attempt-bound freshness gate
                    |                |
             refresh_required   submit_allowed
```

The dashboard and every selected MRR provider timestamp must be at most 26 hours old. Dashboard fetch and KIT capture must be at most six hours old. MRR must equal the exact sum of agent-selected recurring-revenue JSON pointers; deterministic code never infers revenue semantics from keywords. A deck must be generated after both its source and dashboard snapshot. A selected video needs a current digest attestation, H.264 video, AAC audio, at most 60 seconds, and at most 100 MB.

The browser requires both O1C-15 and O1C-16 allow receipts before creating a page. Unknown, stale, inconsistent, or missing input fails closed without opening the browser.
