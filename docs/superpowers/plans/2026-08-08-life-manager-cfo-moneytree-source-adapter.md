# Life Manager CFO Moneytree Source Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the installed Moneytree App's MUFG account and transaction reads into the CFO's privacy-safe normalized contracts, then prove the mapping against the live connected account without persisting raw provider data.

**Architecture:** One pure CommonJS adapter parses JSON strings at the provider boundary, allowlists only required fields, derives stable opaque references with a tenant-scoped HMAC key, and delegates balance truth checks to the existing financial-source validator. A separate closed transaction projection carries only date, signed amount, currency, flow, opaque references, and provider-reported status; merchant descriptions, account numbers, provider IDs, URLs, and raw payloads never leave the adapter. The live interactive verification streams the Moneytree responses through the adapter in memory and emits only a redacted boolean/count receipt.

**Tech Stack:** Node.js 20+, CommonJS, `node:test`, Node `crypto`, installed Moneytree App connector; no new dependency.

## Global Constraints

- Approved design: `docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md` §§4–5.
- Active scope is CFO-1b only: Moneytree-connected MUFG balances and transactions. Do not implement liabilities/consent recovery (CFO-1b2), persistence/snapshot/dedupe, Telegram send, Fleet, valuation, self-heal, Binance, tax, business P&L, or spending advice.
- The interactive Moneytree App is the pilot read path. It is not a cloud credential or scheduled production adapter.
- RED is observed before production code in each implementation task.
- Raw provider payloads, full account numbers, provider account/transaction IDs, transaction descriptions, connection URLs, credentials, and owner data never enter Git, specs, test fixtures, reports, stdout, Telegram, or OTel.
- Provider JSON exists in process memory only for the live check. The live checker prints only boolean/count assertions and opaque references; it never prints amounts or source strings.
- Output account and transaction references are HMAC-derived from a tenant-scoped key of at least 32 UTF-8 bytes. Raw IDs are never concatenated into references.
- Amounts are safe integer minor units. Successful values are `provider_reported`; unknown is never zero.
- In CFO-1b, `observedAt` and `fresh` mean only that the interactive connector read succeeded at that retrieval time. They do not claim Moneytree's underlying aggregation timestamp or durable consent freshness; CFO-1b2 owns those truths.
- CFO-1b has not ingested liabilities, so its source result is always `partial: true` even after a successful live read.
- The adapter accepts only the Moneytree App `structuredContent` shapes observed from `show_accounts(locale="ja")` and `show_transactions(locale="ja")`; it does not persist the outer MCP envelope.
- No dependency addition. Only current-task files are staged. Each task closes with tests, diff check, commit, push, and fresh review.

## File Map and Size Targets

| File | Responsibility | Soft target |
|---|---|---:|
| `apps/life-call/lib/cfo-moneytree.js` | JSON boundary, HMAC refs, MUFG balance and transaction projections | 140 production LOC |
| `apps/life-call/lib/cfo-moneytree.test.js` | Synthetic provider-shape tests, truth/privacy/failure mutations | 220 test LOC |
| `apps/life-call/package.json` | Add the adapter test once to `test:cfo` | +1 LOC |
| This plan and parent/child CFO specs | Exact E2E and closure evidence only | +18 documentation LOC |

The implementation has two code tasks, each touching at most three files. If production exceeds 168 LOC or tests exceed 264 LOC, stop and simplify instead of adding a helper module, class, provider SDK, or generic adapter framework.

## Public Interfaces

```js
adaptMoneytreeAccounts({ accountsJson, observedAt, referenceKey })
  => Readonly<FinancialSourceResult>

adaptMoneytreeTransactions({ accountsJson, transactionsJson, observedAt, referenceKey })
  => Readonly<MoneytreeTransactionResult>
```

`accountsJson` and `transactionsJson` are JSON strings of the connector's `structuredContent`, not files or logged objects. `referenceKey` is a tenant-scoped secret string with at least 32 UTF-8 bytes.

The closed transaction result is:

```js
{
  schemaVersion: 1,
  sourceId: "moneytree_mufg",
  asOf: "2026-08-08T06:02:00+09:00",
  transactions: [{
    transactionRef: "transaction:mt_0123456789abcdef01234567",
    accountRef: "source_account:mt_0123456789abcdef01234567",
    bookingDate: "2026-08-06",
    amountMinor: 1234,
    currency: "JPY",
    flow: "inflow", // inflow | outflow | neutral, derived only from signed amount
    verificationStatus: "provider_reported",
  }],
  evidenceRef: "evidence:mt_0123456789abcdef01234567",
  pagePartial: true,
}
```

