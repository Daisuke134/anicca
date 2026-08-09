# Life Manager CFO Moneytree Coverage State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Represent Moneytree consent, retrieval, aggregation-time, and liability coverage truth without turning missing provider metadata into a fresh/complete claim.

**Architecture:** One pure state normalizer sits beside the completed Moneytree value adapter, and one pure composer binds both into a single downstream read bundle. It distinguishes a successful connector retrieval from Moneytree's underlying aggregation freshness, and represents unexposed liabilities as `coverage: "unknown", count: null`, never zero. Synthetic states cover authorized fresh/stale/unknown-liability, expired, revoked, and outage paths; the live App path proves the honest `interactive_success + aggregation unknown + liabilities unknown` bundle.

**Tech Stack:** Node.js 20+, CommonJS, `node:test`; no new dependency.

## Global Constraints

- Active scope is CFO-1b2 only. Do not add persistence/snapshot, scheduler/cloud credential, Telegram, Fleet, valuation, Binance, tax, advice, retry, or browser fallback.
- The installed Moneytree App exposes balances/transactions but no provider aggregation timestamp, liability group, consent expiry, or revocation metadata. Missing fields remain visible unknowns.
- `retrievalStatus: "succeeded"` means this connector call succeeded; it never implies `aggregationStatus: "fresh"`.
- `liabilityCoverage: "unknown"` requires `liabilityCount: null`. Zero is allowed only with explicit `complete` provider evidence.
- Expired/revoked consent produces one redacted `reconsent` action; outage produces `provider_outage`; errors never interpolate input.
- No owner data or live amount enters Git/report. RED precedes production. Each code task ends with review, commit, and push.

## File Map and Size Targets

| File | Responsibility | Soft target |
|---|---|---:|
| `apps/life-call/lib/cfo-financial-source.js` | Permit unknown-consent provider outage without weakening reconsent | +4 LOC; total max 144 |
| `apps/life-call/lib/cfo-financial-source.test.js` | Outage/reconsent regression matrix | +18 LOC |
| `apps/life-call/lib/cfo-moneytree-state.js` | Closed state contract, source composition, and invariants | 120 production LOC; max 144 |
| `apps/life-call/lib/cfo-moneytree-state.test.js` | Literal state matrix, composition, and invalid mutations | 190 test LOC; max 228 |
| `apps/life-call/package.json` | Add state test once to `test:cfo` | +1 LOC |
| This plan and two CFO specs | Closure evidence only | +14 LOC |

## Closed Interface

```js
deriveMoneytreeState({
  signal: "interactive_success" | "authorized" | "expired" | "revoked" | "provider_outage",
  observedAt: "2026-08-09T06:00:00+09:00",
  aggregationAsOf: null,
  aggregationFreshnessCutoff: null,
  liabilitiesExposed: false,
  liabilityCount: null,
}) => {
  schemaVersion: 1,
  sourceId: "moneytree_mufg",
  retrievalStatus: "succeeded" | "unavailable",
  consentStatus: "valid" | "expired" | "revoked" | "unknown",
  consentEvidence: "interactive_session" | "provider_metadata" | "provider_error",
  observedAt: "2026-08-09T06:00:00+09:00",
  aggregationStatus: "fresh" | "stale" | "unknown",
  aggregationAsOf: string | null,
  liabilityCoverage: "complete" | "unknown",
  liabilityCount: number | null,
  partial: boolean,
  actionRequired: null | { kind: "reconsent" | "provider_outage", actionRef: "action:moneytree_reconsent" | "action:moneytree_outage" },
}

composeMoneytreeRead({ source, state }) => Readonly<{
  schemaVersion: 1,
  source: FinancialSourceResult,
  state: MoneytreeCoverageState,
}>
```

---

### Task 1: Correct provider-outage source contract

**Files:**
- Modify: `apps/life-call/lib/cfo-financial-source.js`
- Modify: `apps/life-call/lib/cfo-financial-source.test.js`

- [x] **Step 1: RED — unknown consent with outage action**

Add a literal unavailable source with `consent: "unknown"`, unavailable/null account value, `partial: true`, and `{ kind: "provider_outage", sourceLabel: "Moneytree", actionRef: "action:moneytree_outage" }`. It must validate and freeze. Add negative cases: unknown consent with null/reconsent action, and expired/revoked consent with outage action must fail.

- [x] **Step 2: GREEN — split unknown outage from expired/revoked reconsent**

Keep valid-consent rules unchanged. Require expired/revoked consent to use `reconsent`; require unknown consent to use `provider_outage`; all non-valid states remain unavailable and partial. Run contract/CFO tests, keep production at or below 144 LOC, diff check, commit `fix(cfo): distinguish provider outage consent`, push, and pass fresh review.

Evidence: commit `28be202ef`; RED 25/27, GREEN contract 27/27 and CFO 128/128; production 138 LOC; fresh review Approved with no findings.

---

### Task 2: Closed consent/freshness/liability state and source composition

**Files:**
- Create: `apps/life-call/lib/cfo-moneytree-state.js`
- Create: `apps/life-call/lib/cfo-moneytree-state.test.js`
- Modify: `apps/life-call/package.json`

- [x] **Step 1: Write RED state matrix tests**

Assert exact objects for:

1. `interactive_success`: retrieval succeeded, consent valid from `interactive_session`, aggregation unknown/null, liabilities unknown/null, partial true, no action.
2. `authorized` with explicit RFC3339 aggregation time/cutoff and `liabilitiesExposed: true`: newer timestamp becomes fresh; older timestamp becomes stale. Cover both zero and positive liability counts; partial false, no action.
3. `authorized` with no aggregation metadata and liabilities unexposed: aggregation unknown/null, liabilities unknown/null, partial true.
4. `expired` and `revoked`: retrieval unavailable, matching consent, aggregation unknown/null, liabilities unknown/null, partial true, fixed reconsent action.
5. `provider_outage`: retrieval unavailable, consent unknown from provider error, unknown aggregation/liabilities, partial true, fixed outage action.

Assert exact input/root/action key sets and deep freeze. Add invalid mutations for unknown keys/signal, invalid timestamp/cutoff, only one of timestamp/cutoff, aggregation metadata without `authorized`, `liabilitiesExposed:false` with any numeric count, exposed liabilities with null/negative/float/unsafe count, exposed liabilities on any non-`authorized` signal, and secret/raw-shaped extra values.

Add successful composition tests for all five signals using validated literal source results, including the corrected unknown-consent provider-outage source. The interactive case also uses real `adaptMoneytreeAccounts` output. Require matching `sourceId`, `source.asOf === state.observedAt`, consent agreement, retrieval succeeded↔source available and unavailable↔source unavailable, identical partial flag, complete-liability count agreement, and matching action kind/ref. Availability/action/consent/partial/liability mismatches fail with stable redacted errors. Assert exact bundle keys and deep freeze.

- [x] **Step 2: Run RED**

```bash
cd apps/life-call
node --test lib/cfo-moneytree-state.test.js
```

Expected: module missing.

- [x] **Step 3: Implement minimal pure normalizer**

Use exact key sets and one literal branch table. Validate RFC3339 timestamps with explicit calendar/clock/offset bounds; compare `aggregationAsOf` to the required cutoff for fresh/stale. Construct output from constants only, `structuredClone`, recursively freeze, and emit only `moneytree_state_invalid:<reason>`. `composeMoneytreeRead` first revalidates the financial source and coverage state, then enforces the cross-contract invariants above.

- [x] **Step 4: GREEN, regression, sizes, commit, push, review**

```bash
cd apps/life-call
node --test lib/cfo-moneytree-state.test.js
npm run test:cfo
npm ci --no-audit --no-fund
npm test
test "$(wc -l < lib/cfo-moneytree-state.js)" -le 144
test "$(wc -l < lib/cfo-moneytree-state.test.js)" -le 228
cd ../..
git diff --check
```

Commit `feat(cfo): model Moneytree coverage state`, push, and pass a fresh task review.

Evidence: commits `5325dab07`, `d4d77ae63`, `563c7fde0`, and `eed2be718`; final focused 37/37, CFO 165/165, full suite 798/798; production 133 LOC and tests 185 LOC. Three adversarial error-authenticity rounds close prefix spoofing, constructor reuse, and mutated same-object replay; scoped re-review says ADDRESSED with no new Critical/Important findings.

---

### Task 3: Live App truth check and CFO-1b2 closure

**Files:**
- Modify: this plan
- Modify: `docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md`
- Modify: `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`

- [x] **Step 1: Verify the live App state without values**

Call `show_accounts(locale="ja")` once. A successful connected MUFG read feeds only:

```js
deriveMoneytreeState({
  signal: "interactive_success",
  observedAt: new Date().toISOString(),
  aggregationAsOf: null,
  aggregationFreshnessCutoff: null,
  liabilitiesExposed: false,
  liabilityCount: null,
})
```

Compose this state with the live `adaptMoneytreeAccounts` result. Verify exact bundle: succeeded retrieval, valid interactive consent evidence, aggregation unknown/null, liability coverage unknown/count null, partial true, no action, matching source/state IDs/timestamps/partiality. Emit/store only booleans; do not print or persist provider response or balances.

Evidence: One corrected privacy-safe live Moneytree/MUFG read followed a synthetic no-echo probe. All 11/11 boolean composition checks were true: bundle creation; matching source/state IDs, timestamps, and partial flags; successful retrieval; valid `interactive_session` consent; unknown/null aggregation; unknown/null liability coverage/count; `partial=true`; no action; and deep freeze. The check exited 0 with `providerPayloadEchoed=false`; no raw payload was persisted or committed. An initial TTY validation exposed the provider response in transient tool output; it persisted and committed nothing, and was corrected with a synthetic-tested no-echo transport plus the durable rule pointer `.claude/rules/private-payload-transport.md`.

- [x] **Step 2: Final review and truthful state closure**

After controller tests and a clean fresh whole-plan review, check only parent CFO-1b2 and make CFO-1e active. Do not check the child persistence acceptance because CFO-1g explicitly persists this bundle. Record that live liability coverage and aggregation freshness remain unknown; keep snapshot/Telegram/cloud boxes unchecked. Commit `docs(cfo): close Moneytree coverage state` and push.

Evidence: Controller fresh final verification at fixed code head `57dab5ecb` passed focused state tests 38/38 and CFO tests 166/166; `npm ci --no-audit --no-fund` completed and full `npm test` exited 0. Production size is 137 LOC and tests are 195 LOC. The final whole-plan review found one changing-get Proxy Important, fixed by `57dab5ecb`; the final scoped re-review marked it ADDRESSED with no new Critical/Important findings and Ready status.
