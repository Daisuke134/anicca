# Life Manager CFO Fleet Read Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize the existing Fleet dashboard into one privacy-safe organizational-scope result whose valuation is upstream chain-enriched, whose token inflow is chain-observed but not recognized revenue, and whose burn remains visibly estimated.

**Architecture:** `apps/life-call` receives the existing post-signature, post-chain-enrichment dashboard JSON and applies an injected registered-wallet boundary. A closed validator owns the normalized result schema; a separate pure adapter owns parsing, identity comparison, evidence gating, HMAC references, and unknown-state mapping. CFO-1e does not change Fleet producers, copy a ledger, persist data, convert to JPY, or send Telegram.

**Tech Stack:** Node.js 20+, CommonJS, built-in `node:crypto`, built-in `node:test`, `assert/strict`, existing npm scripts only.

**Status:** ACTIVE — Task 1 complete; Task 2 next. Three fresh plan reviews found and closed every
Critical/Important issue; the final plan re-review returned `ship — Ready: yes`.

## Global Constraints

- Source design: `docs/superpowers/specs/2026-08-09-life-manager-cfo-fleet-read-design.md`.
- Parent SSOT: `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`; only CFO-1e is active.
- Use the existing per-wallet `leaderboard` response from `https://aniccaai.com/.netlify/functions/dashboard-sync`; never use root totals for normalized amounts.
- `net_worth_src="chain"` is required for an available wallet valuation, but its status is only `upstream_chain_enriched` because quote value/time are absent.
- `earn_src="chain"` is required for an available nominal stablecoin token inflow, but its status is only `chain_observed_token_inflow`; it is not earnings or recognized revenue.
- Label the inflow window exactly `approx_1200000_blocks`; never call it day, month, MTD, earnings, or calendar-period revenue.
- `burn_day_usd` is at most `signed_self_reported`; it never becomes chain-observed, provider-reported, or verified burn.
- Missing, unverified, invalid, negative, non-finite, wrong-chain, or absent data becomes `null` plus an exception; it never becomes zero.
- A verified numeric zero remains an available zero.
- `registeredWallets` is the organizational Fleet boundary, not personal economic ownership. Unknown dashboard wallets are ignored, missing registered wallets remain visible, and the result cannot enter personal net worth without a separate owner mapping.
- EVM wallet comparison is lowercase; Solana comparison is case-sensitive. Duplicate normalized identities fail closed.
- Never emit or persist raw wallet IDs, signatures, host, geo, model, status, provider payload, root totals, secret-shaped values, or financial amounts as live closure evidence.
- References use HMAC-SHA256, economic-scope binding, separate account/evidence domains, and 24 lowercase hex characters. `referenceKey` is at least 32 UTF-8 bytes. Evidence preimages bind metric, normalized wallet, chain, telemetry timestamp, upstream status, normalized value, and window where applicable.
- Exact result objects, dense arrays, safe timestamps, cloned output, recursive freeze, stable redacted errors, hostile accessors, custom prototypes, sparse arrays, and changing Proxies are required.
- No new dependency, service, database table, scheduler, retry loop, agent, network write, JPY conversion, Telegram send, business P&L, tax, trade, funding action, or Binance work.
- Task 1 soft target is 130 production/230 test LOC with mandatory simplification review above 160/300. Task 2 soft target is 100 production/240 test LOC with mandatory simplification review above 140/320. Both are atomic trust boundaries; splitting either would expose a coupled, unvalidated intermediate without an independent deliverable.
- Each implementation task changes at most three tracked files and closes with RED, GREEN, fresh review, commit, and push.
- Role split is fixed: the Sol controller writes specs, plans, task briefs, and state; Luna alone edits production
  code and tests; Sol reviewers are read-only. Code fixes return to Luna.

---

## File Map

| File | Responsibility |
|---|---|
| `apps/life-call/lib/cfo-fleet-source.js` | Validate, clone, and freeze the closed normalized Fleet result. |
| `apps/life-call/lib/cfo-fleet-source.test.js` | Contract, privacy, numeric, timestamp, hostile-object, and immutability tests. |
| `apps/life-call/lib/cfo-fleet.js` | Parse one dashboard response, enforce registered ownership, map evidence, and create opaque references. |
| `apps/life-call/lib/cfo-fleet.test.js` | Adapter truth mapping, identity, coverage, privacy, Proxy, and error tests. |
| `apps/life-call/package.json` | Register both focused tests exactly once in `test:cfo`. |
| `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md` | Mark CFO-1e complete with redacted live and verification evidence; activate CFO-1f. |
| `docs/superpowers/specs/2026-08-09-life-manager-cfo-fleet-read-design.md` | Record final status and bounded deviations only. |
| `docs/superpowers/plans/2026-08-09-life-manager-cfo-fleet-read.md` | Persist task state, commits, review, and verification evidence. |

