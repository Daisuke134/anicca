# O1C-12 Funder Meeting Design

## Outcome

A verified `meeting_requested` Gmail observation can become exactly one
conflict-free Google Calendar event and one source-bound interview brief. A
thread without a real meeting request produces neither artifact.

## Ownership boundary

- The local OpenClaw/DeepSeek agent or cloud Gemini agent reads the untrusted
  Gmail message and decides the proposed time, meeting purpose, location, and
  useful brief content. Its output is explicit `agent_judgment` with exact
  evidence quotes and source references.
- Deterministic code validates fixed formats, binds the judgment to the O1C-11
  observation and application-kit digest, computes duration and calendar
  conflicts, performs one Calendar write, requires positive provider IDs, and
  appends an immutable receipt.
- No keyword or regex decides whether prose means a meeting request.

## Data flow

```text
fresh Gmail full message
        │
        ▼
O1C-11 meeting_requested observation
        │
        ├── agent schedule judgment ── exact quote/time/location
        └── agent brief judgment ───── application-kit source refs
                     │
                     ▼
all-calendar free/busy gate
        │ free                    │ conflict/missing proof
        ▼                         └── no external effect
one gog Calendar create
        │ positive event ID + URL
        ▼
brief artifact + append-only meeting ledger
```

## Contracts

The schedule is future-bound, `Asia/Tokyo`, between 15 and 120 minutes, and
must fit an all-calendar free/busy read. Calendar description contains only
the outreach/status references and brief digest, not raw email content.

The brief has six agent-authored sections: objective, company snapshot,
funder fit, likely questions, questions to ask, and risks. Every section cites
one or more allowed `application-kit://` or original official funder source
references. The brief and rationale are hashed in the repository/database
evidence; raw Gmail text is not persisted there.

## Failure behavior

Missing or non-meeting status, fabricated quote, stale/past or overlapping
time, incomplete free/busy, malformed source, Calendar response without a
positive event ID/URL, or ledger collision fails closed. A post-create
ambiguity is never retried as a new event without reconciliation.

## Current live boundary

As of 2026-08-02 JST, the three live funder threads contain zero
`meeting_requested` observations. O1C-12 therefore proves the executable path
with tests and proves zero live Calendar writes with Gmail/DB readback; it does
not invent a meeting to demonstrate success.