`pagePartial` is true exactly when the connector reports more matching transactions than the returned page. It describes transaction pagination only and MUST NOT be interpreted as source completeness. Transaction descriptions and provider categories are deliberately absent; spending classification is a later milestone.

---

### Task 1: MUFG balance projection

**Files:**
- Create: `apps/life-call/lib/cfo-moneytree.js`
- Create: `apps/life-call/lib/cfo-moneytree.test.js`

**Interfaces:**
- Consumes: `validateFinancialSourceResult(input)` from `./cfo-financial-source.js`.
- Produces: `adaptMoneytreeAccounts({ accountsJson, observedAt, referenceKey })` exactly as declared above.

- [x] **Step 1: Write the failing real-behavior tests**

Create a literal synthetic connector response with `type: "accounts"`, `data.baseCurrency: "JPY"`, one `mufg_bank` savings account, and decoy raw fields `institution_account_number: "9999999"`, `connectUrl: "https://secret.example/connect"`, numeric provider ID `1001`, and private nickname `"秘密口座"`. Use arbitrary balance `420000`.

Tests assert:

```js
const source = adaptMoneytreeAccounts({
  accountsJson: JSON.stringify(syntheticAccounts()),
  observedAt: "2026-08-08T06:02:00+09:00",
  referenceKey: "synthetic-reference-key-32-bytes-long",
});
assert.equal(source.sourceId, "moneytree_mufg");
assert.equal(source.consent, "valid");
assert.equal(source.freshness, "fresh");
assert.equal(source.partial, true);
assert.equal(source.accounts[0].label, "MUFG 普通預金");
assert.equal(source.accounts[0].balanceMinor, 420000);
assert.match(source.accounts[0].accountRef, /^source_account:mt_[a-f0-9]{24}$/);
assert.match(source.evidenceRef, /^evidence:mt_[a-f0-9]{24}$/);
assert.doesNotMatch(JSON.stringify(source), /9999999|secret\.example|1001|秘密口座/);
assert.equal(Object.isFrozen(source.accounts[0]), true);

const repeated = adaptMoneytreeAccounts(sameInput);
const otherTenant = adaptMoneytreeAccounts({ ...sameInput, referenceKey: "different-synthetic-reference-key-32" });
assert.equal(repeated.accounts[0].accountRef, source.accounts[0].accountRef);
assert.notEqual(otherTenant.accounts[0].accountRef, source.accounts[0].accountRef);
```

Add table-driven cases for invalid JSON, wrong root type, wrong `type`, missing data/groups, non-JPY base/account currency, non-integer/unsafe/null balance, missing/nonnumeric/unsafe provider ID, zero MUFG accounts, duplicate provider account ID, weak reference key, and invalid `observedAt`. Through the public account result, prove the same provider ID produces distinct account-reference and evidence-reference digest suffixes. All errors are stable `moneytree_adapter_invalid:<reason>` and never contain input values.

Before writing the test body, name the production mutation it catches: using `totalBalance`, copying raw label/ID, accepting unsafe money, emitting a reversible ref, weakening the key, or claiming a missing source is fresh.

- [x] **Step 2: Run RED**

```bash
cd apps/life-call
node --test lib/cfo-moneytree.test.js
```

Expected: FAIL because `./cfo-moneytree.js` does not exist.

- [x] **Step 3: Implement the minimum balance adapter**

Implement only:

1. `parseJson(value, expectedType)` rejects non-string/invalid/non-plain JSON roots and verifies `{ type, data }` before field access.
2. `opaqueRef(kind, referenceKey, providerId)` requires a string key of at least 32 UTF-8 bytes and a safe-integer provider ID, and returns the first 24 hex characters of `HMAC-SHA256(referenceKey, "moneytree:<kind>:<providerId>")` under the typed prefix. Account, transaction, and evidence domains are distinct.
3. Select accounts only from `data.accountGroups.banks` where `institutionKey === "mufg_bank"`. Reject zero matches and duplicate provider IDs. Do not consume `totalBalance`, nickname, institution name, account number, or `connectUrl`.
4. Map `account_subtype === "savings"` to fixed label `MUFG 普通預金` and kind `deposit`; map any other subtype to fixed label `MUFG 口座` and kind `other`.
5. Require JPY and safe integer `current_balance`; construct `consent: "valid"`, `freshness: "fresh"`, `liabilities: []`, `partial: true`, and `actionRequired: null`.
6. Derive one evidence ref with HMAC over the observed timestamp plus the parsed accounts response, then pass the result through `validateFinancialSourceResult` for clone/freeze and invariant enforcement.

