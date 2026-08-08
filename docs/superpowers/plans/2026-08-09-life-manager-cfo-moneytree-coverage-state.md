# Life Manager CFO Moneytree Coverage State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Represent Moneytree consent, retrieval, aggregation-time, and liability coverage truth without turning missing provider metadata into a fresh/complete claim.

**Architecture:** One pure state normalizer sits beside the completed Moneytree value adapter. It distinguishes a successful connector retrieval from Moneytree's underlying aggregation freshness, and represents unexposed liabilities as `coverage: "unknown", count: null`, never zero. Synthetic states cover authorized, expired, revoked, and outage paths; the live App path proves the honest `interactive_success + aggregation unknown + liabilities unknown` result.

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
| `apps/life-call/lib/cfo-moneytree-state.js` | Closed state contract and invariants | 90 production LOC; max 108 |
| `apps/life-call/lib/cfo-moneytree-state.test.js` | Literal state matrix and invalid mutations | 150 test LOC; max 180 |
| `apps/life-call/package.json` | Add state test once to `test:cfo` | +1 LOC |
| This plan and two CFO specs | Closure evidence only | +14 LOC |

## Closed Interface

```js
deriveMoneytreeState({
  signal: "interactive_success" | "authorized" | "expired" | "revoked" | "provider_outage",
  observedAt: "2026-08-09T06:00:00+09:00",
  aggregationAsOf: null,
  liabilitiesExposed: false,
  liabilityCount: null,
}) => {
  schemaVersion: 1,
  sourceId: "moneytree_mufg",
  retrievalStatus: "succeeded" | "unavailable",
  consentStatus: "valid" | "expired" | "revoked" | "unknown",
  consentEvidence: "interactive_session" | "provider_metadata" | "provider_error",
  aggregationStatus: "provider_reported" | "unknown",
  aggregationAsOf: string | null,
  liabilityCoverage: "complete" | "unknown",
  liabilityCount: number | null,
  partial: boolean,
  actionRequired: null | { kind: "reconsent" | "provider_outage", actionRef: "action:moneytree_reconsent" | "action:moneytree_outage" },
}
```

---

### Task 1: Closed consent/freshness/liability state

**Files:**
- Create: `apps/life-call/lib/cfo-moneytree-state.js`
- Create: `apps/life-call/lib/cfo-moneytree-state.test.js`
- Modify: `apps/life-call/package.json`

- [ ] **Step 1: Write RED state matrix tests**

Assert exact objects for:

1. `interactive_success`: retrieval succeeded, consent valid from `interactive_session`, aggregation unknown/null, liabilities unknown/null, partial true, no action.
2. `authorized` with explicit RFC3339 aggregation time and `liabilitiesExposed: true, liabilityCount: 0`: provider-reported aggregation, complete zero liabilities, partial false, no action.
3. `expired` and `revoked`: retrieval unavailable, matching consent, aggregation unknown/null, liabilities unknown/null, partial true, fixed reconsent action.
4. `provider_outage`: retrieval unavailable, consent unknown from provider error, unknown aggregation/liabilities, partial true, fixed outage action.

Assert exact input/root/action key sets and deep freeze. Add invalid mutations for unknown keys/signal, invalid timestamp, aggregation timestamp without `authorized`, authorized metadata without timestamp, `liabilitiesExposed:false` with any numeric count, exposed liabilities with null/negative/float/unsafe count, exposed liabilities on any non-`authorized` signal, and secret/raw-shaped extra values.

- [ ] **Step 2: Run RED**

```bash
cd apps/life-call
node --test lib/cfo-moneytree-state.test.js
```

Expected: module missing.

- [ ] **Step 3: Implement minimal pure normalizer**

Use exact key sets and one literal branch table. Validate RFC3339 timestamps with explicit calendar/clock/offset bounds. Construct output from constants only, `structuredClone`, recursively freeze, and emit only `moneytree_state_invalid:<reason>`.

- [ ] **Step 4: GREEN, regression, sizes, commit, push, review**

```bash
cd apps/life-call
node --test lib/cfo-moneytree-state.test.js
npm run test:cfo
npm ci --no-audit --no-fund
npm test
test "$(wc -l < lib/cfo-moneytree-state.js)" -le 108
test "$(wc -l < lib/cfo-moneytree-state.test.js)" -le 180
cd ../..
git diff --check
```

Commit `feat(cfo): model Moneytree coverage state`, push, and pass a fresh task review.

---

### Task 2: Live App truth check and CFO-1b2 closure

**Files:**
- Modify: this plan
- Modify: `docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md`
- Modify: `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`

- [ ] **Step 1: Verify the live App state without values**

Call `show_accounts(locale="ja")` once. A successful connected MUFG read feeds only:

```js
deriveMoneytreeState({
  signal: "interactive_success",
  observedAt: new Date().toISOString(),
  aggregationAsOf: null,
  liabilitiesExposed: false,
  liabilityCount: null,
})
```

Verify exact result: succeeded retrieval, valid interactive consent evidence, aggregation unknown/null, liability coverage unknown/count null, partial true, no action. Emit/store only booleans; do not print or persist provider response or balances.

- [ ] **Step 2: Final review and truthful state closure**

After controller tests and a clean fresh whole-plan review, check only parent CFO-1b2 and make CFO-1e active. Do not check the child persistence acceptance because persistence remains CFO-1g. Record that live liability coverage and aggregation freshness remain unknown; keep snapshot/Telegram/cloud boxes unchecked. Commit `docs(cfo): close Moneytree coverage state` and push.
