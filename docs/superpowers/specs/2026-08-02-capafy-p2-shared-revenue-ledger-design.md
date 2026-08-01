# Capafy P2 Shared Revenue Ledger Design

**Date:** 2026-08-02  
**Status:** Approved by the existing Capafy living-spec contract and the standing no-human-in-the-loop execution instruction  
**Parent spec:** [`2026-08-01-capafy-self-improving-revenue-loop-design.md`](2026-08-01-capafy-self-improving-revenue-loop-design.md)

## 1. Outcome

P2 creates one append-only Capafy revenue event ledger that becomes the source for both the natural-language Telegram projection and the public company dashboard. Existing operational ledgers and terminal files remain source evidence; they are not deleted or silently reinterpreted. Every public claim can be traced to a canonical event and then to its source evidence.

P2 is complete only when Builder, Marketer, account lifecycle, sales/payout reconciliation, cost measurement, and incident repair all write idempotent canonical events, and a production Telegram report and deployed dashboard show the same projection identifier and business values.

## 2. Chosen architecture

### 2.1 Why a dedicated Capafy ledger

Three approaches were considered:

1. **Dedicated Capafy JSONL ledger — selected.** It satisfies the approved append-only and open-source requirements, is human-readable, works with the existing Python/Bash runtime, and can preserve source ledgers unchanged.
2. **Reuse the generic OpenClaw event stream.** Rejected because the current generic rows do not enforce Capafy money dimensions, entity identity, evidence URLs, or incident correlation.
3. **Move canonical state to SQLite.** Rejected for P2 because it adds migration, deployment, and inspection complexity without a current scale or query requirement that JSONL cannot meet.

The canonical public-safe event stream is:

```text
~/.openclaw/state/capafy-revenue-events.jsonl
```

Private technical evidence is stored separately:

```text
~/.openclaw/state/capafy-revenue-evidence/<event_id>.json
```

Technical sidecars are mode `0600`, may contain local paths and diagnostic details, and are never copied into the Netlify site. Canonical events contain only public-safe URLs, non-secret evidence labels, and a sidecar reference identifier.

### 2.2 Component boundaries

```text
Builder terminal ──────────────┐
Marketer/account terminal ─────┤
Sales + payout reconcile ──────┤
Cost measurement ──────────────┼─> capafy_event_store.py
Incident transitions ──────────┤        |
Backfill/current-state sync ────┘        v
                              capafy-revenue-events.jsonl
                                           |
                                  capafy_event_projection.py
                                     /                 \
                                    v                   v
                         Telegram renderer       company/state.json
                                                     + index.html
```

- `capafy_event_store.py` owns schema validation, deterministic identifiers, locked append, conflict detection, sidecar writes, and ledger reads. It makes no business or creative judgments.
- `capafy_event_bridge.py` translates already-verified producer outcomes into canonical events. Translation is deterministic because the producer has already established the business observable.
- `capafy_event_projection.py` folds events into current company state and a stable `projection_id`. It performs bookkeeping and money arithmetic only.
- `build_company_dashboard.py` renders a dependency-free, public-safe HTML/JSON projection. It never reads private sidecars.
- Existing agents continue to choose products, positioning, and creative actions. P2 does not add keyword, regex, or if/else business judgment.

## 3. Canonical event contract

Each JSONL row is one object with these exact top-level fields:

