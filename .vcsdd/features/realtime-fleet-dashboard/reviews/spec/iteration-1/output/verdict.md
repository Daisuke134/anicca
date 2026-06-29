# VCSDD Phase 1c Spec Review — realtime-fleet-dashboard (iteration 1)

- Reviewer: VCSDD Adversary (fresh context, disk-only)
- Date: 2026-06-29
- Artifacts reviewed: `specs/behavioral-spec.md`, `specs/verification-architecture.md`
- Grounding cross-check: `runtime/dashboard/telemetry-poster.mjs`, `runtime/identity.mjs`,
  `skills/report/anicca-report.sh`, `docs/superpowers/specs/2026-06-22-revenue-dashboard-and-earn-experiment.md`,
  `THESIS.md`, `README.md`

## OVERALL VERDICT: **FAIL**

| Dimension | Verdict |
|---|---|
| 1. Spec Fidelity | **FAIL** |
| 2. Edge Cases | **FAIL** |
| 3. Completeness / Gaps | **FAIL** |
| 4. Structural Integrity (purity boundary) | **PASS** |
| 5. Verification Readiness | **FAIL** |

Finding count: 16 (F1–F16). Must-fix (critical): F1, F2, F5, F9, F13.

---

## Dimension 1 — Spec Fidelity: **FAIL**

### F1 (critical, category: requirement_mismatch / grounding) — "Context grounded in existing code" cites files that do not exist in this repo
`behavioral-spec.md` §Context lines 10–12 anchor the whole spec on `app/dashboard/page.tsx`,
`netlify/functions/dashboard-sync.js`, and `_lib/telemetry-aggregate.js` "(grounded in existing code, 2026-06-29)".
None of these exist in `/Users/anicca/anicca-human-funded` (Glob `**/dashboard/page.tsx`, `**/dashboard-sync.js`,
`**/telemetry-aggregate.js` → No files found; `apps/**` → No files found, yet line 13 cites `apps/api/.env`).
The actual dashboard front-end + netlify functions live in a SEPARATE repo (per project CLAUDE.md the landing/dashboard
is `~/anicca-project/apps/landing`). A Phase-1c gate whose grounding is unverifiable from the repo under review is
not grounded. **Fix:** state, per IN-scope artifact, exactly which repo/path it lives in (registry-client here;
`/dashboard` page + netlify fn + Supabase schema elsewhere), or move the cross-repo artifacts OUT of scope. Re-cite the
real existing file (`runtime/dashboard/telemetry-poster.mjs`) that this repo actually contains.

