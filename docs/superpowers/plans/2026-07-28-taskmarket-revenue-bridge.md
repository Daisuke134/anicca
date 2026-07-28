# TaskMarket revenue bridge implementation plan

> Workflow: Superpowers TDD → verification-before-completion → finishing branch.

## Goal

Convert only a real, external TaskMarket award into one append-only Life Manager
earnings row. An open task, a submission, a pitch, an API-only award claim, a
self-award, or a non-final Base receipt must write zero rows.

## Task 1 — Pure award contract

1. Add failing tests for completed/external/owned-worker requirements, exact
   award fields, conservative sub-cent handling, stable entry keys, and
   self-award rejection.
2. Implement `taskmarket-work-ledger.js`.
3. Run the focused tests to green.

## Task 2 — Independent Base verification

1. Add failing tests for Base chain 8453, finalized block, successful receipt,
   exact settlement hash, and exactly one native-USDC transfer of
   `workerPayment` to the owned worker.
2. Reject mismatched amount, receiver, token, duplicate transfers, premature
   blocks, failed receipts, and self-wallet requesters.
3. Run focused tests to green.

## Task 3 — Production poller and schedule

1. Add failing tests for public submission discovery, bounded TaskMarket
   responses, no-award no-op, duplicate-safe recording, and fail-closed API/RPC
   errors.
2. Implement the poller, boot script, launchd template, and installer without
   changing or unloading any existing loop.
3. Install and kickstart the new reader/writer; verify an open task produces
   `recorded=0`, not fabricated revenue.

## Task 4 — Live evidence

1. Read back the TaskMarket withdrawal destination and pending submission/pitch.
2. Record live launchd state and exact zero-revenue boundary.
3. When the requester awards work, independently verify the Base receipt,
   record exactly once, rerun for `duplicate=1`, and only then close 13c.
