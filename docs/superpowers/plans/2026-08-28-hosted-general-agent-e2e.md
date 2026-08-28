# GA-11C Hosted General Agent E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove one authenticated paid tenant crosses cloud vault, reference-only enqueue, isolated capability worker, structured receipt, and replay-zero on the shared kernel, then bind the contract to fresh production panel health/state evidence.

**Architecture:** Extend the GA-11A test fixture only. Enqueue through `enqueueHostedGoal`, convert the stored row to the existing claimed-job shape, execute it through `executeCapabilityJob` and the GA-11B adapter, require one heartbeat and one completion receipt, then call ingress again and require no second worker execution.

**Tech Stack:** Node test runner and existing hosted ingress, adapter, runtime worker, cloud secret provider.

**Spec:** `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md` (GA-11).

## Global Constraints

- No production mutation, new tenant, new payment, new connector, provider contact, or synthetic claim of Calendar readiness.
- Production evidence reports Calendar as `action_required`; the E2E contract does not rewrite it.
- Receipt contains no goal text, secret value, phone, chat ID, or raw tenant identity.

### Task 1: One-tenant queue-to-receipt contract

**Files:**
- Modify: `apps/life-manager/lib/hosted-goal-ingress.test.js`
- Modify: `docs/superpowers/specs/2026-08-01-dais-life-manager-five-phase-execution-spec.md`

- [ ] **Step 1:** Add a test that calls ingress, runs the queued job through `executeCapabilityJob` plus `createGeneralAgentWorkLoopAdapter`, invokes the scheduled heartbeat inside the specialist, and asserts the call order `heartbeat → clear → complete` with one safe receipt.
- [ ] **Step 2:** Call ingress with the same goal again, assert `created=false`, worker execution remains one, and receipt count remains one.
- [ ] **Step 3:** Run hosted ingress/adapter/runtime/billing/secret/tenant focused tests.
- [ ] **Step 4:** Record fresh production evidence: public health 200, authenticated canonical panel query 0, stable identity hash, paid true, phone/call/notifications true, and current connection states. Keep Calendar `action_required` visible.
- [ ] **Step 5:** Update GA-11 to DONE with contract/live boundaries, fetch, commit, push, and read back PR #3018.
