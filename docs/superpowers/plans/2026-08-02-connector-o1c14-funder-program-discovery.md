# O1C-14 Funder Program Discovery Implementation Plan

> **For agentic workers:** Use `executing-plans` inline. Do not pause for human confirmation.

**Goal:** Discover official programs daily and append new or changed entries beyond the fixed legacy registry.

**Architecture:** Agent judgment reads full official sources. A deterministic provenance gate validates freshness, hashes, exact excerpts and linked official URLs, compares against current registry identity, and emits append-only snapshots plus a daily receipt.

### Task 1: Discovery contract
- [x] RED then GREEN for fresh complete source assessment, new program, existing change, and zero-candidate day.
- [x] Reject stale/incomplete sources, hash mismatch, fabricated excerpt, unsafe/unlinked URL, and duplicates.

### Task 2: Append-only persistence
- [x] Add current discovery fields and daily receipt storage with tenant-bound service-only RLS.
- [x] Prove exact replay is idempotent and zero-row/collision is not success.

### Task 3: Daily runtime
- [x] Commit official seed sources and install one 06:30 Asia/Tokyo OpenClaw discovery job.
- [ ] Run live source readback, record evidence, mark O1C-14, count 98 remaining, push, and verify remote equality.