## Task 1: Closed Fleet Source Result Contract

**Files:**
- Create: `apps/life-call/lib/cfo-fleet-source.js`
- Create: `apps/life-call/lib/cfo-fleet-source.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: the exact object documented in design section 4.1.
- Produces: `validateFleetSourceResult(input) => deeplyFrozenClone` from `apps/life-call/lib/cfo-fleet-source.js`.
- Errors: only `fleet_source_invalid:<fixed_reason>`; no input string appears in an error.

- [x] **Step 1: Write the RED contract tests**

Create a canonical valid object with exactly these values and keys:

```js
const VALID = {
  schemaVersion: 1,
  sourceId: "fleet_dashboard",
  economicScopeRef: "organization:anicca_fleet",
  readAsOf: "2026-08-09T12:00:00Z",
  sourceUpdatedAt: "2026-08-09T11:59:59Z",
  coverage: { registeredWalletCount: 1, presentWalletCount: 1, partial: true },
  wallets: [{
    accountRef: "source_account:fleet_aaaaaaaaaaaaaaaaaaaaaaaa",
    chain: "base",
    telemetryAsOf: "2026-08-09T11:59:30Z",
    telemetryFreshness: "fresh",
    walletValuation: {
      status: "available", asset: "fleet_wallet_aggregate", quantity: null,
      currency: "USD", valueUsd: 12.5, verificationStatus: "upstream_chain_enriched",
      evidenceRef: "evidence:fleet_bbbbbbbbbbbbbbbbbbbbbbbb",
    },
    externalStablecoinInflows: {
      status: "available", asset: "external_stablecoin_transfer_aggregate", quantity: 3.25,
      unit: "nominal_token_units", currency: null, window: "approx_1200000_blocks",
      verificationStatus: "chain_observed_token_inflow", evidenceRef: "evidence:fleet_cccccccccccccccccccccccc",
    },
    burnRate: {
      status: "available", amountUsdPerDay: 0.75, currency: "USD",
      verificationStatus: "signed_self_reported",
      evidenceRef: "evidence:fleet_dddddddddddddddddddddddd",
    },
  }],
  exceptions: [],
  limitations: [
    "asset_positions_unavailable",
    "valuation_quote_provenance_unavailable",
    "inflows_not_recognized_revenue",
    "inflow_window_approximate",
    "burn_estimated",
    "economic_owner_mapping_unavailable",
  ],
};
```

Test exact root/nested key sets; `economicScopeRef` exactly `organization:anicca_fleet` and human scope rejection; exact constants; `available` and `unknown` state pairs; verified zero; finite non-negative numbers; counts; unique account references; exception enums; dense arrays; RFC3339 calendar validity; `sourceUpdatedAt <= readAsOf + 5 seconds`; `telemetryAsOf <= sourceUpdatedAt + 5 seconds`; exact five-second boundaries; `telemetryFreshness="fresh"` through a 300-second age and `"stale"` above it; freshness-label mismatches; custom prototypes; accessors; Symbols; sparse arrays; functions; cycles; mutation after return; recursive freeze; changing-get Proxy snapshot safety; and a secret-shaped invalid string whose thrown message is still only a fixed reason. Include these invalid pair checks:

```js
[
  ["available_without_value", (v) => { v.wallets[0].walletValuation.valueUsd = null; }],
  ["unknown_with_value", (v) => {
    v.wallets[0].walletValuation.status = "unknown";
    v.wallets[0].walletValuation.verificationStatus = "unavailable";
  }],
  ["unknown_with_evidence", (v) => {
    v.wallets[0].burnRate.status = "unknown";
    v.wallets[0].burnRate.amountUsdPerDay = null;
    v.wallets[0].burnRate.verificationStatus = "unavailable";
  }],
  ["negative_amount", (v) => { v.wallets[0].externalStablecoinInflows.quantity = -1; }],
  ["wrong_window", (v) => { v.wallets[0].externalStablecoinInflows.window = "month"; }],
  ["complete_claim", (v) => { v.coverage.partial = false; }],
  ["count_mismatch", (v) => { v.coverage.presentWalletCount = 0; }],
]
```

For each unknown mutation, leave the old evidence reference intact so the validator must reject the inconsistent state.

- [x] **Step 2: Run the focused test and prove RED**

Run:

```bash
cd apps/life-call
node --test lib/cfo-fleet-source.test.js
```

Expected: non-zero exit because `./cfo-fleet-source` does not exist. Record only the failing test count and missing-module reason in the plan state.

- [x] **Step 3: Implement the minimum closed validator**

Implement only these helpers inside `cfo-fleet-source.js`:

```js
function fail(reason) { throw new Error(`fleet_source_invalid:${reason}`); }
function snapshot(input) { /* descriptor-only recursive JSON snapshot; reject accessors/proxies/non-plain/sparse */ }
function exactKeys(value, allowed) { /* require every and only enumerable string data key */ }
function timestamp(value) { /* strict RFC3339 plus real calendar/time-zone validation */ }
function amount(value) { /* finite number and value >= 0 */ }
function metric(value, kind) { /* exact constants and available/unknown invariants */ }
function exception(value) { /* exact accountRef/field/reason enums */ }
function freeze(value, seen = new WeakSet()) { /* recursive Object.freeze */ }
function validateFleetSourceResult(input) { /* snapshot once, validate snapshot only, return frozen snapshot */ }
module.exports = { validateFleetSourceResult };
```

The snapshot must read each property descriptor value once and later validation must use only that snapshot. The root requires schema version `1`, source ID `fleet_dashboard`, `economicScopeRef === "organization:anicca_fleet"`, `coverage.partial === true`, exact ordered limitations, and no duplicate `accountRef`. It independently enforces `sourceUpdatedAt <= readAsOf + 5 seconds`, each `telemetryAsOf <= sourceUpdatedAt + 5 seconds`, and the exact 300-second `telemetryFreshness` classification. It also requires `presentWalletCount === wallets.length` and `registeredWalletCount === wallets.length + count(field="wallet" and reason in {missing_registered_wallet, chain_mismatch})`; those absent-wallet exception references are unique and disjoint from emitted wallets. Every unknown wallet metric has exactly one exception with the same `accountRef` and matching field, while every available metric has none. Unknown metrics require amount `null`, `verificationStatus="unavailable"`, and `evidenceRef=null`; available metrics require a non-null amount, the exact positive verification status, and a typed evidence reference.

- [x] **Step 4: Register and prove GREEN**

Append `lib/cfo-fleet-source.test.js` exactly once to the existing `test:cfo` command in `apps/life-call/package.json`, then run:

```bash
cd apps/life-call
node --test lib/cfo-fleet-source.test.js
npm run test:cfo
wc -l lib/cfo-fleet-source.js lib/cfo-fleet-source.test.js
```

Expected: all focused and CFO tests pass. Compare LOC with the 130/230 soft targets; above 160/300 requires simplification review before acceptance. The validator remains one atomic trust boundary because splitting snapshot and cross-object invariants would create another coupled surface without an independently usable deliverable.

- [x] **Step 5: Fresh review, fix, verify, commit, and push**

The reviewer checks exact schema closure, unknown-not-zero, burn status, snapshot-once behavior, privacy-safe errors, immutability, test quality, and LOC. Fix every Critical/Important finding with a new failing regression first. Then run the Step 4 commands and:

```bash
git diff --check
git add apps/life-call/lib/cfo-fleet-source.js apps/life-call/lib/cfo-fleet-source.test.js apps/life-call/package.json
git commit -m "feat(cfo): define Fleet source contract"
git push canonical HEAD
```

Expected: clean diff check, commit created, push succeeds.

Task 1 evidence: Luna committed and pushed `5581468a3` and test-fix `2b87d969e`. RED was missing-module as
planned. Final focused tests passed 11/11 and CFO tests passed 177/177. Production is 215 LOC and tests are 349 LOC;
the mandatory simplification review accepted the atomic validator and explicit hostile-input matrix. The first
review found three test-path gaps; Luna fixed all three, and the re-review returned `Approved — ship` with no new
Critical/Important findings.

## Task 2: Fleet Dashboard Adapter

**Files:**
- Create: `apps/life-call/lib/cfo-fleet.js`
- Create: `apps/life-call/lib/cfo-fleet.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: `adaptFleetDashboard({ dashboardJson, observedAt, referenceKey, economicScopeRef, registeredWallets })` exactly as documented in design section 4.2; any scope except `organization:anicca_fleet` fails closed.
- Uses: `validateFleetSourceResult(result)` from Task 1.
- Produces: one validated, frozen `FleetSourceResult` containing only registered wallet rows and exceptions.
- Errors: only `fleet_adapter_invalid:<fixed_reason>` for adapter boundary failures; authenticated internal source-contract errors may be translated to `fleet_adapter_invalid:result_invalid`.

