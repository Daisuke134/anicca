# VCSDD Phase 1c Spec-Review Verdict — agents-at-arms-leaderboard

- Feature: `agents-at-arms-leaderboard` (lean mode)
- Review scope: `reviews/sprint-1/` (behavioral spec gate)
- Reviewer: fresh-context adversary (disk-only, zero builder context)
- Timestamp: 2026-07-01
- Artifact under judgment: `.vcsdd/features/agents-at-arms-leaderboard/specs/behavioral-spec.md`

## Overall verdict: **FAIL**

All 5 dimensions FAIL. The behavioral spec was authored as if the **existing enforced telemetry
schema/verify pipeline does not exist**. The real `instances` rows are validated by
`telemetry-schema.js` (a hard validator) and the existing aggregate consumes a *different* field
vocabulary than the spec declares. Multiple R-requirements directly contradict code that is already
live, and the no-fake invariant — the entire point of the feature — has no proof.

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | FAIL |
| 2. Edge Cases | FAIL |
| 3. Impl Correctness (testability) | FAIL |
| 4. Structural Integrity | FAIL |
| 5. Verification Readiness | FAIL |

---

## Dimension 1 — Spec Fidelity: FAIL

### FIND-001 (critical) — Default rank metric contradicts the design north star
- Design intent, `docs/.../2026-07-01-agents-at-arms-live-leaderboard-design.md:21-22`:
  *"a leaderboard ranked by what each agent actually **earned** — the agent that **earns the most
  wins**."*
- Behavioral spec `behavioral-spec.md:13-14` (R2): default rank = `net_worth_usd` descending.
- Conflict: `net_worth_usd` = total wallet balance, which is dominated by **seeded capital**, not
  earnings. An agent seeded with USDC that earns $0 outranks an agent that genuinely earned money but
  withdrew it. This inverts "earns the most wins" and undermines INV-NOFAKE's spirit (the *ranked
  figure* should reflect real earning, per design §1). The design itself is internally split (§5 line
  75 says "default by net worth"), but the **north-star §1 is the approved Dais intent** and the
  behavioral spec sided with the wrong one without justification.
- Fix: state explicitly which metric is the ranked figure and reconcile with §1; if net worth is
  intended, amend the design north-star and record the rationale. Do not leave the contradiction
  unresolved.

### FIND-002 (critical) — R6 `Ours` filter defined on a field that has no "hackathon" value
- `behavioral-spec.md:23-26` (R6): *"`Ours` SHALL show only agents whose `funding_type` is not a
  hackathon entrant."*
- `design...:41` (§3): `funding_type` ∈ `{self, human}`. Neither value is "a hackathon entrant."
- Hackathon membership is carried by the **tag** `agent-hackathon` (`design...:52`, and R6's own
  `#agent-hackathon` branch keys off `tags`), NOT by `funding_type`. R6 conflates two orthogonal
  axes, making "Ours" undefinable as written.
- Fix: define `Ours` as agents whose `tags` do **not** include `agent-hackathon` (or an explicit
  owned-instance allowlist), and handle the overlap case (see FIND-006).

---

## Dimension 2 — Edge Cases: FAIL

### FIND-003 (critical) — Undefined-money × sort interaction is unspecified
- R3 (`:15-17`) omits money fields (leaves `undefined`); R2 (`:13-14`) sorts by
  `b.net_worth_usd - a.net_worth_usd`.
- When `net_worth_usd` is `undefined`, `undefined - n === NaN`; `Array.prototype.sort` with a NaN
  comparator yields **implementation-defined ordering**. The spec never says where an agent with no
  on-chain net worth ranks (bottom? excluded? above $0 agents?). This is the most common real case at
  spawn time (a just-registered agent before the enrich step runs) and it is undefined behavior.
- Fix: add an EARS requirement: agents with undefined ranked-metric sort last (and tie-break among
  themselves deterministically), or are placed in a separate "pending on-chain" bucket.

### FIND-004 (major) — Missing/never-set `last_heartbeat` not covered by R4
- R4 (`:18-19`) only addresses heartbeat *"older than"* the window. It is silent on a row that has
  **never** heartbeated (`last_heartbeat` undefined/null) — exactly the spawn-registration case in
  design §4.1. Is that `idle`? `running`? Undefined.
- Fix: specify status when `last_heartbeat` is absent.

### FIND-005 (major) — R4 destroys the `stopped`/terminal distinction
- R4: stale ⇒ `idle` *"regardless of the stored status."* An agent explicitly `stopped`/`dead` that
  also happens to be stale is forcibly relabeled `idle`, hiding the real terminal state. The board
  would show a dead agent as merely idle.
