# VCSDD Phase 1c Spec Review — realtime-fleet-dashboard (ITERATION 2)

- Reviewer: VCSDD Adversary (fresh context, disk-only)
- Date: 2026-06-29
- Artifacts reviewed: `specs/behavioral-spec.md` (iter 2), `specs/verification-architecture.md` (iter 2)
- Grounding cross-checked against the REAL files:
  - `~/anicca/runtime/dashboard/telemetry-poster.mjs`
  - `~/anicca/runtime/identity.mjs`
  - `~/anicca-project/apps/landing/netlify/functions/telemetry.js`
  - `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-verify.js`
  - `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-schema.js`
  - `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-store.js`
  - `~/anicca-project/apps/landing/netlify/functions/_lib/telemetry-aggregate.js`
  - `~/anicca-project/apps/landing/netlify/functions/dashboard-sync.js`
  - `~/anicca-project/apps/landing/app/dashboard/page.tsx`

## OVERALL VERDICT: **FAIL**

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | **FAIL** |
| 2. Edge Cases | **FAIL** |
| 3. Completeness / Gaps | **FAIL** |
| 4. Structural Integrity (purity boundary) | **PASS** |
| 5. Verification Readiness | **FAIL** |

F1–F16 from iteration 1: **15 resolved, 1 resolved-with-caveat (F8)**. The rewrite genuinely fixed the
forked-registry, phantom-edge, assets-redefinition, THESIS-conflict, and key-safety problems. BUT the
"grounding" pass introduced a NEW fabricated citation (a host-guard that does not exist), and three
substantive new gaps remain. New must-fix: **N1 (critical), N2 (major), N7 (major)**.

---

## F1–F16 Resolution Table (verified against disk, not just claimed)

| ID | iter-1 problem | Status | Evidence |
|---|---|---|---|
| F1 | grounding cited files not in repo | **RESOLVED** (but see N1) | spec lines 11–20 now give per-artifact repo+path; poster/identity/receiver/store/aggregate/page all verified to exist. One row of that table is fabricated → N1. |
| F2 | silently forked the existing register/heartbeat path | **RESOLVED** | §Decision lines 22–26: REUSE telemetry-poster (EXTEND, not replace); no anon Supabase; old `anicca-report.sh` not reintroduced. Matches real poster (`telemetry-poster.mjs:135-151`). |
| F3 | "assets" redefined to wallet-USDC, dropping HL/DeFi | **RESOLVED** | REQ-8 `assetsUsd(=net_worth_usd)`, line 61 "incl positions+HL". Matches `sumNw` (`telemetry-poster.mjs:110`) which includes hl/aave/morpho/etc. |
| F4 | human-vs-self headline contradicts THESIS | **RESOLVED** | REQ-9: primary axis = harness/env/brain/model; funding demoted to labeled origin attribute; economic flag = real metric. Coherent with THESIS. |
| F5 | phantom `burn_day=0` div edge | **RESOLVED** | REQ-5 divides by const 30 only; ver-arch edges line 26-27 "NO burn_day division anywhere … phantom F5 edge removed". |
| F6 | real div-by-zero (empty-fleet pct) unspecified | **RESOLVED** | REQ-6 "ON empty fleet BOTH pcts SHALL be 0"; ver-arch edge line 24. Matches `aggregate` guard (`telemetry-aggregate.js:8-9` `rows.length ? … : 0`). |
| F7 | null/NaN ts → reads ALIVE | **RESOLVED** | REQ-4 "'stale' if last ts missing/NaN OR nowSec-ts>300"; ver-arch edge line 21. |
| F8 | id-collision/overwrite edge + authority | **RESOLVED w/ CAVEAT** | Reuse (wallet id + signature) is the right authority, and REQ-3 "remain signature-verified" invokes it. BUT the spec names the WRONG guard (host-guard, see N1) and never names/tests the real one (`signer_mismatch`, `telemetry-verify.js:28`) → see N1/N5. |
| F9 | page↔function schema reconciliation + fate of sync | **RESOLVED** (leaderboard mapping) | REQ-7 "KEEP dashboard-sync as the source"; REQ-8 `toCardModel(row)` pins row→card mapping. Totals mapping still ambiguous → N2. |
| F10 | anon/RLS open spoofing | **RESOLVED** | REQ-3 deletes the anon write path entirely; reuse signed POST only. |
| F11 | declared `funding` vs computed economic; which drives pct | **RESOLVED** | REQ-6 "self_funded_pct … computed from isSelfFundedEconomic, NOT the declared funding"; REQ-9 documents the 2×2. Matches `aggregate` (`telemetry-aggregate.js:6`). |
| F12 | cadence ≤30s vs 120s poster → permanently stale | **RESOLVED** | REQ-4 stale at >300s (2.5×120s); REQ-10 client poll ≤120s. Consistent with real `setInterval(post,120000)` (`telemetry-poster.mjs:156`). |
| F13 | per-instance logs absent from view-model; join undefined | **RESOLVED** | REQ-8 `logs: Array<{ts,kind,note}> (newest-first, ≤20 from the row's log[])`. No join needed — log rides on the row (`telemetry-poster.mjs:146 log:recentLog(20)`). (Persistence of that column unverified → N7.) |
| F14 | `toCardModel` "..." open-ended | **RESOLVED** | REQ-8 enumerates the full fixed shape; ver-arch line 10 "no '...'". |
| F15 | key-safety grep gate under-specified + tx_hash collision | **RESOLVED** | REQ-12 + ver-arch §Key-safety: fixed allowlist key-set test; no 64-hex scan; "no tx_hash field exists". Allowlist (ver-arch line 32-34) matches the real 16 posted fields + 3 new = 19. `recentLog` confirms no tx_hash (`telemetry-poster.mjs:97`). |
| F16 | E2E 5s vs 15s poll contradiction; "not the fallback" ill-defined | **RESOLVED** | Acceptance lines 83-86: unique random sentinel in ledger → DOM within ≤150s (poll+heartbeat window); sentinel = objective live-vs-fallback probe. SLA now internally consistent. |

