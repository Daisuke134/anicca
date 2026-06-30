# VCSDD Phase 1c Spec-Review Verdict (ROUND 3 / RE-REVIEW) — agents-at-arms-leaderboard

- Feature: `agents-at-arms-leaderboard` (lean mode)
- Review scope: `reviews/sprint-1/` (behavioral spec gate, v3 spec)
- Reviewer: fresh-context adversary (disk-only, zero builder context)
- Round: 3 (re-review of the v3 rewrite)
- Timestamp: 2026-07-01
- Artifact under judgment: `.vcsdd/features/agents-at-arms-leaderboard/specs/behavioral-spec.md` (v3)

## Overall verdict: **FAIL**

v3 made real progress — it correctly binds the rank to an on-chain enrich step, fixes the INV-NOFAKE
mislabel, defines deterministic unverified ordering + NaN-free totals, extends the signed
`canonicalMessage`, places `net_worth_src` in the element + UI, and scopes Solana out. Five round-2
findings are genuinely resolved. **But the two deepest issues survive the rewrite, and the disk proves
it:**

1. The ranked figure's on-chain source is **redefined to raw wallet inflows**, which is **fakeable by
   self-transfer/seed** and **diverges from the design's earn-ledger** — so the no-fake guarantee is now
   attached to the right field but reads a gameable value (R3-FIND-001).
2. The `/dashboard.json` `EmpireDashboard.tsx` actually fetches is a **static Dais-owned file with no
   `leaderboard`** (`apps/landing/public/dashboard.json`), while the aggregate's `leaderboard` lives in a
   **separate Supabase-backed netlify function** with no rewrite — so R6's leaderboard never reaches the
   UI (R3-FIND-002).

| Dimension | R1 | R2 | R3 |
|---|---|---|---|
| 1. Spec Fidelity | FAIL | FAIL | **FAIL** |
| 2. Edge Cases | FAIL | FAIL | **FAIL** |
| 3. Impl Correctness (testability) | FAIL | FAIL | **FAIL** |
| 4. Structural Integrity | FAIL | FAIL | **FAIL** |
| 5. Verification Readiness | FAIL | FAIL | **FAIL** |

---

## Round-2 must-fix disposition (every item re-checked against disk)

| R2 finding | Status in v3 | Evidence |
|---|---|---|
| R2-FIND-001/010 (no-fake binds to ranked revenue) | **PARTIAL — structurally bound, semantically hollow** | R3 now enriches `revenue_mo_usd` from chain (`behavioral-spec.md:36-42`) and INV-NOFAKE names the ranked metric (`:88-90`). But the chain source = "realized inflows to id", which is self-fundable and diverges from design's earn-ledger (`design...:64-66`). See R3-FIND-001/006. |
| R2-FIND-002 (INV-NOFAKE mislabel) | **RESOLVED** | INV-NOFAKE now binds to `revenue_mo_usd` AND `net_worth_usd` correctly (`behavioral-spec.md:88-90`). |
| R2-FIND-003 (unverified order + total inclusion + NaN) | **RESOLVED** | R2 appends unverified by `id` asc, never out-ranking verified (`:32-35`); R4 totals exclude unverified and "Reducers SHALL never operate on a flagged/undefined figure" (`:43-45`). |
| R2-FIND-004 (extend signed `canonicalMessage`) | **RESOLVED** | R10 extends `canonicalMessage()` + `validate()` (`:63-66`). Soundness confirmed: `telemetry-verify.js:17-29` recovers the signer from the **verbatim** message and `validate()` parses those same bytes, so any `tags` present on a persisted row were signed by `id`; `signer==id` is enforced (`:28`) and replay/tamper are closed (`:23-27`). No cross-agent tag spoof. (Caveat: "not spoofable" overstates — any agent may self-assign `agent-hackathon`; acceptable for a self-declared display filter, non-blocking.) |
| R2-FIND-005 (single render component + type) | **PARTIAL** | v3 correctly single-owns `EmpireDashboard.tsx` + its local `DashboardData` (`:49-53`), matching `EmpireDashboard.tsx:52-56,64-76`. But the compounding sub-point — the `mrr/goals` vs aggregate-output mismatch / which `/dashboard.json` carries `leaderboard` — is **still unreconciled** (R3-FIND-002). |
| R2-FIND-006 (`net_worth_src` in element + UI) | **RESOLVED** | R1 lists `net_worth_src`/`earn_src` (`:31`); R6 renders a `net_worth_src` indicator (`:52`). (Gap: `earn_src` not surfaced — folded into R3-FIND-005.) |
| R2-FIND-007 (type-validate additive fields) | **PARTIAL** | R9/R10 require type-checks for `tags`/`revenue_today_usd`/`log_feed` (`:60-62`) with a 1b proof (`:84`), but **omit `revenue_by_source`** (R3-FIND-005). |
| R2-FIND-008 (Solana scope) | **RESOLVED** | Scope note states `wallet_sol` OUT OF SCOPE, EVM `id` only, with a named follow-up (`:68-70`). |
| R2-FIND-009 (`OUR_INSTANCE_IDS` source/shape) | **PARTIAL** | Shape given ("checked-in `string[]` of 0x ids", `:56`), but **file location/owner still unspecified**; `grep` confirms `OUR_INSTANCE_IDS` exists nowhere in code yet. Minor. |
| R2-FIND-011 (proofs for the above) | **PARTIAL** | New 1b rows added for R2/R9/R10 (`:77,84,85`). Still missing: proof that fabricated EARNED money can't win, and proof the served `/dashboard.json` actually carries the leaderboard (R3-FIND-006). |

