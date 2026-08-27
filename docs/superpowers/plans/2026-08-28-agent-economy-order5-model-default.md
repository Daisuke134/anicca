# Agent Economy Order 5 Model Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route the direct receipt-backed gateway through explicit current BlockRun model `openai/gpt-5.4-nano` and retain only secret-free internal failure diagnostics.

**Architecture:** Declare the model in the canonical agent-economy loop environment and use the same current value as the local fallback. Preserve the generic public 502 response while projecting only stage, configured model, HTTP status, and provider code to an injected/default internal diagnostic sink.

**Tech Stack:** Node.js ESM, `node:test`, loop TOML

**Spec:** `docs/superpowers/specs/2026-08-21-agent-economy-design.md` P3 item 5

## Global Constraints

- No paid request, signature, funding change, or provider mutation.
- Never persist or log prompts, response bodies, keys, raw error messages, or unknown error fields.
- Current official catalog readback contains `openai/gpt-5.4-nano` and omits `openai/gpt-5-nano`.
- Explicit environment wins; fallback must also be current so missing configuration cannot restore the stale model.

---

### Task 1: Current model and safe diagnostics

**Files:**
- Modify: `runtime/compute-proxy/proxy.mjs`
- Modify: `loops/agent-economy/loop.toml`
- Modify: `runtime/compute-proxy/__tests__/compute-receipt.test.mjs`
- Modify: `test/agent-economy-control-plane.test.mjs`

**Interfaces:**
- Produces: `resolveFrontierModel(value) -> string`; `safeComputeDiagnostic(error, context) -> allowlisted object`.
- Consumes: `ANICCA_FRONTIER_MODEL`, receipt-backed proxy catch boundary, optional diagnostic sink.

- [x] **Step 1: RED**

Add behavior tests that require undefined model resolution and the canonical loop declaration to use `openai/gpt-5.4-nano`; the old ID must be absent from active proxy/loop configuration. Add a proxy failure test with sentinel prompt/key/raw-message fields and assert the internal diagnostic contains only event/stage/model/http/provider code while the HTTP body remains generic.

- [x] **Step 2: GREEN**

Implement the minimum resolver, loop env row, allowlist projection, and catch wiring. Provider HTTP failures may attach status/code for the projector, but never their body/message.

- [x] **Step 3: Verify and review**

Run focused compute and control-plane tests, the full agent-economy suite, syntax/diff/secret checks, then fresh read-only Sol adversarial review. The primary owns spec, release, live readback, commit, and push.