---

## Dimension 1 — Spec Fidelity: **FAIL**

### N1 (critical, requirement_mismatch / fabricated grounding) — the "host-guard" the spec leans on does NOT exist
`behavioral-spec.md` line 16 asserts: "host-guard | telemetry-verify | rejects post whose host ≠
`anicca-<wallet hex>` (400 host_wallet_mismatch) — the akash-stole-the-row fix". §Decision line 24 repeats
"Identity stays wallet-address + signature + host-guard + replay guard". REQ-3 (line 44) requires writes
"remain signature-verified WITH THE HOST-GUARD".
- **Reality:** `_lib/telemetry-verify.js` (lines 17–30) performs: json-parse, `validate`, future/stale/replay
  ts checks, `verifyMessage`, and `signer.toLowerCase() !== p.id.toLowerCase()` → `signer_mismatch`. There is
  **no host comparison and no `host_wallet_mismatch` reason anywhere.** `host` is validated ONLY as a
  nonempty string (`_lib/telemetry-schema.js:7-9`); it is a free-form field a poster may set to anything.
- The actual mechanism that prevents one body overwriting another's row is **`signer_mismatch`**
  (`telemetry-verify.js:28`) binding `id` to the signature — NOT a host-guard.
- This is the SAME failure class as iteration-1 F1 (grounding on code that does not exist), re-introduced in
  the very iteration that claimed to fix grounding. A builder told to "preserve the host-guard" (REQ-3) will
  preserve nothing, and may wrongly assume `host` is already authenticated.
- **Fix:** re-ground to `signer_mismatch` as the id-binding authority; delete the host-guard claim, OR
  specify that host validation must be ADDED (it currently is not) and define the exact predicate + status.

### N6 (minor, grounding) — sync path + leaderboard shape mis-cited
Line 19 cites the read API as `_lib/dashboard-sync.js`; the real path is
`netlify/functions/dashboard-sync.js` (not under `_lib`). It also calls `leaderboard[]` "keyed by host", but
`aggregate` returns `leaderboard` as an **array of full rows sorted by net_worth** (`telemetry-aggregate.js:10`),
not a host-keyed map. Low impact but it is a grounding inaccuracy in a grounding-focused iteration.
**Fix:** correct the path and the "keyed by host" wording.