- Fix: exempt terminal statuses from the stale→idle override, or define precedence explicitly.

### FIND-006 (major) — `All`/`#agent-hackathon`/`Ours` are assumed disjoint but can overlap
- Design §1/§4 allow our **own self-funded** agents to also carry `agent-hackathon`. R6 treats
  hackathon vs Ours as a partition. The spec never says how an agent that is both ours AND tagged is
  classified, nor whether the three chips are mutually exclusive filters or independent.
- Fix: define set semantics for the overlap.

---

## Dimension 3 — Impl Correctness / Spec Testability: FAIL

### FIND-007 (critical) — R3 is untestable at the aggregate layer: cannot distinguish self-reported from on-chain
- R3 (`:15-17`) requires omitting a money field when *"not available from an **on-chain source**"*
  and forbids emitting *"a self-reported value."*
- But `dashboard-sync.js:6-14` feeds the aggregate the **raw Supabase `instances` rows**, where
  `net_worth_usd` is a single numeric column. A present number is indistinguishable from a
  self-reported one at this layer — there is no provenance flag in the data model (design §3 has no
  `net_worth_source` column). The aggregate physically cannot enforce "never self-reported."
- The 1b proof for R3 (`:37`) only checks *absent ⇒ undefined*; it does not — and cannot, with this
  data model — prove the "never self-reported" half.
- Fix: add a provenance signal to the data contract (e.g. only the enrich step writes
  `net_worth_usd`, agents write to a separate `net_worth_self_reported`), then R3 becomes testable.

### FIND-008 (major) — R5 does not name the rendering component; two divergent DashboardData types exist
- R5 (`:20-22`) says "the dashboard UI." Design §5 names `EmpireDashboard.tsx`. But
  `EmpireDashboard.tsx:52-56` declares a *local* `DashboardData` of `{mrr, goals}` and reads
  `data.goals.progress_pct` (`:79`), `data.mrr.total_usd` (`:120`) — none of which the aggregate
  emits (`telemetry-aggregate.js:11`). Meanwhile `useDashboard.ts:8-22` declares a *different*
  `DashboardData` with no `agents`/`leaderboard` field at all. R5 does not say which type/component
  gains the leaderboard, so it is not concretely implementable.
- Fix: name the exact component and the exact type to extend.

### FIND-009 (major) — R6 untestable due to FIND-002 (contradictory predicate)
- A test cannot be written for "`funding_type` is not a hackathon entrant" because no `funding_type`
  value denotes a hackathon entrant. Untestable as written.

---

## Dimension 4 — Structural Integrity: FAIL (most severe dimension)

