# TECH PLAY Discovery Audit Persistence Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Superpowers test-driven-development. Sol owns plan/review/verification/commit; Luna owns the exact two operations files.

**Goal:** Persist TECH PLAY discovery aggregate counts in the connector private state directory so the production factory can wire the existing workflow without losing its discovery audit.

**Architecture:** Reuse `safeDoorkeeperDiscoveryAudit`, the existing JSONL append helper, and the existing private-directory/file-mode contract. Add only one provider-specific filename, one thin recorder, and its exported operation. Do not add a logger, schema, database, provider registry, or production factory change in this slice.

**Files / soft target:**

- Modify `apps/mr-bot/lib/connector-minimal-operations.js` — about 4–8 LOC.
- Modify `apps/mr-bot/lib/connector-minimal-operations.test.js` — about 25–45 LOC.

## Grounding

- Node.js `fs.appendFileSync`: <https://nodejs.org/api/fs.html#fsappendfilesyncpath-data-options> — appends data synchronously to an existing or newly created file.
- GitHub code search for `appendFileSync jsonl` found multiple one-record-per-line JavaScript implementations; the repository already has the same reviewed helper, so local reuse wins.
- Japanese GitHub search for `監査ログ JSONL` found the same one-line-per-event convention; no external package is needed.
- Existing `recordDoorkeeperDiscoveryAudit` and `recordEventbriteDiscoveryAudit` already validate the exact five-count monotonic contract required by TECH PLAY.

## Contract

- [x] RED: operations do not expose `recordTechPlayDiscoveryAudit` and no TECH PLAY audit file is written.
- [x] Add exact private file `techplay-discovery-audits.jsonl`.
- [x] Add `recordTechPlayDiscoveryAudit` as a thin wrapper over `safeDoorkeeperDiscoveryAudit` and the existing append helper.
- [x] Persist only schema version, wake ID, five aggregate counts, and recorded timestamp; file mode remains `0600`.
- [x] Reject missing/extra/private keys, non-integers, bounds violations, and monotonic-count violations without appending a second row.
- [x] Run focused/full operations tests, syntax, diff check, mutation proof, and fresh Sol review.
- [x] Do not change factory/router, browser Harness, evidence, Calendar, native order, launchd, or perform any external side effect.