### N8 (minor, requirement_mismatch) — REQ-11 promises `model='claude-sonnet-4-6'` but model is DERIVED, not declared
REQ-11 (line 70-72) asserts this instance posts `model='claude-sonnet-4-6'`. The real poster computes
`model_live` from the ledger via `lastModel()` (default `"auto"`) and tier via `FREE_RE`
(`telemetry-poster.mjs:102-107,127-128`); there is no `ANICCA_MODEL` declared field. The asserted value is
not objectively guaranteed unless the ledger happens to log it. **Fix:** either source `model` from a declared
env field, or state REQ-11's model is "whatever `lastModel()` resolves" rather than a fixed string.

---

## Dimension 2 — Edge Cases: **FAIL**

### N3 (major, requirement_mismatch / edge) — the schema's `'critical'` status is silently swallowed by `deriveStatus`
`_lib/telemetry-schema.js:15` accepts `status ∈ {alive, critical, dead}`. REQ-4 `deriveStatus` only branches
on `status==='dead'` else alive/stale-by-ts; `'critical'` is never mentioned, so a `status==='critical'` row
renders as **alive or stale**, never surfaced as critical. `aggregate`'s `alive` count also treats critical
as alive (`status !== 'dead'`, `telemetry-aggregate.js:4`). A real, schema-valid enumerated input has no
defined display result. **Fix:** add `'critical'` to REQ-4's enumeration + the edges table with a defined
`statusDisplay`, or explicitly document that `'critical'` collapses into the alive class on purpose.

(Positive: the previously-failing edges F5/F6/F7 are all now defined and internally consistent with the
formulas — verified against `aggregate` and the REQ-5/REQ-6 arithmetic.)

---

## Dimension 3 — Completeness / Gaps: **FAIL**

### N2 (major, spec_gap) — "REUSE not fork" is contradicted: `computeTotals` (TS) duplicates `aggregate` (JS) and which one renders is undefined
REQ-6 defines a PURE `computeTotals(rows,nowSec) → {assets, revenue30d, net, counts:{alive,stale,dead},
self_funded_pct, frontier_pct}`. The live read path is `dashboard-sync.js` → `aggregate()`
(`telemetry-aggregate.js`), which returns a DIFFERENT shape `{total_net_worth_usd, earned_mo_usd, alive,
self_funded_pct, frontier_pct, leaderboard, updated_at}` — **no `net`, no `counts.stale`/`counts.dead`**.
REQ-7 says the page renders "dashboard-sync's leaderboard[] + totals."
- If the page renders dashboard-sync's totals → `computeTotals` (REQ-6) is dead spec, and stale/dead counts
  (which need `deriveStatus`) cannot be shown (aggregate has no staleness notion).
- If the page recomputes via `computeTotals` from the leaderboard rows → there are now TWO implementations of
  `self_funded_pct`/`frontier_pct` (CommonJS `aggregate.js` + TS `dashboard-core`) = the exact fork the spec
  says it is avoiding, with no statement of how they stay consistent.
The spec never says whether `aggregate()` is extended to call `dashboard-core`, replaced, or duplicated.
**Fix:** pin one path — either make `dashboard-sync`/`aggregate` the single source consumed verbatim (and
drop/justify `computeTotals`), or have the page own totals via `dashboard-core` and explicitly retire
`aggregate`'s totals; reconcile the field names (`total_net_worth_usd`↔`assets`, `earned_mo_usd`↔`revenue30d`).

