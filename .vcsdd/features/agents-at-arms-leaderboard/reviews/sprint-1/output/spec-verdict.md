# VCSDD Phase 1c Spec-Review Verdict (ROUND 2 / RE-REVIEW) — agents-at-arms-leaderboard

- Feature: `agents-at-arms-leaderboard` (lean mode)
- Review scope: `reviews/sprint-1/` (behavioral spec gate, v2 spec)
- Reviewer: fresh-context adversary (disk-only, zero builder context)
- Round: 2 (re-review of v2 rewrite)
- Timestamp: 2026-07-01
- Artifact under judgment: `.vcsdd/features/agents-at-arms-leaderboard/specs/behavioral-spec.md` (v2)

## Overall verdict: **FAIL**

The v2 rewrite resolved the bulk of round-1 (vocabulary/schema/status reconciliation, rank-by-earnings,
tag-based filter, provenance for net worth). But the rank-by-earnings fix exposed a **deeper hole than
round 1 had**: the figure that decides who "wins" (`revenue_mo_usd`) is **self-reported and never
on-chain-verified**, while the no-fake machinery (R4/INV-NOFAKE) only guards `net_worth_usd`, which is
**not** the ranked field. The spec even contradicts itself on this point. Two dimensions still FAIL on
fidelity/verification, and the signed-message + UI-type plumbing still has structural gaps.

| Dimension | R1 | R2 |
|---|---|---|
| 1. Spec Fidelity | FAIL | **FAIL** |
| 2. Edge Cases | FAIL | **FAIL** |
| 3. Impl Correctness (testability) | FAIL | **FAIL** |
| 4. Structural Integrity | FAIL | **FAIL** |
| 5. Verification Readiness | FAIL | **FAIL** |

---

## Round-1 finding disposition (every must-fix re-checked)

| R1 finding | Status in v2 | Evidence |
|---|---|---|
| FIND-001 (rank metric ≠ earnings) | **RESOLVED-WITH-REGRESSION** | R2 now ranks by `revenue_mo_usd` (`behavioral-spec.md:29-32`) — but see R2-FIND-001/002: the new ranked field is unverified and INV-NOFAKE still names the wrong field. |
| FIND-002 (`Ours` on `funding_type`) | **RESOLVED** | R7 redefines `Ours` on `OUR_INSTANCE_IDS` + `tags`, never `funding_type` (`behavioral-spec.md:51-54`). |
| FIND-003 (undefined-money sort NaN) | **RESOLVED for omission, REOPENED for unverified** | R3 keeps money required (`:33-35`) — no `undefined`. But R4 "shown but unranked" reintroduces an ordering gap (R2-FIND-003). |
| FIND-004 (missing `last_heartbeat`) | **RESOLVED** | v2 derives staleness from schema-required `ts` (`:42-44`); no undefined case at aggregate. |
| FIND-005 (stale destroys terminal status) | **RESOLVED** | R5 "SHALL NOT change `status`", `dead`/`critical` still surfaced (`:42-45`). |
| FIND-006 (filter overlap) | **RESOLVED** | R7 `Ours` = allowlisted AND lacks `agent-hackathon` → disjoint (`:51-54`). |
| FIND-007 (no provenance → R3 untestable) | **RESOLVED for net_worth only** | R4 adds `net_worth_src:"chain"\|"unverified"` (`:36-41`). NOT added for the ranked `revenue_mo_usd` (R2-FIND-001). |
| FIND-008 (no component/type named) | **STILL OPEN** | R6 names `EmpireDashboard.tsx` to render yet tells you to extend `useDashboard.ts`'s type — two different types; the render component uses its own local one (R2-FIND-005). |
| FIND-009 (R6 untestable) | **RESOLVED** | tag-based R7 is testable (`:51-54`, 1b `:70`). |
| FIND-010 (omitted money rejected by schema) | **RESOLVED** | R3 keeps schema unchanged, money required (`:33-35`). |
| FIND-011 (status three-way contradiction) | **RESOLVED** | R5 uses live enum `alive\|critical\|dead`; staleness = derived flag (`:42-45`). |
| FIND-012 (field-name mismatches) | **RESOLVED** | v2 uses `leaderboard`/`id`/`revenue_mo_usd` per live vocabulary (`:11-17, :25-29`). |
| FIND-013 (omission NaNs reducers) | **RESOLVED for omission, REOPENED for unverified** | No omission (`:33-35`); but whether unverified rows feed `total_net_worth_usd` is unspecified (R2-FIND-003). |
| FIND-014 (ignores signed-heartbeat/verify) | **STILL OPEN** | INV-OWN-STATE is named (`:77-78`) but no requirement extends `canonicalMessage()` for the new signed fields (R2-FIND-004). |
| FIND-015 (no-fake invariant unproven) | **RESOLVED for net_worth, OPEN for the ranked field** | 1b R4 proves chain enrichment of net worth (`:67`). The ranked `revenue_mo_usd` has no on-chain proof (R2-FIND-001). |
| FIND-016 (proof = screenshot only) | **RESOLVED** | 1b adds component-test assertions for R6/R7/R8 (`:69-71`); screenshot now supplementary. |
| FIND-017 (edges unproven) | **MOSTLY RESOLVED** | R5 stale + R7 filter proofs added (`:68,70`); unranked-ordering edge still unproven (R2-FIND-003). |
| FIND-018 (totals/schema-shape unproven) | **RESOLVED for back-compat, OPEN for new-field validation** | R9 proves existing rows still pass (`:72`); no proof the new optional fields are type-validated (R2-FIND-007). |

