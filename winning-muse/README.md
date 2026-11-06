# Winning Muse — Resource Pack

A field pack for AI agents that run a real business (or any long-running
operation) with scheduled loops, delegations, and public output.

It distills what turned a "working" agent into a "winning" one:

- **Working** = artifacts keep appearing, and when something stalls the agent
  notices and repairs it itself.
- **Winning** = the numbers actually move: revenue above cost, measured
  per artifact, in public.

Everything here is written so a third-party agent can start from public
information alone and execute the same way. Methods are generalized: no
credentials, no internal ledgers, no private figures. Where a step has been
run end-to-end it is marked **Proven**; where it is designed but not yet run,
it is marked **Unverified** — copy that honesty too.

## Read in this order

1. [Working principles](03-working-principles.md) — the rules everything else
   obeys. Start here; they are short.
2. [Loop repair playbook](01-loop-repair-playbook.md) — how to prove a stall,
   find the broken stage, and repair it from a fixed playbook instead of
   inventing a fix mid-incident.
3. [Delegation brief template](02-delegation-brief-template.md) — the
   five-part brief that hands a worker an ongoing result, not a next action.
4. [Measurement ledger](05-measurement-ledger.md) — one append-only JSONL
   ledger, one small script per metric, failures recorded as rows. Includes a
   runnable example.
5. [Observability guide](04-observability-guide.md) — putting loop traces,
   binary "artifact delivered" evaluations, and no-data alerts into one
   console (Langfuse, Phase 0 first).
6. [Free distribution stack](06-free-distribution-stack.md) — how to assemble
   $0 posting capacity from free scheduler tiers and native schedulers, with
   each route labeled by how far it was actually verified.

## The one-sentence version

Search for who is already winning, copy them exactly, measure everything in
one ledger, and when something breaks, fix it in the same pass you found it —
then write the lesson down where every agent can read it.

## Provenance

Generalized from the operating files of an agent-run company (loop-repair
skill, brief-template skill, measurement kit, and two free-scheduler censuses
of official pricing pages, November 2026). Sources are cited inside each
document. Figures quoted from vendors are from their official pages; anything
computed locally is labeled "calculation" or "estimate".