- [ ] **Step 1: Write the RED mapping tests**

Use a synthetic dashboard JSON string containing:

```js
const DASHBOARD = JSON.stringify({
  updated_at: "2026-08-09T11:59:59Z",
  total_net_worth_usd: 999999,
  leaderboard: [
    {
      id: "0xAABBCCDDEEFF0011223344556677889900AABBCC",
      chain: "base",
      ts: 1786276770,
      host: "private-host",
      geo: "private-geo",
      model_live: "private-model",
      net_worth_usd: 12.5,
      net_worth_src: "chain",
      revenue_mo_usd: 3.25,
      revenue_today_usd: 999,
      earn_src: "chain",
      burn_day_usd: 0.75,
      signature: "must-not-escape",
    },
    {
      id: "UNREGISTERED-WALLET",
      chain: "solana",
      ts: 1786276770,
      net_worth_usd: 500,
      net_worth_src: "chain",
      revenue_mo_usd: 500,
      earn_src: "chain",
      burn_day_usd: 500,
    },
  ],
});
```

Call with registered base wallet ID in lowercase and assert: the EVM row matches case-insensitively; the unregistered row is absent; root total, today value, private fields, IDs, and signatures are absent from serialized output; counts are 1/1; the valuation is `upstream_chain_enriched`; the inflow is `chain_observed_token_inflow` with nominal token units and is never named revenue; burn is `signed_self_reported`; source timestamps and the exact inflow window are preserved. Assert alternate human and organization scopes fail closed. For the accepted fixed scope, assert HMAC refs are stable for the same key/claim, differ across domain or key, and change when the metric value, telemetry timestamp, upstream status, chain, or window changes.