---

## Dimension 1 — Spec Fidelity: FAIL

### R3-FIND-001 (critical) — Ranked revenue = "raw inflows" is gameable + diverges from design
- v3 R3 (`behavioral-spec.md:38-39`) defines `revenue_mo_usd`/`revenue_today_usd` as *"realized inflows to
  `id` over the month / since 00:00 UTC."* Design (`design...:64-66`) instead says compute *"from the
  on-chain realized-earn **ledger** (INV-7 rows from the earn skeleton)"* and *"Self-reported numbers …
  never the ranked figure."*
- Raw inflows ⊋ earn-ledger rows: they include (a) the design's own test agent's seed (`design...:98`
  *"seeded a few USDC"*) and (b) USDC an attacker cycles in from a second wallet. Since `revenue_mo_usd`
  is THE ranked field (`:32-34`), rank #1 is buyable with your own money. INV-NOFAKE (`:88-90`) is bound
  to the right field but reads a fabricable value.
- **Fix**: define revenue as earn-ledger reads (exclude seed/self/own-address transfers), name the
  ledger interface + network + token set, and prove a self-transfer cannot raise rank.

### R3-FIND-002 (critical) — The leaderboard never reaches the `/dashboard.json` the UI reads
- R6 says `EmpireDashboard.tsx` reads `leaderboard` via *"its existing `/dashboard.json` fetch"*
  (`:53`). The real `apps/landing/public/dashboard.json` is a **static** file shaped
  `{updated_at, mrr, followers, views, spend, goals, basic_income, socials, lineage, …}` — **no
  `leaderboard`, no `total_net_worth_usd`** (`apps/landing/public/dashboard.json:1-8,186-190`).
- The aggregate's `leaderboard` is produced only by `dashboard-sync.js:14` (`return … aggregate(rows)`
  from the Supabase `instances` table) at the **function endpoint**; no netlify rewrite maps
  `/dashboard.json` → that function (`grep`: none). Extending `EmpireDashboard`'s local type with
  `leaderboard?` adds a field the fetched file never contains.
- **Fix**: name the single producer that injects the enriched `leaderboard` into the exact
  `/dashboard.json` the UI fetches and reconcile the two data sources (Supabase `instances` vs the
  Dais-owned instance-state render).

---

## Dimension 2 — Edge Cases: FAIL

### R3-FIND-003 (major) — All-unverified headline + unconstrained `revenue_today_usd`
- All-unverified state (reader fully down): R4 (`:43-45`) makes `total_net_worth_usd`/`earned_mo_usd`
  sum to **0**, so the headline shows a literal `$0` while rows display flagged numbers — the
  "never render `$0`" intent of R8 (`:58`) is not applied to the totals; spectators read "$0 earned"
  instead of "nothing verified yet". Undefined in the spec.
