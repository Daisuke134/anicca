# Iteration-4 Spec Review — Resolution Notes

Reviewer: Opus-model adversary (deeper-scrutiny pass beyond prior Sonnet passes). Verdict: FAIL, 5
findings (3 critical, 2 major). All 6 iteration-1, 4 iteration-2-round-1, and 6 iteration-2-round-2
findings were reconfirmed genuinely resolved before this pass ran. This note records exactly what
changed for each of the 5 new findings, citing the real, current source files verified before editing
and the new line ranges in `specs/behavioral-spec.md` / `specs/verification-architecture.md`.

Files touched: `specs/behavioral-spec.md`, `specs/verification-architecture.md`. No implementation
code was touched — `ledger.js` remains exactly `{readChildren, appendChild}`, unmodified, per the
finding's own explicit instruction.

---

## FIND-301 (critical) — ledger.js duplicate `child_id` rows, no update primitive

**Root cause confirmed real:** `~/anicca/skills/self/spawn/lib/ledger.js` exports exactly
`readChildren`/`appendChild` (verified by direct read) — no update/upsert primitive, and its own test
suite (`__tests__/ledger.test.js`) never exercises two rows sharing one `child_id`. The superseded
`run.sh` (verified lines 124-140, 200-220) genuinely appends a `"provisioning"` row and later a SECOND
row with the same `child_id` and an updated `status` (`"seed_failed"` or `"active"`) — proving
duplicate-`child_id` rows are real, existing, production behavior.

**Fix — spec-level only, `ledger.js` untouched:**
- `specs/behavioral-spec.md` REQ-101 (lines ~170-201): step 2's join description now explicitly states
  `ledgerRows` may contain multiple rows sharing one `child_id`, cites `run.sh`'s real
  provisioning-row-then-status-row pattern as evidence, and defines "that row" as the LAST
  (highest-index / most-recently-appended) row for a given `child_id` — last-write-wins, since JSONL
  append order is chronological. `filterProductiveCitizens` MUST reduce to one effective row per
  `child_id` before applying its exclusion rule; matching the FIRST row is explicitly forbidden.
- REQ-101 Edge Cases (new bullet, ~lines added after the RPC-failure edge case): a citizen with two
  rows for the same `child_id` with different `status` values — only the LAST row's `status`/
  `active_since` is used.
- REQ-101 Acceptance Criteria (the `filterProductiveCitizens` bullet, ~line 213 region): now states the
  function FIRST reduces to one row per `child_id` (last-write-wins) THEN applies the exclusion rule.
- `specs/verification-architecture.md`: **extended PROP-101d's own fixture** (chose to extend rather
  than add a new PROP ID, since it is the same function under a broader input shape) to include a
  citizen with two ledger rows for one `child_id` (an earlier `"provisioning"` row, a later
  `"active"`-and-healthy or `"bootstrap_failed"` row) and asserts the LAST row's data is used, never the
  first. Purity Boundary Map row for `filterProductiveCitizens` (line 28) and for `ledger.js` (line 45)
  both now state the last-write-wins reduction and confirm `ledger.js` remains unmodified. Tier 0 list
  (lines 205-206) adds a structural check that `ledger.js` remains exactly `{readChildren, appendChild}`.
  Gate item (1b) (lines 297-306) now describes the reduction step explicitly.

---

## FIND-302 + FIND-303 (critical, same root gap) — coordinator can't reach a remote child's local files

**Investigation performed before deciding the fix** (all files read in full):
- `~/anicca/runtime/dashboard/telemetry-poster.mjs` and `telemetry-post-franklin.mjs`: both POST
  signed telemetry to a central, third-party-hosted endpoint (`https://aniccaai.com/.netlify/functions/
  telemetry`). This is a real, working cross-host-capable mechanism (a network POST), but (a) it is a
  ONE-WAY report to a Dais-owned public dashboard with no documented read-back/query API the
  coordinator could use to retrieve a citizen's current balance for a financial spawn decision, and
  (b) per this project's own `CLAUDE.md` aniccaai.com write-restriction table, Anicca-side consumption
  of that public surface for an autonomous spend decision is architecturally the wrong layer.
- `~/anicca/skills/self/telemetry-collect.sh` (read in full): queries PUBLIC RPC (Base/Solana/Polygon)
  by each instance's own KNOWN WALLET ADDRESS — hardcoded to today's 3 instances
  (anicca-a3cdd4/Franklin/claude-p) — and writes a local `telemetry.json`. Critically, the RPC QUERY
  itself has zero dependency on the querying process's physical location: it works identically whether
  run from the Mac Mini or from any other host, because it is keyed on a public wallet address, not a
  local file.
- **Decision: generalize `telemetry-collect.sh`'s RPC-by-`walletAddress` pattern, not the
  telemetry-poster central-endpoint route.** Reasoning: less new surface (no dependency on a
  third-party dashboard's undocumented internal storage/read API, no aniccaai.com write-path
  entanglement), directly reuses an already-proven, already-working mechanism, and requires only a
  registry-driven generalization (loop over `citizens[].walletAddress` instead of 3 hardcoded
  constants) rather than inventing a new read-back API for the public dashboard.
