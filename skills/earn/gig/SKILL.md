---
name: gig-work
description: Local-only autonomous gig marketplace loop that discovers work, applies, replies, delivers, maintains listings, reports every effect, and improves from verified revenue outcomes.
disable-model-invocation: true
---

# Gig work

This package is the canonical Life Manager source for the local Gig loop.
It owns four revenue lanes:

| Lane | Required behavior |
|---|---|
| Apply | Discover eligible single and recurring work, submit, then verify the submission, marketplace history, and canonical ledger |
| Reply | Detect buyer messages, answer promptly, and verify the buyer-visible response |
| Fulfill | Build, validate, submit, revise, reconcile acceptance, and record paid revenue |
| List | Inspect the storefront every hour and publish or improve an offer only when the public result is verifiable |

The four production entrypoints are `scripts/storefront_direct.py`,
`scripts/application_parent.py`, `scripts/reply_detector.py`, and
`scripts/paid_direct.py`. The exact scheduler and support-owner allowlist is
`config/launchd/agents/gig.json`. Runtime state, credentials, browser identity,
and transaction evidence remain outside the public repository.

## Autonomy boundary

The loop performs browser and code work itself. A synchronous human body or
voice is unavailable, so required Meet/Zoom/phone/live teaching/face interview
and human voice recording are rejected. Initial KYC/OAuth credential bootstrap
may be minimal human input; routine discovery, application, reply, delivery,
reporting, recovery, and improvement never wait for a human.

## Production boundary

Only immutable releases of this public repository may run production. Legacy
shared-pass, Hermes, private-worktree, and compatibility entrypoints are not
rollback paths.
