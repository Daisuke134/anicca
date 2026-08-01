# O1C-15 Submission-day Verification Design

## Goal

No funder form may be submitted from discovery-time or legacy facts. The exact attempt must carry a same-day official verification of deadline, location, solo-founder acceptance, terms, and eligibility.

## Boundary

The agent reads full official text and current `application-kit://KIT.md`, then makes the semantic eligibility judgment with exact excerpts. Deterministic code verifies source freshness and hashes, official-link provenance, excerpt containment, registry identity/drift, deadline time, and all five required claims. It emits an immutable gate receipt only; it does not click Submit.

```text
current registry identity + same-day official text + current KIT
                         |
                         v
       agent judgment over five required facts
                         |
                         v
 freshness/hash/excerpt/link/drift/deadline gate
            |                         |
          deny                 submit_allowed receipt
```

Unknown solo status, unknown eligibility, a closed deadline, stale source, changed known registry fact, or missing exact evidence fails closed. A null registry fact may be filled by the same-day receipt; a contradictory known registry fact requires a new registry revision before submission.