### FIND-010 (critical) — R3 directly violates the existing enforced schema
- `telemetry-schema.js:11`: `if (typeof o.net_worth_usd !== "number" || o.net_worth_usd < 0) return
  {ok:false, reason:"schema"}`. A row with `net_worth_usd` **omitted/undefined** (R3's mandate) is
  **rejected** by the live validator before it can reach Supabase or the aggregate.
- R3 ("leave undefined rather than emit 0") is incompatible with a schema that **requires** the field
  to be a non-negative number. The spec never acknowledges this validator exists.
- Fix: either make the money fields optional in `telemetry-schema.js` (and document the contract
  change) or change R3.

### FIND-011 (critical) — Status vocabulary is a three-way contradiction
- Existing enforced enum, `telemetry-schema.js:15`: `["alive","critical","dead"]`.
- Existing aggregate, `telemetry-aggregate.js:4,6`: keys off `status !== "dead"`.
- Design §3 (`design...:53`): `running | idle | stopped`.
- Behavioral R4 (`:18-19`): sets `idle`.
- `idle`/`running`/`stopped` are **not** accepted by the live schema; a heartbeat with `status:"idle"`
  is rejected at `telemetry-schema.js:15`. The spec picks a vocabulary that the running code forbids
  and never reconciles the three.
- Fix: choose one status vocabulary, update the schema enum + aggregate filters, and state the
  migration.

### FIND-012 (critical) — Field-name mismatches with live code (`agents` vs `leaderboard`, `revenue_mtd_usd` vs `revenue_mo_usd`, `instance_id` vs `id`)
- R1 (`:10-12`) demands a top-level **`agents`** array, but `telemetry-aggregate.js:10-11` already
  emits **`leaderboard`**; the spec never says whether to rename, replace, or add (breaking existing
  consumers/tests `aggregate.test.js:16`).
- R1 lists **`revenue_mtd_usd`**; the live schema/aggregate use **`revenue_mo_usd`**
  (`telemetry-schema.js:12`, `telemetry-aggregate.js:3`). Same concept, different key — unreconciled.
- R1 element key **`instance_id`**; existing leaderboard rows are keyed by **`id`**
  (`aggregate.test.js:16` asserts `d.leaderboard[0].id`; schema validates `o.id` at
  `telemetry-schema.js:5`). Unreconciled.
- Fix: a field-mapping table in the spec reconciling every new name against the existing column/key.

### FIND-013 (major) — R3 omission breaks existing total reducers (NaN)
- `telemetry-aggregate.js:2-3`: `rows.reduce((s, r) => s + r.net_worth_usd, 0)` and `+ r.revenue_mo_usd`.
  If R3 makes any row's money field `undefined`, these reducers yield **`NaN`**, corrupting
  `total_net_worth_usd`/`earned_mo_usd` shown elsewhere on the board. The spec mandates omission but
  never requires guarding the existing sums.
- Fix: require null-safe reducers as part of this slice.

### FIND-014 (major) — Spec ignores the signed-heartbeat/verify layer it depends on
- Design §4.4 anti-spoof = signed heartbeat; this is implemented in `telemetry-verify.js` +
  `telemetry-schema.js`, whose canonical field set (`telemetry-verify.js:10`) is `net_worth_usd,
  revenue_mo_usd, model_tier, ...` — not the spec's `revenue_mtd_usd, revenue_by_source,
  model_current, tags`. Adding the new fields silently changes (or bypasses) the signed canonical
  message. The behavioral spec has **no requirement** governing how new fields interact with
  signature verification. INV-OWN-STATE (`:47`) is asserted but unproven against this layer.
- Fix: add a requirement + test covering the canonical signed message when new columns are added.

---

## Dimension 5 — Verification Readiness: FAIL

### FIND-015 (critical) — The no-fake invariant (the feature's whole point) has no proof
- INV-NOFAKE (`:45-46`): money is on-chain-derived or omitted, *"never a self-reported or fabricated
  number."* The 1b table (`:37`, R3 row) only asserts *absent ⇒ undefined*. **No test** feeds a
  self-reported number and asserts it is rejected/not ranked. Given FIND-007 (no provenance in the
  data model), this invariant is currently unprovable. The single most important guarantee of "Agents
  at Arms" is unverified.
- Fix: add provenance to the contract (FIND-007) and a test asserting a self-reported value never
  becomes the ranked figure.

### FIND-016 (major) — R5/R6 proofs rely on a manual screenshot, not an automated assertion
- 1b table `:39-40`: R5/R6 "browser E2E / CloakBrowser screenshot." A screenshot is a human eyeball
  check, not a regression-proof assertion. The component-test halves are listed but their expected
  DOM contract (which component, which selectors) is undefined because of FIND-008.
- Fix: specify automated component-test assertions (rows in order; filter narrows DOM set) as the
  binding proof; keep the screenshot as supplementary.

### FIND-017 (major) — No proof for the stale/missing-heartbeat and overlap edges
- No 1b row proves FIND-004 (missing heartbeat), FIND-005 (stopped+stale precedence), FIND-006
  (Ours/hackathon overlap), or FIND-003 (undefined-money sort position). Each named edge needs a
  test row.
- Fix: add one test per edge above.

### FIND-018 (major) — No proof that totals survive R3 omission, nor that schema accepts the new shape
- No test covers FIND-013 (NaN totals) or FIND-010/011 (schema accepting omitted money / new status
  enum). The spec asserts a new data shape that the existing validator rejects, with no test pinning
  the validator change.

---

## Must-fix before Phase 2 (RED)
1. FIND-010 + FIND-011 + FIND-012: reconcile the spec's field/status vocabulary against the **live**
   `telemetry-schema.js` / `telemetry-aggregate.js` (mapping table + schema migration). The spec
   currently describes a contract the running code rejects.
2. FIND-007 + FIND-015: add money **provenance** to the data model so INV-NOFAKE is testable; today
   it cannot be proven and the aggregate cannot enforce it.
3. FIND-001 + FIND-002: fix the rank-metric vs "earns most wins" contradiction and redefine `Ours`
   on `tags`, not `funding_type`.
4. FIND-003/004/005/006: specify the undefined-money sort position, missing-heartbeat status,
   stopped-vs-stale precedence, and Ours/hackathon overlap.
5. FIND-008: name the exact rendering component/type (EmpireDashboard reads `mrr/goals` the aggregate
   never emits — pick and reconcile).
6. FIND-013: require null-safe reducers so omission cannot NaN the totals.
