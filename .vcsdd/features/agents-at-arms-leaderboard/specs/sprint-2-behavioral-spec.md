# Sprint-2 Behavioral Spec — agents-at-arms-leaderboard

Builds on sprint-1 `behavioral-spec.md` v5 (spec gate PASS, impl adversary PASS ×2, 52 unit tests
green, browser E2E green). Sprint 2 closes the remaining production wiring so real self-funding
agents seat themselves on `aniccaai.com/dashboard` with zero human in the loop:

- S7: additive SQL migration extending the live `instances` table with the leaderboard columns
  named in the spec (tags, revenue_today_usd, revenue_by_source, net_worth_src, earn_src,
  last_heartbeat), with strict back-compat (no rejection of currently-valid rows).
- S9: spawn-boot helper that upserts the agent's row and signs the canonical heartbeat message
  (`tags` and `revenue_today_usd` are inside the signed bytes, so the `#agent-hackathon` /
  `Ours` categorization on the leaderboard is authenticated per sprint-1 R10).
- S11: a render script that periodically runs `enrichOnChain` + `aggregate` and writes the
  ENRICHED result (including `leaderboard`) into the SERVED `apps/landing/public/dashboard.json`.
  Sprint-1 R12 already forced the netlify endpoint to enrich; this closes the second producer
  named in sprint-1 v5 R11 and used by `components/site/AgentLeaderboard.tsx`.

Ground truth (unchanged): `_lib/telemetry-schema.js`, `_lib/telemetry-aggregate.js`,
`_lib/telemetry-verify.js`, `_lib/telemetry-store.js`, `_lib/enrich.js`,
`_lib/leaderboard-constants.js`, `_lib/chain-reader.js`, `netlify/functions/dashboard-sync.js`
(R12 GREEN), `apps/landing/supabase/instances.sql`.

## 1a. Requirements (EARS)

- **S7.1 (additive columns)** The migration SHALL add to `instances`, IF NOT EXISTS, the columns
  `tags text[]`, `revenue_today_usd double precision`, `revenue_by_source jsonb`,
  `net_worth_src text`, `earn_src text`, `last_heartbeat timestamptz`, and `log_feed jsonb` —
  where `log_feed` mirrors the field that sprint-1 `telemetry-schema.validate` already type-checks
  (`_lib/telemetry-schema.js:27-29`) and `canonicalMessage` already signs
  (`_lib/telemetry-verify.js:18`), so a live payload with `log_feed` upserts without an
  unknown-column error via `telemetry-store.upsertInstance` (which spreads the payload). The
  migration SHALL also create index `idx_instances_tags_gin` on `tags` (GIN). All columns SHALL
  be nullable so any currently-valid row remains valid (back-compat, sprint-1 R9). Running the
  migration twice SHALL be safe (idempotent).
- **S7.2 (write path constraint)** The migration SHALL NOT change the runtime contract in
  `telemetry-schema.js`: the additive fields remain OPTIONAL, and the schema validator continues
  to type-check them when present exactly as sprint-1 R9 requires. (No column becomes NOT NULL.)
- **S9.1 (spawn upsert)** The spawn-register helper `_lib/spawn-register.js` SHALL export
  `async registerSpawn({ privateKey, payload, storeDeps, now = () => new Date().toISOString() })`
  that (a) builds `message = canonicalMessage(payload)` byte-identical to sprint-1's helper (so
  additive fields are inside the signed bytes and cross-language signatures still hold),
  (b) signs `message` with `privateKey` via `ethers.Wallet.signMessage`, (c) verifies locally
  with `verifyTelemetry` (schema + replay window), (d) upserts the row via
  `telemetry-store.upsertInstance` with `id` lowercased, and (e) returns
  `{ message, signature, last_heartbeat }`. `storeDeps = { url, key, f = fetch }` is the same
  shape sprint-1's `telemetry-store.js` accepts — passed through unchanged for test injection.
- **S9.2 (signer == id invariant)** If `ethers.verifyMessage(message, signature).toLowerCase()`
  does not equal `payload.id.toLowerCase()`, the helper SHALL throw an Error whose message
  contains BOTH the literal token `signer` AND the mismatched address values, and SHALL NOT
  call the store. The RED test SHALL assert on that specific token so the assertion cannot pass
  on a generic error (e.g. a network error would fail the assertion). This is the same
  invariant the netlify verifier enforces (`telemetry-verify.js`), applied pre-upload.
- **S9.3 (last_heartbeat)** WHEN the helper upserts, it SHALL also stamp `last_heartbeat` to the
  current UTC ISO string.
- **S11.1 (render script)** `scripts/render-dashboard.mjs` SHALL take an array of raw Supabase
  rows (in tests, from a fixture; in production, from `SUPABASE_URL` + service role key), pass
  them through `enrichOnChain(reader)` then `aggregate()`, and MERGE the result into the existing
  `apps/landing/public/dashboard.json`. The existing top-level keys of `dashboard.json` (`mrr`,
  `goals`, `followers`, `lineage`, etc.) SHALL NOT be dropped — the merge is additive and
  preserves ordering. The output SHALL contain the top-level key `leaderboard` matching the
  aggregate output.
- **S11.2 (reader injection + honesty)** `render-dashboard.mjs` SHALL accept an injectable reader
  (`{ reader }`) so tests can drive it deterministically. When no live `BASE_RPC_URL` is
  configured, the script SHALL still succeed, producing `earn_src`/`net_worth_src ==
  'unverified'` for every row (never a fabricated chain figure). This preserves sprint-1
  INV-NOFAKE.
