# Building a Paid/Fulfillment lane on a marketplace

This recipe is the shared business lifecycle. Keep provider URLs, DOM selectors,
authentication, state labels and mutations in a thin provider adapter. Do not
copy Coconala's `paid_direct.py` when adding Lancers, CrowdWorks or Fiverr.

## One wake

1. Read the provider's complete active-order inventory, including every page.
2. Normalize each order into a durable work item with provider, order ID,
   buyer, deadline, latest-message identity and official observation receipt.
3. Run different orders concurrently. One slow or failed order must not prevent
   another order from being observed, repaired or answered.
4. Reconcile prior intents from official state before creating a new effect.
5. Compile cumulative buyer requirements and attachments, then choose exactly
   one outcome: fulfil, answer, wait for buyer, no-op, cancel, or an explicit
   resumable blocker.
6. For fulfilment, build in the order workspace, independently review the real
   artifact, freeze its hash and buyer-visible message, then authorize an effect.
7. Immediately before any mutation, read the same order again. A newer buyer
   message invalidates the intent and returns the item to decision.
8. Mutate through the provider adapter and read the result back in the same
   authenticated session. Persist the receipt before optional work.

Every inventory item remains represented in the result. Capacity limits defer
items; they never make items disappear.

## Ownership and parallelism

Lane ownership follows spec §6.2A. Within Paid, different orders use
project-scoped claims and progress in parallel; only the same order/effect
identity is serialized. A browser identity lease may briefly serialize one
authenticated session without turning an unrelated client into `failed`.

Reuse the provider-independent primitives that already exist for model routing,
effect fencing, receipts and recovery. In particular:

- a busy Codex profile fails over before spending a task timeout;
- every model invocation gets a private runtime home and lock while reusing only
  immutable authentication inputs, so unrelated loops and client orders never
  serialize on one provider lock;
- configured fallback provider/model pairs must all be allowed by the recipe;
- an effect owner receives non-interactive mutation capability, while decisions
  remain read-only;
- retry is allowed only when official state proves the effect did not happen.

After a click timeout, crash or lost acknowledgement, record `reconcile_unknown`.
The next wake performs read-only official reconciliation: adopt an existing
matching effect with effect count zero, retry only after authoritative absence,
or remain pending when neither can be proved.

A blocked outcome is explicit resumable state, not a failed or forgotten order.
Persist a nonempty blocker string, `remaining_work` as a nonempty string array,
and official wait receipts. The parent reports the order as pending and the next
wake revalidates it while other orders continue normally. Use
`remaining_work=[]` only after both required effect and output have official
readback.

## Provider adapter contract

An adapter owns only:

- authenticated active-order inventory and pagination;
- stable order, message, revision and transaction identities;
- attachment download and official-state normalization;
- answer, artifact-delivery and cancellation mutations supported by that provider;
- same-session official readback for each mutation.

Each receipt binds provider, action, effect key, order ID, buyer-visible payload
hash, artifact hash when applicable, authoritative state, observed time and
evidence hash. A process exit, model assertion or click is not a receipt.

## Delivery and cancellation safety

Formal delivery is a distinct provider effect, never an alias for a normal
message. Its policy is platform-specific. On Coconala it remains off unless an
explicitly authorized formal-delivery contract says otherwise; a progress reply
must prove the checkbox was false before and after send.

A buyer-requested cancellation is also a distinct provider effect. It requires a
code-owned adapter, an exact current-buyer-request readback, a truthful visible
reason, and post-send official state. Re-running a matching cancellation request
must produce effect count zero. Never replace cancellation with a polite message
that leaves the transaction open.

Keep seller delivery, buyer acceptance, transaction completion, payment settled
and payout/banked as separate states. Paid work is not revenue until the relevant
official money receipt exists.

## Current proven implementation

Coconala currently supplies the production evidence for this recipe:

- `skills/earn/gig/scripts/paid_direct.py` — order orchestration and per-order workers;
- `skills/earn/gig/scripts/coconala_queue_snapshot.py` — inventory and talkroom readback;
- `skills/earn/gig/scripts/coconala_paid_progress_browser.py` — normal reply with formal delivery off;
- `runtime/agent-runner/agent_runner.py` — shared model routing and fallback.

`paid_direct.py` is still a Coconala-specific orchestrator; the repository does
not yet have a provider-neutral Paid entrypoint. A second real Paid platform is
the extraction trigger: reuse the recipe and existing shared primitives, measure
its adapter, then move only proven duplicate orchestration into
`skills/_shared/marketplace-core/`. Do not claim production support until a real
active order has an official readback receipt and a second run proves replay
count zero.
