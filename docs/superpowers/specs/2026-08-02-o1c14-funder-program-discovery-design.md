# O1C-14 Funder Program Discovery Design

## Goal

Every day at 06:30 Asia/Tokyo, inspect current official accelerator, VC, grant, and prize pages. Append newly discovered programs and changed existing programs to the tenant funder registry without treating a fixed seed list as the universe.

## Ownership boundary

The agent owns semantic judgment: which linked official program is relevant, its human-readable name, status, location, solo-founder rule, deadline, terms summary hash, and the exact source excerpt supporting the judgment. Deterministic code owns provenance and persistence gates only.

Each source snapshot must be fetched within 26 hours of the run, use credential-free HTTPS, include a SHA-256 matching the supplied full text, and enumerate the exact HTTPS links found on the page. Every candidate URL must be the source URL itself or one of those links. Every evidence excerpt must occur verbatim in the supplied source text. The assessment must account for every fetched source, including sources with zero candidates.

## Data flow

```text
06:30 JST scheduler
      |
      v
official seed pages + agent-discovered official pages
      |
      v
fresh text, links, hash -----> agent assessment
      |                            |
      +---------- provenance gate-+
                                   |
                         new / changed / unchanged
                                   |
                    append-only registry snapshots
                                   |
                         daily discovery receipt
```

No browser submission occurs here. Unknown facts remain explicit `unknown` or `null`; they are not inferred. O1C-15 re-verifies submission-day facts.

## Failure behavior

A stale or missing source, hash mismatch, fabricated excerpt, unlinked candidate URL, duplicate program, incomplete source assessment, or database zero-row result fails closed. A valid complete run with zero new candidates is a successful discovery run, not proof that no programs exist outside the inspected sources.