- **S11.3 (empty is honest)** If Supabase returns zero rows OR no rows are enrich-verifiable,
  `leaderboard` SHALL still be an array (possibly empty). The UI's empty state (sprint-1 R8)
  handles rendering; no fake placeholder rows are injected.
- **S11.4 (CLI safety — never clobber a good `dashboard.json`)** The CLI entrypoint SHALL:
  (a) refuse to run and exit with a non-zero code if `SUPABASE_URL` or `SUPABASE_SERVICE_ROLE_KEY`
  is missing; (b) refuse to write the served `dashboard.json` and exit non-zero if the Supabase
  fetch fails (non-2xx or throws); (c) NEVER produce a `leaderboard=[]` result to disk from a
  fetch-failure path — the served file MUST retain its prior `leaderboard`. The importable
  `renderDashboard` function stays a pure transform of its inputs (empty rows ⇒ empty
  leaderboard is correct at the function level; the CLI wrapper is the guardrail against a
  fetch-failure silently wiping a good leaderboard).
- **S11.5 (pre-migration row shape)** The additive columns from S7 are nullable. A Supabase row
  fetched BEFORE ops runs the migration SHALL surface those columns as either absent OR
  `null`; both shapes SHALL pass through `enrichOnChain` unchanged (self-asserted values are
  never trusted anyway). Tests SHALL model at least one row with explicit `tags:null`,
  `revenue_today_usd:null`, `revenue_by_source:null`, `net_worth_src:null`, `earn_src:null`,
  `last_heartbeat:null`, `log_feed:null` to prove enrich + aggregate handle both shapes.

## 1b. Verification architecture (proves each requirement)

| Req  | Test kind       | Concrete proof |
|------|-----------------|----------------|
| S7.1 | pure SQL parse  | file exists; contains `add column if not exists tags`, `revenue_today_usd`, `revenue_by_source jsonb`, `net_worth_src`, `earn_src`, `last_heartbeat`; contains `create index if not exists idx_instances_tags_gin on instances using gin(tags)` |
| S7.1 | idempotency     | running the SQL text through a stub applier twice yields the same normalized schema (no duplicate columns, no drop) |
| S7.2 | contract check  | every current fixture in `handler-telemetry.test.js` still passes; new fixtures with the additive fields still validate (sprint-1 R9 already covers this — sprint-2 must not regress it) |
| S9.1 | unit            | given a known private key + payload including `log_feed`, helper builds the canonicalMessage EXACTLY equal to `canonicalMessage(payload)`, signs it, and `verifyTelemetry` returns `ok:true` |
| S9.1 | unit            | on success, helper calls the injected `upsertInstance(f, ...)` exactly once with `id.toLowerCase()` and returns `{ message, signature, last_heartbeat }` |
| S9.2 | unit            | if `id` does not match the signer (payload id is a different address), helper throws an Error whose `.message` contains the literal `"signer"` AND both address strings, and does NOT call `upsertInstance` |
| S9.3 | unit            | injected clock -> upsert body AND return value contain the SAME `last_heartbeat` ISO string |
| S11.1| unit + snapshot | given a fixture existing dashboard.json (`{ mrr, goals }`) and 3 raw rows + injected reader, the render script produces a JSON with `mrr` + `goals` preserved AND top-level `leaderboard` array whose length matches the aggregate |
| S11.2| unit            | when reader throws for every method, the resulting `leaderboard` still exists and every element carries `earn_src == 'unverified'` and `net_worth_src == 'unverified'` |
| S11.3| unit            | zero raw rows -> `leaderboard == []`; verified count = 0 -> `total_net_worth_usd == undefined` (sprint-1 R4 already GREEN) |
| S11.4| unit            | CLI safety helper (exportable pure fn `shouldRefuseCliWrite({env,fetchOk})`) returns `refuse:true` on missing env / non-ok fetch — so the RED assertion doesn't require spawning a subprocess |
| S11.5| unit            | pre-migration row shape (all additive columns explicitly `null`) enriches + aggregates without throw, leaderboard length matches input rows |

## Invariants preserved (from sprint-1)

- INV-NOFAKE: ranked figures come from the on-chain reader; unverifiable ⇒ flagged, ranked last,
  excluded from totals. S11.2 tightens this by REQUIRING that a broken reader produces
  `unverified` (never a fabricated chain figure).
- INV-OWN-STATE / write-auth: heartbeat is signed; `signer == id` enforced BOTH client-side in
  the spawn helper (S9.2) AND server-side in the netlify verifier.
- INV-BACKCOMPAT: additive-only. No currently-valid row is rejected (S7.1, S7.2).

## Done (this sprint)

1. `apps/landing/supabase/2026-07-instances-leaderboard.sql` on disk (S7).
2. `apps/landing/netlify/functions/_lib/spawn-register.js` with unit tests green (S9).
3. `apps/landing/scripts/render-dashboard.mjs` with unit tests green (S11).
4. Full telemetry test suite still green (regression baseline: 52+ PASS).
5. Fresh-context sonnet-5 adversary PASS on this spec AND on the impl.
6. **My own browser E2E** on `/dashboard` after running the render script against a curated
   fixture: real agents appear, no-fake gating still visible, filters still work.

## Scope

- Solana `wallet_sol` remains OUT OF SCOPE (sprint-1 v5).
- Earn-ledger cross-check (donation vs earned) remains OUT OF SCOPE — the sprint-1 v5 honest
  scope stands (self/seed exclusion is what's un-buyable).
- The scheduled cadence that runs `render-dashboard.mjs` (cron/GitHub Actions) is ops config, not
  behavior; this spec proves the script's I/O contract and delegates scheduling to Dais ops per
  the aniccaai.com write-guardrail (Anicca instances never write the served json directly).
