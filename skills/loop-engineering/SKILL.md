---
name: loop-engineering
description: Use when building, fixing, releasing or operating a Life Manager loop, adding a marketplace lane, or deciding whether existing loop components must be reused.
---

# Loop Engineering

One entry, so no lane invents what another lane already owns. This file routes;
it does not carry the corpus.

```text
loop config -> reusable recipe -> shared runtime -> provider adapter -> official provider
```

Dependencies run one way only. `runtime/` owns scheduling, admission, model
routing, checkpoint/resume, retries, replay prevention, receipts and recovery,
and knows no marketplace rules. A recipe owns one business lifecycle (Apply,
Negotiate, Storefront, Paid) and knows no DOM selector or credential. An adapter
owns only official observation, mutation and readback. A loop config selects a
recipe, provider, cadence and policy — it never implements a second runner,
retry engine, ledger, browser launcher or model client.

## Route by task

| Task | Read |
|---|---|
| Change a loop, its cadence, release or plist | `skills/loop-development/SKILL.md` |
| Build or fix an Apply lane on any marketplace | `references/marketplace-apply-lane.md` |
| Build or fix a Paid/Fulfillment lane on any marketplace | `references/marketplace-paid-lane.md` |
| Reuse the shared marketplace runtime | `skills/_shared/marketplace-core/scripts/` |
| Sell the same catalogue on a new platform | `skills/gig-work/profile/listings/catalog.json` |
| Lane ownership and parallelism rules | spec §6.2A, `docs/superpowers/specs/2026-08-22-life-manager-gig-economy-loop-design.md` |

## Before writing code

Search `runtime/`, existing recipes, provider adapters and `skills/_shared/`.
Reuse what is there. A new abstraction is prohibited for one speculative
consumer — the second real consumer is the extraction trigger.

## Lane ownership

Apply alone submits applications. Negotiate alone replies to buyer threads.
Storefront alone mutates listings. Paid alone fulfils orders. Effects are
disjoint by construction, so there is no cross-lane lock, shared queue, sibling
wait or effect arbitration. Each owner prevents replay from its own durable
state and reconciles an uncertain result from official state without pausing any
other owner.

## Completion

Completion is official provider readback, never process liveness, never a clean
exit code. A lane that ran and reported success without a receipt has not
completed.
