# Agent Economy Status and Graduation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a truthful status snapshot that combines verified external revenue, compute cost, shelter cost, and graduation readiness.

**Architecture:** `status.mjs` is pure over already-read rows and calls the existing money-truth and treasury-policy modules. It normalizes seconds/milliseconds timestamps, sums only the trailing 30-day window, and returns a fail-closed graduation result when runway or human-fuel evidence is missing.

**Tech Stack:** Node.js ESM, JSONL rows, `node:test`.

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md`

## Global Constraints

- No market price or wallet balance is invented.
- Missing runway or human-paid-inference evidence keeps graduation ineligible.
- Revenue is verified by `money-truth.mjs`; costs are summed conservatively.
- Shelter lease rows are additive and remain separate from compute cost rows.

---

### Task 1: Build the trailing-window status snapshot

**Files:**
- Create: `skills/agent-economy/status.mjs`
- Test: `skills/agent-economy/status.test.mjs`

**Interfaces:**
- Produces: `summarizeEconomyStatus({ earnRows, corrections, computeRows, shelterRows, nowMs, liquidRunwayDays, humanPaidInference30d })`.

- [ ] **Step 1: Write the failing status tests**

  Cover a verified external row, seconds and milliseconds cost timestamps, shelter lease costs, 30-day exclusion, and missing runway evidence.

- [ ] **Step 2: Run `node --test skills/agent-economy/status.test.mjs` and observe the missing module**

- [ ] **Step 3: Implement the pure trailing-window aggregation and CLI JSON output**

- [ ] **Step 4: Run status, money-truth, treasury-policy, install, and OSS tests**

- [ ] **Step 5: Commit and push**

  Run: `git add skills/agent-economy/status.mjs skills/agent-economy/status.test.mjs docs/superpowers/plans/2026-08-21-agent-economy-status.md && git commit -m "feat: add agent economy graduation status" && git push`