### F2 (critical, category: requirement_mismatch) — Spec ignores and silently forks the EXISTING registration/heartbeat mechanism
The real existing "register/heartbeat/log" path in THIS repo is `runtime/dashboard/telemetry-poster.mjs`: it builds a
signed message (`acct.signMessage`, line 148) and POSTs to `https://aniccaai.com/.netlify/functions/telemetry`
(line 149), and identity is the wallet address (`runtime/identity.mjs` lines 1–15: "the address makes uniqueness free…
first telemetry POST auto-registers"). The spec (REQ-1/2/3/12, `verification-architecture.md` §EFFECTFUL line 15)
proposes a NEW `registry-client` writing DIRECTLY to Supabase via "anon+RLS upsert OR scoped server endpoint" with a
hand-assigned text id. The spec never names telemetry-poster.mjs, never says whether it is replaced or coexists, and
drops the signature auth. Two writers to one row = the exact "akash stole anicca's wallet row" bug already fixed
(see `2026-06-22-revenue-dashboard...md` line 52 "host_wallet_mismatch", line 62 akash overwriter). **Fix:** declare
whether the new client REPLACES telemetry-poster.mjs (and delete it) or extends it; reconcile the write path with the
existing signed-POST/host-guard model.

### F3 (major, category: spec_gap) — "assets" silently redefined from net worth to wallet-USDC, dropping all DeFi/HL positions
Context line 12 says existing fields include `net_worth_usd`; the new canonical schema (lines 31–33) replaces it with
`wallet_usdc` "(assets, USDC)" and REQ-6 totals "Σ wallet_usdc (assets)", REQ-8 "wallet→assets (linked to basescan)",
REQ-10 "wallet_usdc from chain". But `telemetry-poster.mjs` net worth (lines 59–73, `sumNw` line 110) is wallet USDC
PLUS aave/morpho/moonwell/beefy/fluid/bluechip/Hyperliquid (~$7.3 yield + $8.84 HL). Defining "assets" as wallet USDC
only (basescan-visible) DROPS every position the existing dashboard deliberately added (HL was explicitly fixed in,
see same spec lines 117–119). This is a behavioral regression presented as a field rename, unacknowledged.
**Fix:** either keep `net_worth_usd` (wallet + positions) as "assets" and define how the registry client computes it,
or explicitly state and justify that the dashboard now shows wallet-USDC-only and accepts under-counting.

### F4 (major, category: spec_gap) — human-funded vs self-funded is the headline distinction, but the project's own THESIS/README say it is NOT meaningful
Goal (line 5) and REQ-8 make "human-funded vs self-funded" a first-class badge, yet `README.md` line 87
("Human-funded and self-funded therefore **behave identically**") and line 91 ("the more meaningful distinction is the
harness … **not** human-funded vs self-funded") plus `THESIS.md` line 8 ("Human-funding is only a KICKSTART, never the
identity") directly contradict elevating it. The spec neither cites nor resolves this. **Fix:** justify why `funding`
deserves a first-class badge against the repo's own thesis, or demote it and elevate the harness/env/brain axis the
THESIS says is the real one.

---

## Dimension 2 — Edge Cases: **FAIL**

### F5 (critical, category: requirement_mismatch) — PHANTOM div-by-zero edge: `burn_day=0` guards a division that exists in NO requirement
`verification-architecture.md` line 23 lists "burn_day=0 (div-by-zero guard)" as a unit edge. But REQ-5 divides by
the CONSTANT 30 (`revenue_mo_usd/30 >= burn_day_usd`, line 47) and REQ-6 MULTIPLIES burn (`Σ(burn_day·30)`, line 48).
No requirement ever divides by `burn_day`, so there is nothing to guard. Either the formula was meant to be a ratio
(`revenue_mo_usd / burn_day_usd >= 30`, which WOULD div-by-zero) or the edge is fictitious. A spec whose enumerated
edge does not match its own arithmetic is internally inconsistent. **Fix:** make the formula and the edge agree —
state the intended expression and the burn_day=0 result, OR delete the phantom edge.

### F6 (critical, category: test_coverage) — The REAL div-by-zero (per-instance % over an empty/all-derived fleet) is unspecified
REQ-6 returns `self_funded_pct` and `frontier_pct`. On an empty fleet these are 0/0 = NaN; the "empty fleet" edge
(line 23) is listed but never tied to a defined result for the percentages. **Fix:** specify `computeTotals([])` →
`{assets:0, revenue30d:0, net:0, counts:{alive:0,stale:0,dead:0}, self_funded_pct:0, frontier_pct:0}` (or null),
explicitly defining the 0-denominator outcome.

### F7 (major, category: requirement_mismatch) — `deriveStatus` behavior on null/NaN `last_heartbeat` undefined; a corrupt row reads ALIVE
`verification-architecture.md` line 23 lists "no last_heartbeat" but REQ-1 (line 43) always sets `last_heartbeat=now`,
so the pure function's behavior when the field is null/undefined is never specified. `now - null = NaN`, and
`NaN > 90_000 === false` ⇒ such a row derives `'alive'` — i.e. a never-heartbeated/corrupt row is shown alive, the
opposite of intent. **Fix:** REQ-4 must define the null/NaN/missing case explicitly (e.g. missing last_heartbeat ⇒
`'stale'` or `'dead'`).

### F8 (major, category: security_surface) — Missing edge: duplicate / spoofed `id` (PK collision overwrites another body's row)
PK is a hand-assigned text `id` (line 21, REQ-10 hardcodes `anicca-001-claude`). `runtime/identity.mjs` exists
PRECISELY because uniqueness must come from the wallet address, not a hand-picked label, and the akash incident shows
the real attack (one body overwriting another's row). With anon upsert keyed on a guessable text id there is no edge
covering "second writer claims the same id". **Fix:** enumerate the id-collision/overwrite edge and define the
authority that prevents it (wallet-derived id + signature, as the existing system does).

---

## Dimension 3 — Completeness / Gaps: **FAIL**

### F9 (critical, category: spec_gap) — The page↔function schema mismatch the gate is supposed to reconcile is NOT reconciled
The task is to reconcile the page's `lineage` shape vs the function's `instances` shape. The spec asserts (line 16)
the page is "rewritten to render LIVE from the registry" but never states the migration: the live page (per
`runtime/identity.mjs` line 25) consumes `dashboard-sync`'s `leaderboard[]` keyed by `host`; the new schema is
`instances[]` keyed by `id` with different fields (`wallet_usdc` not `net_worth_usd`, `funding`/`env`/`brain` new).
There is no mapping table from old shape → new shape, no statement of what happens to `dashboard-sync.js`/`aggregate()`,
and the artifacts are in another repo (F1). **Fix:** add an explicit field-by-field reconciliation (old `leaderboard`/
`net_worth_usd`/`host` → new `instances`/`wallet_usdc`/`id`) and state the fate of `dashboard-sync`.

### F10 (critical, category: security_surface) — RLS / least-privilege write path is not concrete; "anon + RLS upsert" with no per-row auth = open spoofing
REQ-12 (line 54) offers "anon+RLS insert/upsert OR a scoped server endpoint" as an OR with no decision and no policy.
A Supabase anon key + RLS that permits `insert/upsert` on `instances` lets ANY client write ANY `id`'s wallet/revenue
(no per-instance identity), regressing the signed-POST host-guard that already prevents this. **Fix:** pick ONE path
and specify the concrete policy: which key the client holds, the exact RLS predicate that ties a write to the writing
instance's identity (e.g. signed claim / JWT / wallet signature), and prove an anon client cannot overwrite a row it
does not own.

### F11 (major, category: spec_gap) — `funding` (declared) vs `isSelfFundedEconomic` (computed): relationship and which one drives `self_funded_pct` is undefined
REQ-5 (line 47) keeps `funding` as declared origin and `isSelfFundedEconomic` as economic reality, "Both shown" — but
never defines what a user concludes from a `funding='human' & economic=true` (or `'self' & economic=false`) row, nor
WHICH field feeds REQ-6 `self_funded_pct` / the badge. Given economic revenue is currently ~$0/negative
(`telemetry-poster.mjs` lines 143; `2026-06-22...md` line 99 "Current value = $0.00"), `isSelfFundedEconomic` is
~always false, making the headline % meaningless if it uses the economic flag, or static if it uses `funding`.
**Fix:** define `self_funded_pct`'s source field unambiguously and document the 2x2 interpretation.

### F12 (major, category: spec_gap) — Heartbeat cadence contradiction: spec demands ≤30s, the existing body posts every 120s ⇒ THIS instance is permanently STALE
REQ-2 (line 44) mandates heartbeat interval ≤30s and REQ-4 (line 46) marks `'stale'` at >90s. The actual running body
`telemetry-poster.mjs` line 156 is `setInterval(post, 120000)` = 120s, which exceeds 90s ⇒ under REQ-4 the live
instance would render STALE forever, contradicting REQ-7/REQ-10 ("THIS instance … ALIVE"). The spec never instructs
changing the poster interval. **Fix:** reconcile the cadence (lower the poster to ≤30s, or raise the staleness
threshold above the real heartbeat period) and state it.

### F13 (critical, category: spec_gap) — Per-instance logs are required on the card but absent from the view-model + the join is undefined
REQ-8 (line 50) requires each card to show "its most-recent N logs", but `toCardModel(row, nowMs)`
(`verification-architecture.md` line 11) takes only a single `instances` row — no logs parameter — and its return type
ends in "...". The `instances`↔`instance_logs` join, the value of N, ordering, and where the join lives (pure core?
shell?) are all unspecified. **Fix:** define the card model's full field list (no "..."), add logs (with N + ordering)
to the model or define the join boundary, and specify the data-source query.

---

## Dimension 4 — Structural Integrity (purity boundary): **PASS**

Positive evidence: the pure core (`verification-architecture.md` lines 5–12) is genuinely pure — `deriveStatus(row,
nowMs)`, `computeTotals(rows, nowMs)`, `isSelfFundedEconomic(row)`, `normalizeLogKind(kind)` all take `now` as an
explicit parameter rather than calling `Date.now()` internally, so they are deterministic and unit-testable without
network or clock, and the module forbids fetch/supabase/fs imports (line 6). I/O is isolated behind a "fake source"
adapter (line 16). This boundary is sound and testable.

### F14 (minor, category: structural — non-blocking) — `toCardModel` return type is open-ended ("..."), weakening the contract
Line 11 ends the return shape with "...", so the pure view-model contract is not fully pinned for the unit tests that
are supposed to enforce it. Does not break the purity boundary (hence dimension PASS) but should be closed alongside
F13. **Fix:** enumerate every field `toCardModel` returns.

---

## Dimension 5 — Verification Readiness: **FAIL**

### F15 (critical, category: verification_tool_mismatch) — REQ-12 key-safety "grep gate" is under-specified and collides with a legitimate field
`verification-architecture.md` lines 27–29 propose "a test/grep gate asserts no private-key / service-role-key string
ever reaches a payload". A 64-hex private key pattern (`0x[0-9a-fA-F]{64}`) also matches the legitimate `tx_hash`
field (schema line 40), so a generic regex false-positives on real log rows; conversely grepping only the one known
secret string proves nothing about "NEVER" for arbitrary keys. The obligation is not objectively verifiable as
written. **Fix:** specify the exact detection (e.g. assert the payload object's key set is a fixed allowlist that
excludes any secret-bearing field, AND assert `env.SUPABASE_SERVICE_ROLE_KEY` / wallet private key never appear as a
substring), and explicitly exclude `tx_hash` from the private-key heuristic.

### F16 (critical, category: test_quality) — E2E "within 5s" contradicts the ≤15s polling fallback, and "not the fallback" is not objectively distinguishable
Acceptance line 59 requires a log line "appearing within 5s", but REQ-9 (line 51) permits a ≤15s polling fallback when
Realtime is unavailable — under that fallback the 5s assertion cannot pass, so the acceptance is unsatisfiable in the
fallback mode the spec itself blesses. Separately, REQ-7's fallback is now an explicit "registry unavailable" state
(not fake rows), so "proves NOT the fallback" is ill-defined: a correctly-rendered LIVE row and a correctly-rendered
cached/stale row can look identical in a screenshot. **Fix:** (a) make the realtime-mode SLA (5s) and polling-mode SLA
(≤15s) consistent or branch the acceptance per mode; (b) define an objective "not the fallback" probe — e.g. insert a
unique random sentinel log id from the test and assert that exact id appears in the rendered DOM within the SLA, which
also proves it is the live registry and not a cached/hardcoded board.

---

## Required for PASS (next iteration)
Resolve all critical findings F1, F2, F3, F5, F6, F9, F10, F13, F15, F16 (and the majors). Re-ground every "existing
code" citation against files that actually exist in this repo, reconcile the new registry client with the existing
signed `telemetry-poster.mjs`/wallet-identity model, make every formula/edge pair internally consistent, and make
each REQ objectively checkable by a named test.