Do not add storage, logging, raw-payload hashing without HMAC, callback abstractions, classes, retries, or provider clients.

- [x] **Step 4: Run GREEN, mutation checks, and size check**

```bash
cd apps/life-call
node --test lib/cfo-moneytree.test.js
test "$(wc -l < lib/cfo-moneytree.js)" -le 168
cd ../..
git diff --check
```

Manually mutate the account reference derivation to concatenate the raw ID and confirm a privacy test fails; restore the code and rerun GREEN.

- [x] **Step 5: Commit, push, and fresh task review**

```bash
git add apps/life-call/lib/cfo-moneytree.js apps/life-call/lib/cfo-moneytree.test.js
git commit -m "feat(cfo): adapt Moneytree MUFG balances"
git push canonical HEAD
```

Review gates: source-contract compliance, HMAC opacity, raw-field exclusion, partial truth, integer money, exact scope, and actual RED evidence.

---

### Task 2: Redacted transaction projection and normal test wiring

**Files:**
- Modify: `apps/life-call/lib/cfo-moneytree.js`
- Modify: `apps/life-call/lib/cfo-moneytree.test.js`
- Modify: `apps/life-call/package.json`

**Interfaces:**
- Consumes: the exact accounts JSON and HMAC helpers from Task 1.
- Produces: `adaptMoneytreeTransactions({ accountsJson, transactionsJson, observedAt, referenceKey })` exactly as declared above.

- [x] **Step 1: Write RED transaction tests**

Use two synthetic MUFG accounts with provider IDs `1001` and `1002`, then a `type: "transactions"` response containing three interleaved transactions: positive `1234` on the first account, negative `-500` on the second, and zero `0` on the first. Include decoy provider transaction IDs, full account numbers, merchant descriptions, institution names, provider category IDs/names, and running balances.

Assert literal outputs:

```js
assert.deepEqual(result.transactions.map((row) => row.flow), ["inflow", "outflow", "neutral"]);
assert.deepEqual(result.transactions.map((row) => row.amountMinor), [1234, -500, 0]);
assert.deepEqual(result.transactions.map((row) => row.bookingDate), ["2026-08-06", "2026-08-05", "2026-08-04"]);
assert.match(result.transactions[0].transactionRef, /^transaction:mt_[a-f0-9]{24}$/);
assert.equal(result.transactions[0].accountRef, source.accounts[0].accountRef);
assert.equal(result.transactions[1].accountRef, source.accounts[1].accountRef);
assert.equal(result.pagePartial, false);
assert.doesNotMatch(JSON.stringify(result), /9999999|merchant-secret|provider-category|1001|2001/);
assert.equal(Object.isFrozen(result.transactions[0]), true);

const rootKeys = ["asOf", "evidenceRef", "pagePartial", "schemaVersion", "sourceId", "transactions"];
const rowKeys = ["accountRef", "amountMinor", "bookingDate", "currency", "flow", "transactionRef", "verificationStatus"];
assert.deepEqual(Object.keys(result).sort(), rootKeys);
for (const row of result.transactions) assert.deepEqual(Object.keys(row).sort(), rowKeys);
```

Add failures for invalid transaction JSON/type/required shape, invalid or impossible booking date, float/unsafe/string amount, non-JPY currency, missing/nonnumeric/unsafe/duplicate transaction ID, unknown/unsafe account ID, duplicate transaction ref, negative/float/unsafe/string `totalCount`, and total count smaller than page length. Raw provider extras remain ignored rather than copied. Add one pagination case proving `pagePartial === (totalCount > transactions.length)`, never a false complete state. Repeat the same input and assert every transaction reference is stable; change only `referenceKey` and assert every reference changes; assert account and transaction HMAC domains never collide for the same provider ID.

- [x] **Step 2: Run RED**

```bash
cd apps/life-call
node --test --test-name-pattern='transaction|pagination' lib/cfo-moneytree.test.js
```