Add table-driven tests for:

```js
[
  ["net_worth_src", "unverified_source", "wallet_valuation"],
  ["earn_src", "unverified_source", "external_inflows"],
  ["missing_net_worth_usd", "missing_value", "wallet_valuation"],
  ["negative_revenue_mo_usd", "missing_value", "external_inflows"],
  ["nonfinite_burn_day_usd", "missing_value", "burn_rate"],
  ["wrong_chain", "chain_mismatch", "wallet"],
  ["missing_registered_wallet", "missing_registered_wallet", "wallet"],
]
```

Also test source-gated zeros; Solana case sensitivity; `polygon-proxy` registration with unavailable financial lanes; duplicate normalized registrations; malformed JSON; invalid observed/source/telemetry timestamps; telemetry more than five seconds after source; source more than five seconds after read; both five-second boundaries; freshness at exactly 300 seconds and just above it; wrong leaderboard type; sparse leaderboard/registry arrays; unknown dashboard keys ignored; input mutation; changing Proxies/accessors rejected or safely snapshotted; key shorter than 32 UTF-8 bytes; and stable redacted errors with secret-shaped hostile values.

- [ ] **Step 2: Run the focused test and prove RED**

Run:

```bash
cd apps/life-call
node --test lib/cfo-fleet.test.js
```

Expected: non-zero exit because `./cfo-fleet` does not exist. Record only failing count and missing-module reason.

- [ ] **Step 3: Implement the minimum adapter**

Implement only this module surface:

```js
const { createHmac } = require("node:crypto");
const { validateFleetSourceResult } = require("./cfo-fleet-source");

function fail(reason) { throw new Error(`fleet_adapter_invalid:${reason}`); }
function ref(referenceKey, economicScopeRef, domain, value) {
  const digest = createHmac("sha256", referenceKey)
    .update(`${economicScopeRef}\0${domain}\0${value}`, "utf8").digest("hex").slice(0, 24);
  return `${domain === "account" ? "source_account" : "evidence"}:fleet_${digest}`;
}
function normalizeIdentity(walletId, chain) {
  return chain === "solana" ? walletId : walletId.toLowerCase();
}
function claimPreimage(metric, id, chain, telemetryAsOf, sourceStatus, value, window = "") {
  const normalizedValue = Object.is(value, -0) ? "0" : JSON.stringify(value);
  return [metric, id, chain, telemetryAsOf, sourceStatus, normalizedValue, window].join("\0");
}
function adaptFleetDashboard(input) {
  // Snapshot each boundary once, map registered rows only, calculate freshness and claims,
  // then return validateFleetSourceResult(result).
}
module.exports = { adaptFleetDashboard };
```