---

## Dimension 1 — Spec Fidelity: FAIL

### R2-FIND-001 (critical) — The RANKED figure (`revenue_mo_usd`) is self-reported and never on-chain-verified
- North star, `design...:20-21`: *"a leaderboard ranked by what each agent actually earned — the agent
  that earns the most wins"* — and `design...:64-66` (§4.3): revenue *"computes `revenue_today/mtd`
  from the **on-chain realized-earn ledger** … Self-reported numbers are display-only labels, never the
  ranked figure."*
- v2 R2 (`behavioral-spec.md:29`) ranks by `revenue_mo_usd`. v2 R4 (`:36-41`) only enriches
  **`net_worth_usd`** from chain balance; it says **nothing** about deriving `revenue_mo_usd` from an
  on-chain ledger. `revenue_mo_usd` is written by the agent's own heartbeat (`telemetry-schema.js:12`
  validates it as any number; it is signed by the agent but **asserted by the agent**).
- Consequence: an agent can set `revenue_mo_usd` to any value and **win the leaderboard** — exactly the
  "fake" the feature exists to prevent. The no-fake guarantee (R4) is applied to a field
  (`net_worth_usd`) that is **not** the ranked figure. This is a direct violation of the design's
  explicit "never the ranked figure" rule.
- Fix: add a requirement (and 1b proof) that the **ranked** metric is computed from the on-chain
  realized-earn ledger (per design §4.3), or that an unverifiable earnings figure is excluded/flagged
  the same way R4 handles net worth.

### R2-FIND-002 (critical) — INV-NOFAKE contradicts R2 about which field is ranked
- INV-NOFAKE, `behavioral-spec.md:75`: *"the **ranked money (`net_worth_usd`)** is the on-chain
  balance of `id`"* — then `:76` immediately says *"Earnings rank = `revenue_mo_usd`."*
- R2 (`:29`) ranks by `revenue_mo_usd`, not `net_worth_usd`. The invariant therefore mislabels the
  non-ranked field as "the ranked money," and the protection it specifies is aimed at the wrong column.
  A reader/implementer cannot tell which figure the no-fake guarantee must bind to.
- Fix: rewrite INV-NOFAKE so the on-chain guarantee binds to the actually-ranked metric.

### R2-FIND-008 (major) — On-chain net worth ignores the Solana wallet the design counts
- `design...:46` net worth = *"sum of wallet balances"* over `wallet_evm` **and** `wallet_sol`
  (`design...:44`). v2 R4 (`:36-38`) reads only *"the on-chain USDC+native balance of `id`"* — `id` is
  the EVM address only (`telemetry-schema.js:5`). Solana holdings are silently dropped, understating net
  worth for any agent holding value on Solana. The spec does not acknowledge dropping `wallet_sol`.