- `revenue_today_usd` has **no sign/relational constraint** (R9 only requires "number", `:62`), unlike
  `net_worth_usd ≥ 0` (`telemetry-schema.js:11`); a negative value or `today > mtd` passes.
- **Fix**: define the all-unverified headline (`—`, not `$0`) and add `revenue_today_usd ≥ 0` +
  `today ≤ mtd` invariants with proofs.

---

## Dimension 3 — Impl Correctness / Testability: FAIL

### R3-FIND-004 (major) — `reader` interface is undefined → R3 mock is non-deterministic
- The no-fake core is `enrichOnChain(rows, reader)` (`:22-23`) and R3's proof is *"unit (mock `reader`)"*
  (`:78`), but the spec never defines the `reader` contract: method names, return shapes
  (number vs `{amount,from,token,ts}[]`), network/RPC, or failure signalling (throw vs null → maps to
  `*_src='unverified'`). A mock can be shaped to pass any assertion → tautological-test risk.
- `net_worth_usd` = *"on-chain USDC+native balance of `id`"* (`:37-38`) names no token contract or chain
  (design says Base/Polygon, `design...:44`).
- **Fix**: specify the reader interface, network(s), token-contract set, and earn-ledger query shape.

---

## Dimension 4 — Structural Integrity: FAIL

### R3-FIND-005 (major) — Producer/ownership conflict + `revenue_by_source` untyped + `earn_src` unshown
- Pipeline (`:21-23`) treats the landing-repo netlify `dashboard-sync.js` as the `/dashboard.json`
  owner, but project `CLAUDE.md` says `/dashboard.json` is rendered by a **Dais-owned** sync from
  `anicca-dais`+`anicca-genesis` state and Anicca/landing must not write it. The spec adds the chain
  enrich/aggregate without saying which producer owns it or how the guardrail holds.
- `revenue_by_source` is signed/persisted (R1 `:30-31`, R10 `:63-64`) and shown in drill-down, but R9's
  type-check list (`:62`) omits it → malformed object reaches the UI.
- `earn_src` (the ranked figure's provenance) is added to the element (`:31`) but R6 surfaces only a
  `net_worth_src` indicator (`:52`) → an unverified high-revenue row looks identical to a verified one.
- **Fix**: name the enrich/write owner + respect the guardrail; add `revenue_by_source` to R9; add an
  `earn_src` indicator to R6.

---

## Dimension 5 — Verification Readiness: FAIL

### R3-FIND-006 (critical) — Proof covers self-report overwrite, not fabricated EARNINGS or real delivery
- 1b R3 (`:78`) proves only that an inflated **self-report** is overwritten by the mocked chain value.
  Because R3 trusts raw inflows (R3-FIND-001), the chain value itself is fakeable — no 1b row feeds a
  self-transfer/seed inflow and asserts rank does not move.
- R6's proof (`:81`) renders a hand-authored *"leaderboard fixture"*, not the real served
  `/dashboard.json`, so a green component test coexists with a `/dashboard.json` that has no
  `leaderboard` (R3-FIND-002).
- **Fix**: add a 1b proof that a self-funding inflow cannot raise rank, and a 1b/E2E proof that the
  actually-served `/dashboard.json` carries the enriched leaderboard the UI renders.

---

## Must-fix before Phase 2 (RED)
1. **R3-FIND-001 + R3-FIND-006**: define the ranked figure as earn-ledger reads (exclude
   seed/self/own-address transfers), name the ledger interface, and prove a self-transfer cannot win.
   This is the feature's entire point and is still gameable.
2. **R3-FIND-002 + R3-FIND-005**: name the single producer that writes the enriched `leaderboard` into
   the exact `/dashboard.json` `EmpireDashboard` fetches; reconcile Supabase-`instances` vs the
   Dais-owned static render and the no-direct-write guardrail.
3. **R3-FIND-004**: specify the `reader` interface + network + token-contract set so R3's mock tests are
   concrete and non-tautological.
4. **R3-FIND-003**: define the all-unverified headline state (`—`, not `$0`) and constrain
   `revenue_today_usd` (`≥0`, `today ≤ mtd`).
5. Minor: type-validate `revenue_by_source`; surface `earn_src` in the UI; pin `OUR_INSTANCE_IDS` file
   location/owner.
