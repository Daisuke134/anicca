# GA-12A Public Marketplace Manifest Plan

> **For agentic workers:** Use Superpowers task-by-task. Keep the general-agent kernel provider-neutral.

**Goal:** Publish one credential-free marketplace manifest that shows how an unknown site joins the existing `marketplace.application` kernel without site-specific code.

**Architecture:** Add one example JSON beside the public capability catalogue. The example declares references, authorization state, bounded browser transport, effect receipt, and readback contract only. Extend the existing catalogue test to reject provider names, URLs, DOM selectors, raw secrets, personal identifiers, and human-loop fields.

**Files:**

- Add: `skills/earn/gig/config/provider-capability.example.json`
- Modify: `skills/earn/gig/tests/test_provider_authorization.py`
- Modify: `docs/superpowers/specs/2026-08-01-dais-mr-bot-five-phase-execution-spec.md`

## Task 1: Public sample contract

- [x] Add a failing test for a versioned `marketplace.application` example with reference placeholders only.
- [x] Require default `unknown`, `cloak_browser`, private authorization receipt, `application_receipt`, replay-zero, and no credential/PII/provider-specific instructions.
- [x] Add the smallest JSON example that passes the contract.
- [x] Run the focused provider authorization test and PII/OSS checks for only the changed paths.
- [x] Mark GA-12 `IN_PROGRESS` with GA-12A evidence, fetch, commit, push, and read back PR #3018.

Delivery: commit `1d87e401f`; PR #3018 is open, head-matched, and mergeable.