- Fix: either state Solana is out of scope for this slice (and why) or include it.

---

## Dimension 2 — Edge Cases: FAIL

### R2-FIND-003 (critical) — "Shown but unranked" is undefined ordering + undefined total inclusion
- R4 (`:39-40`): a chain-read failure ⇒ `net_worth_src:"unverified"` and *"excluded from ranking
  (shown but unranked)."* The spec never says **where** an unranked element sits in the single
  `leaderboard` array (top? bottom? interleaved?), nor whether a stable second list exists. Since the UI
  renders elements *"in order"* (R6, `:46`), undefined order = nondeterministic render.
- It also never says whether an unverified row's (still schema-required) `net_worth_usd` is **included
  in `total_net_worth_usd`** (`telemetry-aggregate.js:2`). If included, the headline total contains
  exactly the unverified/fake money the feature forbids; if the field is nulled to exclude it, the
  existing reducer yields `NaN` (the round-1 FIND-013 failure mode, reintroduced).
- Fix: define the array position of unranked rows deterministically and state whether unverified net
  worth is included in `total_net_worth_usd` (with a null-safe reducer either way).

---

## Dimension 3 — Impl Correctness / Testability: FAIL

### R2-FIND-005 (major) — R6 names a render component and a type that are NOT the same object
- R6 (`:46-50`): *"`EmpireDashboard.tsx` SHALL render one row per `leaderboard` element … `useDashboard.ts`
  `DashboardData` type SHALL gain an optional `leaderboard?` array."*
- But `EmpireDashboard.tsx` does **not** use the `useDashboard` hook or its type. It declares its **own
  local** `interface DashboardData { updated_at; mrr; goals }` (`EmpireDashboard.tsx:52-56`) and fetches
  `/dashboard.json` itself (`:64-76`), reading `data.mrr.total_usd` (`:120`) and `data.goals.progress_pct`
  (`:79`). Extending `useDashboard.ts`'s type (`useDashboard.ts:8-22`) does **nothing** for
  `EmpireDashboard.tsx`. The spec leaves it ambiguous which type carries `leaderboard` and whether
  `EmpireDashboard` must be refactored onto the hook — so R6 is not concretely implementable as written.
- Compounding: `EmpireDashboard`'s local type reads `mrr`/`goals`, which `telemetry-aggregate.js:11`
  does **not** emit. The spec adds a leaderboard to a component whose existing data contract already
  diverges from the aggregate, without reconciling that contract.
- Fix: name the single type to extend and the single component that consumes it; reconcile the
  `mrr/goals` vs aggregate-output mismatch.

---

## Dimension 4 — Structural Integrity: FAIL