- `~/anicca/skills/earn/lib/resolve-identity.mjs` (read in full): `resolveEvmPrivateKey`/
  `resolveSolanaSecret` are confirmed to be pure `fs.readFileSync` primitives with no network path —
  structurally cannot reach a remote child's disk, and the child must never transmit its private key
  over the network for comparison (would violate REQ-201's key-handling discipline). REQ-106's own
  precedent ("this increment only, future work for multi-host") was reused verbatim for REQ-403's
  scoping fix.

**Fix:**
- REQ-101 (`specs/behavioral-spec.md`, lines ~203-222): balance lookup redefined from `fs.readFile` of
  a per-citizen `telemetryPath` to a new, coordinator-run, registry-driven `readCitizenBalances
  ({citizens})` public-RPC query keyed on `walletAddress`, generalizing `telemetry-collect.sh`.
  `telemetryPath` is REMOVED from REQ-105's schema.
- REQ-101 Edge Cases: rewritten to cover RPC failure (fail-closed to 0) and native-token normalization
  via the SAME already-proven `solPrice()` Coinbase-spot pattern (`telemetry-post-franklin.mjs`).
- REQ-105 (lines ~449-468): schema reduced from two extra fields to one (`homeDir` only); seed JSON
  literal (lines ~477-497) has `telemetryPath` removed from both entries; Acceptance Criteria updated.
- REQ-305 (lines ~1049-1061, 1112-1117): appended registry record no longer includes `telemetryPath`.
- REQ-403 (renamed header + full rewrite, lines ~1296-1349): EARS split into two independently-scoped
  halves; a new "Scoping correction" paragraph explains why the live-comparison half is confined to
  co-located instances this increment (today: automaton + Franklin), with a cloud-hosted child EXEMPT
  until a future increment adds a remote self-check mechanism; the static grep-sweep half is confirmed
  unaffected because a cloud child boots from the same git-cloned repo the grep already covers.
- `specs/verification-architecture.md`: Purity Boundary Map rows for `citizens.json` (line 25),
  `readCitizenBalances` (line 34, full rewrite), `resolve-identity.mjs` (line 38), and the REQ-403 audit
  script (line 47) all updated. New Proof Obligations PROP-101e (registry-driven RPC mechanism, Tier 2)
  and PROP-403d (structural check that the live comparison never includes a cloud child, Tier 0);
  PROP-101c reframed from "telemetry.json missing" to "RPC query failure"; PROP-403b rewritten to scope
  to co-located instances and explicitly drop the Tier-3 "extend to an actual spawned child" claim.
  Verification tiers narrative and Gate items (1a), (1c) [new], (11) updated accordingly.

---

## FIND-304 (major) — wallet field 3-way shape collision

**Confirmed real:** `child-spec.js:37` (`wallet: childWallet`, a bare string) and its test
(`child-spec.test.js:36`) vs. `citizens.json`'s `wallet: {evm?: boolean, solana?: boolean}` (REQ-105) —
two unrelated fields sharing a name across two files this feature touches, never previously flagged.

**Fix (documentation-only, no schema/code change to either file):**
- REQ-206 (`specs/behavioral-spec.md`, new paragraph inserted after the existing "returned row shape"
  sentence, ~lines 798-808): explicit disambiguation note.
- REQ-305 (new paragraph inserted after the registry-append description, ~lines 1064-1071): a
  cross-file disambiguation note pointing out the SAME child's `ledger.js` row already has a string
  `wallet` (from `buildChildSpec`) distinct from the boolean `wallet` object appended to `citizens.json`
  moments later in the same requirement.
- `specs/verification-architecture.md`: disambiguation notes added to the `child-spec.js` Purity
  Boundary Map row (line 30) and the `ledger.js` row (line 45). New Proof Obligation PROP-206h (Tier 0,
  structural cross-assignment check) and Gate item (4a) extended to require the adversary confirm no
  code path conflates the two `wallet` fields.

---

## FIND-305 (major) — REQ-306's false price-oracle reuse claim

**Confirmed real:** `akt-treasury.sh` (read in full) has no live USD price query — only native-unit
(`uact`/`uakt`) balance comparisons; its `P_mint≈0.66` is a one-time historical comment. A repo-wide
grep (`nosana|market.*price|SOL.*price`, case-insensitive, across `~/anicca/skills`) found no NOS/USD
or AKT/USD utility. Checked `~/anicca/skills/earn/sol-trade` and `hl-trade` (both read/greped) — neither
calls a SOL/AKT/NOS-USD rate API either.

**What WAS found and reused:** `runtime/dashboard/telemetry-poster.mjs::ethPrice()`,
`runtime/dashboard/telemetry-post-franklin.mjs::solPrice()`, and `skills/earn/execute-invest.mjs`'s own
`ethPrice()` — three existing, already-used instances of the SAME minimal pattern: one `fetch()` to a
public Coinbase spot-price endpoint, parsed to a number, fail-closed to `0` on error.

**Fix:** REQ-306's edge case (`specs/behavioral-spec.md`, ~lines 1156-1171) is rewritten to (a) state
plainly that no already-available price-conversion mechanism exists for AKT-USD or NOS-USD, citing the
real evidence above, and (b) specify a genuinely NEW, minimal price-fetch step — one public spot-price
API call per native token — that reuses the SAME already-proven pattern (`ethPrice()`/`solPrice()`),
reusing `solPrice()` as-is if Nosana's market is SOL-denominated. `specs/verification-architecture.md`:
new Purity Boundary Map row (line 43) for the new price-fetch step, updated `readCitizenBalances` row
(line 34) noting the same pattern is reused there too, new Proof Obligation PROP-306e (fail-closed
behavior, Tier 1/2), and Gate item (8a) extended to require the adversary confirm the corrected,
honest framing.

---

## Summary of what was NOT changed

- `ledger.js` source: byte-identical, still exactly `{readChildren, appendChild}` (FIND-301's own
  constraint).
- `child-spec.js` source: byte-identical (FIND-304 is documentation-only).
- No `state.json`, review manifest, or verdict file touched, per instructions.
- No commit/push performed.