```json
{
  "schema_version": 1,
  "event_id": "capafy:content.published:instagram:DbgsvEbo5kd",
  "event_type": "content.published",
  "occurred_at": "2026-08-01T20:32:53Z",
  "recorded_at": "2026-08-01T20:32:54Z",
  "loop": "marketer",
  "entity": {"type": "content", "id": "instagram:DbgsvEbo5kd"},
  "correlation_id": "capafy-marketer-20260801T164641Z-4e195cd6",
  "summary": "Published and owner-verified an Instagram Reel for Decision Debate.",
  "status": {"before": "publish_probe_ready", "after": "reach_observing"},
  "money": {
    "currency": "USD",
    "gross_delta": "0.00",
    "pending_delta": "0.00",
    "realized_delta": "0.00",
    "mrr_delta": "0.00",
    "cost_delta": "0.00",
    "contribution_delta": "0.00"
  },
  "metrics": {},
  "public_evidence": {
    "urls": [
      "https://www.instagram.com/reel/DbgsvEbo5kd/",
      "https://capafy.ai/agent/4866150011"
    ],
    "labels": ["post-write owner session verified"]
  },
  "technical_evidence_ref": "capafy:content.published:instagram:DbgsvEbo5kd",
  "source": {
    "producer": "capafy-marketing-handoff",
    "source_id": "marketing-published:DbgsvEbo5kd",
    "source_digest": "sha256:<hex>"
  },
  "next": {"owner": "marketer", "retry_at": null}
}
```

Required event types in P2 are the parent spec's canonical set. P2 production wiring must cover at least:

- `listing.submitted` and `listing.approved` from Builder evidence;
- `content.published` and `content.measured` from Marketer evidence;
- `account.created`, `account.session_ready`, `account.publish_probe_ready`, and `account.post_verified` from account lifecycle evidence;
- `order.received`, `payout.received`, and `cost.measured` from reconciled money sources;
- `balance.reconciled` for pending/confirmed seller-balance changes that are not bank payouts;
- `incident.detected`, `incident.repair_started`, `incident.repaired`, `incident.verified`, and `incident.unresolved` from the incident state machine.

All six money deltas are decimal strings with two fractional digits. Missing money is `"0.00"`, never `null`. `order.received` changes gross but contributes `"0.00"` until settlement; `balance.reconciled` changes pending but not contribution; `payout.received` changes realized and contribution by the positive bank-payout delta; `cost.measured` changes cost and contribution by equal opposite amounts; refunds reverse the appropriate recognized dimensions. Lifetime contribution is calculated by the projection and is never copied from prose. `metrics` contains non-negative integers and is empty for events without a measurement; metric snapshots are folded by entity and observation time rather than summed repeatedly.

## 4. Idempotency and durability

`event_id` is derived from the immutable business observable, not from wall-clock execution. Examples:

- `capafy:listing.submitted:<agent_id>:<remote_version>`
- `capafy:content.published:instagram:<reel_shortcode>`
- `capafy:order.received:2026-06-23:daily-aggregate` when Capafy exposes only a daily aggregate rather than order identifiers
- `capafy:cost.measured:<provider>:<source_record_identity>`
- `capafy:incident.verified:<incident_id>`

The store obtains an exclusive file lock, scans existing identifiers, and then applies one of three outcomes:

1. new identifier and valid event: append one compact JSON line, flush, and `fsync`;
2. identical identifier and identical canonical payload: return `appended=false` with success;
3. identical identifier and different payload: return an explicit conflict and write nothing.

If a technical sidecar is supplied, it is written atomically at mode `0600` before the event append. A failed event append cannot create a public claim. A sidecar without a canonical event is safe orphan evidence and may be reused on retry.

## 5. Producer integration

Producer wiring occurs only after the producer's existing verification gate:

- Builder emits after remote status, skill confirmation, and config confirmation pass.
- Marketer emits after one new Reel URL and post-write owner-session verification pass.
- Account manager emits only after independent owner-session verification and records lifecycle transitions separately.
- Sales reconciliation emits one `order.received` event per immutable sales row, `balance.reconciled` for pending-balance deltas, and `payout.received` only for a positive increase in realized payout.
- Cost reconciliation emits `cost.measured` from immutable provider usage records, not from a mutable prose total.
- Incident transitions emit the exact phase written by `capafy_outcome.py`; phase retries reuse the same phase event identifier and conflict if evidence changes silently.