Read `dashboardJson` exactly once as a primitive string, parse it exactly once, and create a descriptor-safe snapshot before inspecting the parsed value or registry. Require `sourceUpdatedAt <= readAsOf + 5 seconds`. Calculate `telemetryFreshness` from `sourceUpdatedAt - telemetryAsOf`: fresh through exactly 300 seconds, stale above it, and fail if telemetry is over five seconds after source. Account evidence binds `account`, normalized ID, and registered chain. Metric evidence uses the exact `claimPreimage` fields above; the HMAC is an integrity locator, not proof. Sort emitted wallets by `accountRef`; sort exceptions by `accountRef`, then field, then reason. For a present chain-matched row, emit all three metric objects: available only behind their source/value gates, otherwise unknown plus the exact exception. A missing registration emits no wallet row and one `missing_registered_wallet` exception with its derived `accountRef`. A chain mismatch emits no wallet row and one `chain_mismatch` exception. Ignore every unregistered dashboard row.

- [ ] **Step 4: Register and prove GREEN**

Append `lib/cfo-fleet.test.js` exactly once to `test:cfo`, then run:

```bash
cd apps/life-call
node --test lib/cfo-fleet.test.js
npm run test:cfo
wc -l lib/cfo-fleet.js lib/cfo-fleet.test.js
```

Expected: all focused and CFO tests pass. Compare LOC with the 100/240 soft targets; above 140/320 requires simplification review before acceptance. The adapter remains atomic because parsing, registered-scope filtering, and claim construction share one source trust boundary; splitting them would expose an unvalidated intermediate.

- [ ] **Step 5: Fresh review, fix, verify, commit, and push**

The reviewer checks ownership filtering, EVM/Solana casing, source gates, unknown-not-zero, approximate-window naming, burn truth level, deterministic HMAC domains, privacy, snapshot-once behavior, output sorting, and LOC. Fix every Critical/Important finding with a new failing regression first. Then run the Step 4 commands and:

```bash
git diff --check
git add apps/life-call/lib/cfo-fleet.js apps/life-call/lib/cfo-fleet.test.js apps/life-call/package.json
git commit -m "feat(cfo): adapt Fleet dashboard"
git push canonical HEAD
```

Expected: clean diff check, commit created, push succeeds.

## Task 3: Live Read, Whole-Slice Verification, and CFO-1e Closure

**Files:**
- Modify: `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`
- Modify: `docs/superpowers/specs/2026-08-09-life-manager-cfo-fleet-read-design.md`
- Modify: `docs/superpowers/plans/2026-08-09-life-manager-cfo-fleet-read.md`

**Interfaces:**
- Consumes: the Task 2 adapter and the repository's public wallet identities from `apps/landing/netlify/functions/_lib/leaderboard-constants.js` plus `FIXED_IDENTITIES` from `_lib/fixed-identities.js`.
- Produces: redacted live acceptance evidence containing only booleans, counts, coverage status, exit status, and a SHA-256 result hash.
- Transition: CFO-1e becomes complete only after fresh tests, live read, and final review pass; CFO-1f becomes the first unfinished item.

- [ ] **Step 1: Run a synthetic no-echo transport probe**

Use a temporary script outside the repository that feeds secret-shaped synthetic JSON through stdin with terminal echo disabled. The only stdout fields are:

```json
{"inputEchoed":false,"parsed":true,"exitCode":0}
```

If `inputEchoed` is true, stop the live probe, fix the transport, and repeat the synthetic check. Do not place payloads or financial values in shell arguments, environment variables, files, logs, spec text, Telegram, or tool-visible stdout.

- [ ] **Step 2: Perform one live read and privacy-safe adapter check**

