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

The revenue pass entrypoint is `gig_pass.sh`. `run.sh` is the Life Manager
`earn/gig` slot bridge. Runtime state, credentials, browser identity, and
transaction evidence remain outside the public repository.

## Autonomy boundary

The loop performs browser and code work itself. A synchronous human body or
voice is unavailable, so required Meet/Zoom/phone/live teaching/face interview
and human voice recording are rejected. Initial KYC/OAuth credential bootstrap
may be minimal human input; routine discovery, application, reply, delivery,
reporting, recovery, and improvement never wait for a human.

## Migration status

D5-A places the complete tracked source and tests in this canonical slot.
D5-B makes every engine and browser path repository-relative. D5-C provides the
idempotent macOS/Linux local installer and adopts existing state without
copying it. D5-D/E verify parity before production cutover. Do not run this
checkout as production until those gates are complete.