Every writer is allowed to retry indefinitely. Duplicate execution must not create duplicate revenue, cost, content, Telegram, or incident events.

## 6. Projection and user experience

The fold produces one `company_state` object containing:

- inventory by status and latest verified Builder URL;
- account lifecycle, owner-session proof, public Reel, and reach state;
- orders, gross, pending, realized, MRR, cost, contribution, and currency;
- active incident summary or `null`;
- latest content metrics and experiment identifiers;
- `as_of`, `last_event_id`, and `projection_id`.

`projection_id` is the SHA-256 digest of the ordered canonical event identifiers and canonical projection payload. Telegram and the dashboard must show the same short identifier. A dashboard generated from a different ledger revision is visibly stale rather than silently contradictory.

Telegram remains concise natural language. It does not dump raw JSON or local file paths. The daily message includes the real listing/Reel/dashboard links, separated money dimensions, active repair state, and the projection identifier.

The public dashboard is deployed under:

```text
https://capafy-skills-daily.netlify.app/company/
```

Its `state.json` contains only the public-safe projection. The existing product landing page and `/go/<agent_id>` attribution route remain unchanged.

## 7. Backfill and migration

The first production sync reads, without deleting or rewriting:

- Builder and Marketer terminal envelopes;
- account lifecycle and account registry state;
- Capafy sales/payout ledger;
- immutable provider usage records;
- attribution and Instagram metric ledgers;
- every incident JSON record.

It emits canonical events with source digests. Running the same backfill twice must append zero rows on the second run. Deployment-verification clicks are represented as technical verification evidence and excluded from organic `content.measured` totals.

The old goal monitor is migrated only after the backfilled projection matches its independently derived values. During migration, a parity command compares every money, inventory, account, content, and incident field and refuses the switch on mismatch.

## 8. Failure handling and self-healing

- Invalid producer data fails closed and starts/resumes an incident; no Telegram success or dashboard mutation follows.
- Event conflicts are incidents because they indicate two different claims for one business observable.
- A corrupt JSONL tail is quarantined as technical evidence; valid prior lines remain readable and the writer refuses to append until repair verifies the tail.
- Dashboard deployment failure does not change the ledger. The dashboard remains visibly stale through its `projection_id`, and the repair owner retries generation/deployment.
- Telegram failure leaves the canonical event intact. The existing exactly-once terminal recovery retries delivery from that event without repeating the business mutation.
- Repair completion is an `incident.verified` event only after the original business observable is re-read.

## 9. Verification strategy

P2 requires all of the following evidence:

1. schema tests reject missing identity, unsafe URLs, invalid money precision, unsupported event types, and secret/local-path leakage;
2. append tests prove new, duplicate-identical, duplicate-conflict, concurrent, truncated-tail, and sidecar-mode behavior;
3. bridge tests cover Builder, Marketer, account, sales, payout, cost, metrics, and every incident phase;
4. projection tests prove monetary separation, no double-counting, deterministic `projection_id`, active-incident folding, and public-safe output;
5. Telegram/dashboard parity tests render the same fixture projection and compare every asserted business value and link;
6. backfill tests prove the second pass appends zero rows;
7. production backfill and direct producer probes create traceable events without resending Telegram or repeating a Reel/listing mutation;
8. deployed `/company/` and `/company/state.json` return HTTP 200 with the same `projection_id` as the local ledger;
9. a seeded writer failure enters repair and closes only after the original append and projection are verified;
10. all P0/P1 regression suites remain green.

## 10. P2 non-goals

- P2 does not choose the next niche, price, product, hook, or creative; P5 owns evidence-driven agent judgment.
- P2 does not retire products or change portfolio allocation; P3 owns that behavior.
- P2 does not add new marketplaces, billing, or tenant credentials; P6 and P7 own those concerns.
- P2 does not replace source evidence ledgers or fabricate historical per-order identifiers that Capafy never exposed.
