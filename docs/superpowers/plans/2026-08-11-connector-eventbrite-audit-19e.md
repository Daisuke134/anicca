# Connector Eventbrite privacy-safe discovery audit 19E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development and subagent-driven-development. Luna writes production/tests; Sol reviews and integrates.

**Goal:** Persist Eventbrite's reviewed five-count discovery audit as a private append-only `0600` JSONL row.

**Ponytail decision:** Eventbrite uses the exact same five keys and monotonic inequalities as Doorkeeper. Reuse `safeDoorkeeperDiscoveryAudit`; add only a provider-specific filename, writer method, export, and one focused test. Do not create a generic registry or rename the existing validator.

**Estimated change:** 2 existing files. Production 3–6 LOC; test 30–55 LOC.

## TDD contract

- Modify only `apps/life-manager/lib/connector-minimal-operations.js` and matching test.
- RED asserts `recordEventbriteDiscoveryAudit` exists and appends exactly one row to `eventbrite-discovery-audits.jsonl`.
- Exact persisted keys: schema version, wake ID, recorded timestamp, and `discovered_count`, `within_window_count`, `eligible_count`, `calendar_free_count`, `selected_count`.
- File mode is `0600`. Reject missing/extra keys, private URL/title/email fields, non-integers, negative/>500 values, and monotonic violations without appending.
- Existing provider audit files and schemas remain unchanged.
- Run focused operations, minimal production, Eventbrite workflow, syntax, diff, exact two-file scope. Commit without amend and push. Browser/native/evidence/Telegram/live effects zero.

## Completion gate

Fresh Sol review Critical/Important 0, stable independent GREEN, SSOT/result update, and remote push. Native provider order remains unchanged.