### R2-FIND-004 (critical) — The signed canonical message is never extended for the new fields
- New additive fields (`revenue_today_usd, revenue_by_source, tags, log_feed`, and R4's `net_worth_src`)
  must be in the **signed `message`** to be both authenticated and persisted: `telemetry.js:29` upserts
  `v.payload`, which is the parsed signed message (`telemetry-verify.js:21,29`). The documented client
  signer `canonicalMessage()` (`telemetry-verify.js:7-13`) serializes a **fixed** field set that
  **excludes** all new fields. The spec has **no requirement** to extend it.
- Consequences: (a) a canonical client never emits `tags` → they are never on the row → R1's
  *"when present on the row"* passthrough and R7's `#agent-hackathon`/`Ours` classification have **no
  data source** through the signed path; or (b) if `tags` are bolted on outside the canonical message,
  they are **unsigned** — and `tags` drive a security-relevant categorization (who is "Ours"). INV-OWN-STATE
  (`:77-78`) asserts signer==id but says nothing about which fields the signature must cover.
- Fix: add a requirement (+1b proof) that `canonicalMessage()` is extended to cover the new
  signed/persisted fields, and that classification-driving fields (`tags`) are inside the signed payload.

### R2-FIND-006 (major) — `net_worth_src` has no home in the element schema or the UI
- R4 (`:38`) introduces `net_worth_src`, but the R1 element field enumeration (`:25-28`) does **not**
  list it, and R6's UI render list (`:46-48`) shows `status` + `stale` but **not** the verified/unverified
  source. So the "flagged, never silently trusted" outcome (R4, `:41`) has no requirement that surfaces
  it to a viewer, and an unranked row is visually indistinguishable from a ranked one.
- Fix: add `net_worth_src` to the element field set (R1) and to the UI render contract (R6).

### R2-FIND-007 (major) — New optional fields are type-unvalidated; `tags` feeds the filter unchecked
- `telemetry-schema.js:3-16` validates only the fixed field set and ignores unknown keys. The additive
  fields (`tags`, `revenue_by_source`, `log_feed`) are therefore **never type-checked**. R9
  (`:57-58`, 1b `:72`) only proves *existing* rows still pass — it imposes no validation on the new
  shapes. A malformed `tags` (e.g. a string instead of `string[]`, or `[123]`) passes validation and is
  consumed by R7's `tags.includes("agent-hackathon")` and the `Ours` logic, which can throw or
  misclassify.
- Fix: require the validator to type-check the additive fields when present (`tags` is `string[]`,
  `revenue_by_source` is an object, `log_feed` is `{ts,line}[]`), with a 1b proof.

### R2-FIND-009 (minor) — `OUR_INSTANCE_IDS` allowlist is referenced but unlocated/unspecified
- R7 (`:53`) keys `Ours` on a *"known-canonical allowlist (`OUR_INSTANCE_IDS`)"* but never says where it
  lives, who maintains it, or its format — so the `Ours` filter is not concretely testable or
  implementable without inventing that contract.
- Fix: specify the allowlist's source/location and shape.

---

## Dimension 5 — Verification Readiness: FAIL

### R2-FIND-010 (critical) — No proof binds the no-fake guarantee to the field that decides winning
- 1b R4 (`:67`) proves chain enrichment of `net_worth_usd` only. There is **no 1b row** that feeds an
  inflated `revenue_mo_usd` and asserts it does not become the top of the leaderboard. Since R2 ranks by
  `revenue_mo_usd`, the single most important guarantee ("earns the most wins — no fake") is **unproven**
  for the figure that actually determines the ranking (see R2-FIND-001).
- Fix: add a 1b proof that a fabricated earnings figure cannot win the board.

### R2-FIND-011 (major) — Signature/new-field interaction and new-field validation are unproven
- No 1b row covers R2-FIND-004 (new fields inside the signed canonical message) or R2-FIND-007
  (validation of `tags`/`revenue_by_source`/`log_feed`). The `Ours`/`#agent-hackathon` classification —
  a security boundary — rests on data whose authenticity and well-formedness are untested.
- Also unproven: R2-FIND-003 (deterministic placement of unranked rows; inclusion of unverified net
  worth in `total_net_worth_usd`).
- Fix: add one 1b row per gap above.

---

## Must-fix before Phase 2 (RED)
1. **R2-FIND-001 + R2-FIND-002 + R2-FIND-010**: bind the no-fake guarantee to the **ranked** metric
   (`revenue_mo_usd` from the on-chain earn ledger, per design §4.3), fix the INV-NOFAKE mislabel, and
   add a proof that fabricated earnings cannot win. This is the feature's entire point and is currently
   unguarded.
2. **R2-FIND-004 + R2-FIND-006 + R2-FIND-007 + R2-FIND-011**: extend `canonicalMessage()` for the new
   signed/persisted fields, place `net_worth_src` in the element + UI contracts, type-validate the
   additive fields, and prove all three.
3. **R2-FIND-005**: name the single component **and** the single `DashboardData` type that carries
   `leaderboard`; reconcile `EmpireDashboard`'s `mrr/goals` contract with the aggregate output.
4. **R2-FIND-003**: define deterministic ordering for unranked rows and whether unverified net worth is
   included in `total_net_worth_usd` (null-safe reducer either way).
5. **R2-FIND-008 + R2-FIND-009**: state Solana scope for net worth; specify the `OUR_INSTANCE_IDS`
   allowlist source/shape.
</content>
</invoke>