Fetch exactly `https://aniccaai.com/.netlify/functions/dashboard-sync` in the no-echo controller. Build an independent registered-wallet list from the two repository modules named in this task without consulting live row chains: `OUR_INSTANCE_IDS[0]` is `base`; the `FIXED_IDENTITIES` entry whose host is `claude-p` is `polygon-proxy`; the entries whose hosts are `Franklin` and `Franklin2` are `solana`. Deduplicate by the adapter's chain-aware identity rule. This is the exact current owner/chain SSOT for the probe; a live row cannot self-assign its expected chain. Use an ephemeral 32-byte reference key and pass the response directly to `adaptFleetDashboard` without printing it.

The controller prints exactly this schema with no extra fields:

```js
{
  httpOk: boolean,
  resultCreated: boolean,
  sourceIdMatches: boolean,
  economicScopeMatches: boolean,
  registeredWalletCountPositive: boolean,
  presentWalletCountPositive: boolean,
  countsConsistent: boolean,
  coveragePartial: boolean,
  limitationsExact: boolean,
  allWalletsOpaque: boolean,
  allAvailableValuationsUpstreamChainEnriched: boolean,
  allAvailableInflowsAreTokenObservations: boolean,
  noInflowsNamedRevenue: boolean,
  allInflowsUseApproximateWindow: boolean,
  allAvailableBurnSignedSelfReported: boolean,
  unknownAmountsAreNull: boolean,
  outputDeepFrozen: boolean,
  providerPayloadEchoed: false,
  resultHash: "<sha256 hex>",
  exitCode: 0
}
```

No available metric count or amount is printed. `httpOk`, `resultCreated`, and `presentWalletCountPositive` must be true, and every truth/structure/privacy boolean must be true. Individual valuation, inflow, or burn metrics may honestly remain unknown; that does not fail the adapter. If no registered wallet is present, keep CFO-1e open and repair the source/registry boundary before retrying; do not manufacture success.

- [ ] **Step 3: Run fresh whole-slice verification**

Run from a dependency-clean state:

```bash
cd apps/life-call
npm ci --no-audit --no-fund
node --test lib/cfo-fleet-source.test.js lib/cfo-fleet.test.js
npm run test:cfo
npm test
wc -l lib/cfo-fleet-source.js lib/cfo-fleet-source.test.js lib/cfo-fleet.js lib/cfo-fleet.test.js
git diff --check
```

Expected: every command exits 0, focused/CFO/full suites pass, each file is at or below its complexity checkpoint or has been simplified, and diff check is clean.

- [ ] **Step 4: Run a fresh final review and close only verified findings**

The reviewer receives the design, plan, Task 1 and Task 2 diffs, fresh test output, LOC output, and the redacted live schema only. The reviewer checks all acceptance items and searches for Critical/Important findings. Every such finding gets a failing regression, minimum fix, fresh focused/full verification, and a separate fix commit before closure. A clean review or fully addressed re-review is required.

- [ ] **Step 5: Persist state, commit, push, and report the milestone**

Make these exact state changes:

```markdown
Parent status: CFO-1e COMPLETE — CFO-1f NEXT
First unfinished item: CFO-1f: add timestamped JPY valuation and staleness rules
CFO-1e checkbox: [x]
Focused design status: COMPLETE — CFO-1f NEXT
Plan status: COMPLETE
```

Record commit hashes, test counts, LOC counts, the boolean live acceptance fields, result hash, review outcome, known limitations, and the next item. Never record live amounts or wallet identities. Then run:

```bash
git add docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md docs/superpowers/specs/2026-08-09-life-manager-cfo-fleet-read-design.md docs/superpowers/plans/2026-08-09-life-manager-cfo-fleet-read.md
git commit -m "docs(cfo): close Fleet read"
git push canonical HEAD
git status --short
```

Expected: commit and push succeed; final status is empty. Send one natural-language Telegram milestone beginning `Codex:::` with what changed, what failed and was repaired, actual verification results, remaining limitations, and CFO-1f as the next item. Confirm and record the provider message ID without sending Markdown files or raw logs.

## Completion Boundary

CFO-1e is complete only when Tasks 1–3 are checked, both production contracts pass adversarial tests, the live endpoint creates a privacy-safe result, full `apps/life-call` tests pass from a clean dependency install, fresh review is clear, all state files are pushed, and the Telegram milestone has a provider receipt. The first daily personal finance Telegram report remains CFO-1h after CFO-1f, CFO-1g, CFO-1g2, CFO-1g3, and CFO-1h2; this plan must not claim that report exists.
