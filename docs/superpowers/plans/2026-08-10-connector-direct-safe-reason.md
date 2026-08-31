# Connector Direct Safe Reason Implementation Plan

> **For Luna:** Use Superpowers test-driven-development. Own only `apps/mr-bot/lib/connector-peatix-workflow.js`, `connector-peatix-workflow.test.js`, `connector-minimal-runner.js`, and `connector-minimal-runner.test.js`. You are not alone in the codebase; preserve all other edits. Do not commit or push.

**Goal:** Preserve the exact privacy-safe Peatix direct failure stage through the provider-neutral circuit report so the next live wake identifies the one broken action.

**Architecture:** The Peatix browser provider already returns a bounded static `reason`. The workflow validates and prefixes it as `peatix_<reason>` in its failed operation. The runner validates operation `safe_reason`, preserves the direct reason across a failed Browser Harness fallback, and uses the last exact safe reason when the failure count opens the circuit. Status and `consecutive_failure_count` continue to express why execution stopped.

**Ponytail full gate:** Reuse existing outcome, operation, report, and Telegram fields. Add no new log/store/schema/key, event identity, raw DOM, prompt, retry, or browser action.

**Soft target:** 4 files, production ≤22 LOC, tests ≤55 LOC. Four files are required because the trusted provider reason crosses both workflow and provider-neutral runner contracts.

## Task 1: TDD safe stage propagation

- [x] RED: Peatix workflow maps `unknown_required_field` to failed `peatix_unknown_required_field`, rejects malformed/absent reasons to `direct_action_unverified`, and still maps registered to completed.
- [x] RED: runner preserves a valid direct safe reason when fallback fails and reports it at 3-failure circuit-open; malformed reasons fail to a generic safe reason.
- [x] GREEN: add only bounded safe-reason validation/propagation; keep action-history exact fields unchanged.
- [x] Run Peatix workflow, runner, production/native integration, syntax, diff, and fresh review checks.

## Acceptance

The next official circuit report contains a static safe stage such as `peatix_unknown_required_field` rather than `consecutive_failure_limit`; it contains no event URL/ID, title, attendee data, selector, DOM, or private value. Submit behavior is unchanged.