Expected: FAIL because `adaptMoneytreeTransactions` is not exported.

- [x] **Step 3: Implement the minimum transaction adapter**

Parse both JSON strings, rebuild the MUFG provider-ID→opaque-account-ref map from the accounts response, and require every transaction to resolve through that exact map. Validate `totalCount` as a nonnegative safe integer. Construct only the exact closed root/row keys above while ignoring extra raw provider keys. Derive references by HMAC, derive `flow` only from the signed amount, convert RFC 3339 provider date to its literal `YYYY-MM-DD` booking date after calendar validation, and set `verificationStatus: "provider_reported"`. Set `pagePartial` to the literal comparison `totalCount > transactions.length`, derive a separate evidence ref, and deep-freeze a cloned result. Do not copy descriptions, categories, balances, account numbers, institution labels, or raw IDs.

- [x] **Step 4: Verify focused and regression paths**

```bash
cd apps/life-call
node --test lib/cfo-moneytree.test.js
npm run test:cfo
npm ci --no-audit --no-fund
npm test
test "$(wc -l < lib/cfo-moneytree.js)" -le 168
test "$(wc -l < lib/cfo-moneytree.test.js)" -le 264
cd ../..
git diff --check
```

Expected: adapter tests, CFO suite, and full package suite pass with no provider or Telegram effect.

- [x] **Step 5: Commit, push, and fresh task review**

```bash
git add apps/life-call/lib/cfo-moneytree.js apps/life-call/lib/cfo-moneytree.test.js apps/life-call/package.json
git commit -m "feat(cfo): adapt Moneytree transactions"
git push canonical HEAD
```

Review gates: exact closed root/row keys, two-account cross-reference, amount/date truth, `pagePartial` pagination honesty, raw-field exclusion, stable tenant- and domain-separated HMAC refs, no categorization claim, no effect, and production/test size.

---

### Task 3: Live Moneytree pilot verification and CFO-1b closure

**Files:**
- Modify: this plan for exact redacted evidence
- Modify: `docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md`
- Modify: `docs/superpowers/specs/2026-08-06-life-manager-cfo-design.md`

**Interfaces:**
- Consumes: the installed Moneytree App `show_accounts(locale="ja")` and `show_transactions(locale="ja")`, plus both Task 1–2 adapter exports at the reviewed HEAD.
- Produces: a private ignored verification receipt and state transition to CFO-1b2. It does not produce a snapshot or Telegram report.

- [x] **Step 1: Read the live connected account without logging raw data**

In one tool orchestration, call `show_accounts(locale="ja")`, extract connected MUFG account numbers only in memory, and call `show_transactions(locale="ja", account_numbers=<in-memory>, limit=20, sort_key="date", sort_order="desc")`. Do not print either response or any extracted field.

- [x] **Step 2: Stream both live responses through the adapter**

Start a non-TTY Node process that reads exactly one newline-terminated JSON envelope from stdin with `readline.createInterface({ input: process.stdin }).once("line", verifyLine)`. The orchestrator sends `JSON.stringify(envelope) + "\n"` through `write_stdin`; non-TTY stdin is never echoed, and the verifier closes the readline interface and exits after that one line rather than waiting for EOF:

```js
JSON.stringify({
  accounts: accountsResult.structuredContent,
  transactions: transactionsResult.structuredContent,
  observedAt: new Date().toISOString(),
  referenceKey: crypto.randomBytes(32).toString("hex"),
}) + "\n"
```

The Node process parses the envelope, calls both adapter functions, and evaluates named predicates with a constant-code checker. It MUST NOT use `assert.deepEqual`/`assert.equal` on private objects or amounts because Node prints actual/expected values on failure:

```js
const liveMufgAccounts = accounts.data.accountGroups.banks
  .filter((group) => group.institutionKey === "mufg_bank")
  .flatMap((group) => group.accounts);
const liveRows = transactionResponse.data.transactions;
const normalizedJson = JSON.stringify({ source, transactions });
const sourceRefs = new Set(source.accounts.map((row) => row.accountRef));
const forbidden = [
  accounts.data.connectUrl,
  ...liveMufgAccounts.flatMap((row) => [row.id, row.institution_account_number]),
  ...liveRows.flatMap((row) => [row.id, row.account_id, row.account_number, row.description]),
].filter((value) => value !== null && value !== undefined && String(value).length >= 6);

function check(code, predicate) {
  if (!predicate) { const error = new Error(code); error.code = code; throw error; }
}

check("source_contract", JSON.stringify(validateFinancialSourceResult(source)) === JSON.stringify(source));
check("source_frozen", Object.isFrozen(source) && source.accounts.every(Object.isFrozen));
check("mufg_accounts", source.accounts.length > 0);
check("source_partial", source.partial === true);
check("balance_parity",
  source.accounts.reduce((sum, row) => sum + row.balanceMinor, 0)
    === liveMufgAccounts.reduce((sum, row) => sum + row.current_balance, 0));
check("transaction_page_parity", transactions.transactions.length === liveRows.length);
check("transaction_page_partial",
  transactions.pagePartial === (transactionResponse.data.totalCount > liveRows.length));
check("account_cross_reference", transactions.transactions.every((row) => sourceRefs.has(row.accountRef)));
check("raw_field_leak", forbidden.every((value) => !normalizedJson.includes(String(value))));
check("fixed_labels", source.accounts.every((row) => ["MUFG 普通預金", "MUFG 口座"].includes(row.label)));
```

Wrap the entire process in `try/catch`. On success, stdout contains only the fixed receipt below. On any failure, stdout contains only `{"verified":false,"error_code":"<one allowlisted constant code>"}` and exits nonzero. Adapter exceptions map to `adapter_rejected`; JSON/unknown exceptions map to `verification_failed`. Never print `error.message`, stack, actual/expected values, stdin, or the normalized result.

Write only this receipt to the plan-owned ignored workspace with mode `0600`:

```json
{
  "source_contract_valid": true,
  "connected_mufg_accounts_positive": true,
  "balance_parity": true,
  "transaction_page_parity": true,
  "transaction_page_partial": true,
  "raw_field_leak": false,
  "source_partial_until_cfo_1b2": true
}
```

No amount, raw string, raw ID, account suffix, provider response, or reference key may appear in the receipt or task report.

- [x] **Step 3: Fresh review and controller verification**

A fresh read-only reviewer checks the full CFO-1b range. The controller reruns adapter tests, CFO tests, a fresh full package suite after `npm ci`, size gates, and diff check. Critical/Important findings enter the bounded Superpowers loop.

- [x] **Step 4: Close only CFO-1b**

After clean review:

- check parent `CFO-1b` and set first unfinished item to `CFO-1b2`,
- set child active item to `CFO-1b2`,
- check only the child M1 acceptance that a fresh Moneytree/MUFG read became a redacted normalized source result,
- change parent test-matrix row 1 from `Planned` to `PASS`,
- record exact commits, test counts, review verdict, and the seven boolean receipt fields,
- keep liabilities, snapshot, Telegram receipt, and all later M1 acceptance boxes unchecked.

Commit and push the three state documents separately with `docs(cfo): close live Moneytree adapter`. CFO-1b completion means live read parity and privacy-safe normalization only; it is not durable ingestion, a scheduled cloud read, a net-worth snapshot, or a finance Telegram delivery.

## CFO-1b closure evidence

- Task 1 closed at `ee1966d827290a1d091f64ab6f12ad7c05298062`; Task 2 closed at `99c20d3de166097b66c2c45502c0b316854eaf03`; the transaction-boundary fix is `0aee20df13e1bcb5d05df7e89be2432f7b0832f1`.
- Controller evidence: adapter suite 51/51, CFO suite 126/126, `npm ci --no-audit --no-fund` succeeded, then the full `npm test` exited 0; production adapter 166 LOC and test file 264 LOC; `git diff --check` passed.
- Fresh review verdict: Critical 0, Important 0, Minor 0.
- Task 3 used one fresh interactive Moneytree/MUFG read; account selectors and both provider responses remained in memory, the guarded adapter produced a redacted normalized source result, and raw payloads were not persisted.
- Fixed redacted receipt: `source_contract_valid=true`, `connected_mufg_accounts_positive=true`, `balance_parity=true`, `transaction_page_parity=true`, `transaction_page_partial=true`, `raw_field_leak=false`, `source_partial_until_cfo_1b2=true`.
- State closure: parent first unfinished item is CFO-1b2 and child active item is CFO-1b2. Liabilities, durable ingestion, scheduled/cloud read, snapshot, reconciliation, and all later M1 acceptance remain unchecked. No real finance Telegram delivery has occurred.