### N7 (major, spec_gap / verification) — REQ-8 assumes `row.log[]` (and the 3 new fields) are PERSISTED columns; this is unverified and contradicted by `canonicalMessage`
REQ-8 derives card `logs` "from the row's `log[]`", served via `dashboard-sync` `select=*`
(`dashboard-sync.js:6`). But `_lib/telemetry-verify.js:7-13` `canonicalMessage` — the documented persisted/
signed subset — lists only **11** fields and **omits `log`, `breakdown`, `daily_revenue_usd`,
`monthly_revenue_usd`, `revenue_by_source`**, even though the poster signs/sends all 16. There is strong
evidence the `instances` table may not have a `log` column; if so, `select=*` returns no `log` and REQ-8's
logs + the F16 sentinel E2E cannot render. The spec provides NO DDL / column list for the `instances` table
and does not confirm `log` is stored. REQ-2 only adds the 3 new columns. **Fix:** include the exact
`instances` schema (columns for `log`, `breakdown`, `funding`, `env`, `brain`) and assert
`dashboard-sync` actually returns `log`; add an integration test that reads a persisted `log` back.

### N4 (minor, spec_gap) — server-side default VALUES for `funding`/`env`/`brain` on the backward-compat path are unspecified
REQ-2 says an old poster omitting the 3 fields "still upsert (fields default server-side)". REQ-1's
`human/local/claude-p` defaults are the POSTER's env defaults (applied only when the new poster runs); an OLD
poster sends nothing, so the SERVER default for an unknown-origin row is undefined. Defaulting to `'human'`
would mislabel a cloud/self instance. **Fix:** specify the server default (e.g. `'unknown'`/null) and how a
card renders unknown funding/env/brain.

---

## Dimension 4 — Structural Integrity (purity boundary): **PASS**

Positive evidence: the pure core (`verification-architecture.md` lines 5–11) keeps `nowSec` as an explicit
parameter for `deriveStatus`/`isSelfFundedEconomic`/`computeTotals` (deterministic, no `Date.now()`),
forbids fetch/supabase/fs imports (line 5), and isolates I/O behind a fake-source adapter (line 15). The
iteration-1 F14 defect is fixed: `toCardModel`'s return shape is now fully enumerated (REQ-8, ver-arch
line 10) with no open-ended "...". The boundary and the view-model contract are sound and unit-testable.
(The `computeTotals`/`aggregate` duplication is real but is routed under Completeness/N2 to avoid
double-counting; it does not break the purity boundary itself.)

---

## Dimension 5 — Verification Readiness: **FAIL**

### N5 (major, test_coverage / security_surface) — the REAL anti-overwrite mechanism (`signer_mismatch`) has no named test
The integration plan (acceptance line 82; ver-arch line 40) tests "unsigned/anon write → rejected", but NOT
the attack F8 was actually about: a DIFFERENT wallet signing a payload whose `id` is ANOTHER instance's
wallet → must be rejected by `signer_mismatch` (`telemetry-verify.js:28`). That is the precise "akash stole
the row" defense, and it is the authority the spec should be proving. **Fix:** add a named integration test:
"valid signature by wallet B with `id`=wallet A → 401 `signer_mismatch`".

### N9 (minor, verification_tool_mismatch) — `isSelfFundedEconomic` signature is inconsistent (1 vs 2 args) → not objectively testable
`behavioral-spec.md` REQ-5 (line 49) writes `isSelfFundedEconomic(row)` (one arg); `verification-architecture.md`
line 7 writes `isSelfFundedEconomic(row, nowSec)` (two args, since it uses `deriveStatus` which requires
`nowSec`). A unit test cannot be written against an ambiguous arity. **Fix:** pin the signature (it must take
`nowSec` to evaluate `deriveStatus≠dead`).

(N1 and N7 also degrade verification readiness: REQ-3's host-guard is untestable because the guard does not
exist, and REQ-8's logs cannot be E2E-verified without a confirmed persisted `log` column.)

---

## Required for PASS (iteration 3)
Must-fix: **N1** (delete/replace the fabricated host-guard grounding; name `signer_mismatch` as the real
id-binding authority), **N2** (resolve `computeTotals` vs `aggregate` — one source of truth, reconcile field
names), **N7** (specify the `instances` DDL incl. `log`+3 new columns and prove `dashboard-sync` returns
them). Also close N3 (`'critical'` status), N4 (server defaults), N5 (signer-mismatch test), N6/N8/N9
(grounding + signature precision). The iteration-1 corpus (F1–F16) is otherwise genuinely resolved.
