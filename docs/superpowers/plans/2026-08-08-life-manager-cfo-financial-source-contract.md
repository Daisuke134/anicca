# Life Manager CFO Financial Source Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the one strict, provider-neutral result contract that Moneytree App, LINK, and official-export adapters must satisfy before their data can enter a CFO snapshot.

**Architecture:** A pure CommonJS validator accepts one closed normalized object and returns a deep-frozen clone. Synthetic JSON fixtures prove fresh, partial, stale, unavailable, and re-consent states without containing any owner data. No provider call, storage, scheduler, or renderer change belongs to CFO-1a.

**Tech Stack:** Node.js 20+, CommonJS, `node:test`, Node standard library only, JSON.

## Global Constraints

- Approved design: `docs/superpowers/specs/2026-08-08-life-manager-cfo-moneytree-daily-report-design.md` §5.
- Active TODO is CFO-1a only. Do not implement Moneytree reads, OAuth, LINK, export parsing, persistence, snapshot assembly, Telegram, self-heal, Fleet, Binance, business P&L, token cost, tax, or spending advice.
- RED is observed before production code in each task.
- The validator consumes normalized adapter results only. It never receives or preserves raw provider payloads.
- Unknown is `null`, never zero. All amounts are safe integers in currency minor units.
- `locally_estimated` is not an allowed account-balance status in M1. A source adapter emits only provider-reported values or unavailable values.
- Account references and action references are opaque typed IDs, never account numbers or URLs.
- The result contains no owner ID because the caller binds owner scope before invoking the adapter; downstream persistence adds owner identity separately.
- No real balance, bank label, account reference, transaction, credential, path, or provider response enters Git.
- No dependency additions. Only current-task files are staged. Each task ends with tests, diff check, commit, and push.

## File Map and Size Targets

| File | Responsibility | Soft target |
|---|---|---:|
| `apps/life-call/lib/cfo-financial-source.js` | Closed schema, privacy validation, state invariants, deep freeze | 120 production LOC |
| `apps/life-call/lib/cfo-financial-source.test.js` | Contract, enums, truth/privacy failures, immutability | 150 test LOC |
| `apps/life-call/test/fixtures/cfo-financial-source.json` | Synthetic fresh/partial/stale/reconsent inputs | 100 data LOC; one file keeps the adapter truth table atomic |
| `apps/life-call/package.json` | Include contract test in existing `test:cfo` | +1 LOC |
| Parent/child specs and this plan | Closure evidence only | +12 documentation LOC |

The implementation is split into three bounded tasks; no implementation task edits more than three files. If production exceeds 144 LOC, stop and simplify the schema checks instead of adding helpers or another module.

## Closed Result Shape

```js
{
  schemaVersion: 1,
  sourceId: "moneytree_mufg",
  consent: "valid", // valid | expired | revoked | unknown
  freshness: "fresh", // fresh | stale | unavailable
  asOf: "2026-08-08T06:02:00+09:00",
  accounts: [{
    accountRef: "source_account:synthetic_deposit",
    label: "サンプル銀行",
    kind: "deposit", // deposit | card | loan | investment | other
    currency: "JPY",
    balanceMinor: 420000,
    verificationStatus: "provider_reported", // provider_reported | unavailable
  }],
  liabilities: [],
  evidenceRef: "evidence:synthetic_moneytree_read",
  partial: false,
  actionRequired: null,
}
```

When owner action is necessary:

```js
actionRequired: {
  kind: "reconsent", // reconsent | provider_outage
  sourceLabel: "Moneytree",
  actionRef: "action:moneytree_reconsent",
}
```

Exports:

```js
validateFinancialSourceResult(input) => Readonly<FinancialSourceResult>
```

Errors use `Error("cfo_financial_source_invalid:<reason>")` and never interpolate input values.

---

### Task 1: Strict normalized-source validator

**Files:**
- Create: `apps/life-call/lib/cfo-financial-source.test.js`
- Create: `apps/life-call/lib/cfo-financial-source.js`

- [ ] **Step 1: Write the first failing contract tests**

Create a literal `validResult()` factory with the exact synthetic result above. Tests exercise real production code and assert:

```js
test("valid fresh provider result is cloned and deeply frozen", () => {
  const input = validResult();
  const result = validateFinancialSourceResult(input);
  assert.notEqual(result, input);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.accounts), true);
  assert.equal(Object.isFrozen(result.accounts[0]), true);
  input.accounts[0].label = "changed";
  assert.equal(result.accounts[0].label, "サンプル銀行");
});

test("unavailable values are null and never silently become zero", () => {
  const input = validResult();
  input.freshness = "unavailable";
  input.partial = true;
  input.accounts[0].balanceMinor = null;
  input.accounts[0].verificationStatus = "unavailable";
  assert.equal(validateFinancialSourceResult(input).accounts[0].balanceMinor, null);

  input.accounts[0].balanceMinor = 0;
  assert.throws(() => validateFinancialSourceResult(input), /:unavailable_amount$/);
});

test("raw payloads, account numbers, URLs, paths, and secret-shaped labels fail closed", () => {
  for (const mutate of privateMutations()) {
    assert.throws(() => validateFinancialSourceResult(mutate(validResult())), /^Error: cfo_financial_source_invalid:/);
  }
});
```

Add table-driven literal mutations for:

- unknown root/account/liability/action key,
- unknown enumerable/non-enumerable/symbol properties on the accounts and liabilities containers, sparse and non-canonical array indices, custom array prototypes, and array accessor properties,
- invalid schema/source ID/consent/freshness/kind/currency/status,
- invalid or timezone-free `asOf`,
- float/unsafe integer/string amount,
- duplicate account reference across accounts and liabilities,
- `locally_estimated` and `unavailable` with a non-null amount,
- `provider_reported` with a null amount,
- expired/revoked consent without unavailable freshness and `reconsent`,
- fresh result with non-valid consent or without an account,
- stale result without `partial: true`,
- full account-like digit sequence, absolute or embedded private path, embedded credential-bearing or ordinary URL, secret-shaped label,
- `actionRef` that is a URL or is not `action:<opaque_id>`.

- [ ] **Step 2: Run RED**

```bash
cd apps/life-call
node --test lib/cfo-financial-source.test.js
```

Expected: FAIL because `./cfo-financial-source.js` does not exist.

- [ ] **Step 3: Implement the minimum closed validator**

Use exact key sets and small enum sets:

```js
const ROOT_KEYS = new Set([
  "schemaVersion", "sourceId", "consent", "freshness", "asOf",
  "accounts", "liabilities", "evidenceRef", "partial", "actionRequired",
]);
const ACCOUNT_KEYS = new Set([
  "accountRef", "label", "kind", "currency", "balanceMinor", "verificationStatus",
]);
const LIABILITY_KEYS = new Set([
  "accountRef", "label", "currency", "balanceMinor", "verificationStatus",
]);
const ACTION_KEYS = new Set(["kind", "sourceLabel", "actionRef"]);
const CONSENTS = new Set(["valid", "expired", "revoked", "unknown"]);
const FRESHNESS = new Set(["fresh", "stale", "unavailable"]);
const KINDS = new Set(["deposit", "card", "loan", "investment", "other"]);
const STATUSES = new Set(["provider_reported", "unavailable"]);
const ACTIONS = new Set(["reconsent", "provider_outage"]);
```

Validation rules:

1. Accept plain JSON objects only; reject unknown keys at every level.
2. `sourceId` matches `/^[a-z][a-z0-9_]{2,63}$/`.
3. `accountRef` matches `/^source_account:[a-z][a-z0-9_]{2,63}$/`; `evidenceRef` matches `/^evidence:[a-z][a-z0-9_]{2,63}$/`; `actionRef` matches `/^action:[a-z][a-z0-9_]{2,63}$/`.
4. `asOf` is an RFC 3339 timestamp with explicit `Z` or `±HH:MM`; impossible dates fail rather than normalize.
5. Labels are non-empty strings at most 80 characters and reject six consecutive digits, private filesystem prefixes, credential-bearing URLs, API/secret/private-key markers.
6. Amounts are safe integers or null. `provider_reported` requires non-null; `unavailable` requires null. Liabilities cannot be negative.
7. References are unique across accounts and liabilities. A fresh result requires valid consent and at least one account. Stale requires valid consent and `partial: true`. Unavailable requires `partial: true` and all amounts null.
8. Expired/revoked/unknown consent requires unavailable freshness and a `reconsent` action. Valid consent may use null or `provider_outage`, never `reconsent`; no action URL is accepted.
9. Clone with `structuredClone`, recursively freeze the clone, and never retain caller references.

Use a strict date round-trip helper. Accept the RFC 3339 offset as evidence, normalize to `Date`, and verify each parsed UTC date component corresponds to the timestamp rather than relying only on `Date.parse`.

- [ ] **Step 4: Run GREEN and size check**

```bash
cd apps/life-call
node --test lib/cfo-financial-source.test.js
wc -l lib/cfo-financial-source.js
cd ../..
git diff --check
```

Expected: all Task 1 tests pass; production is at or below 144 LOC; diff check exits zero.

- [ ] **Step 5: Commit and push Task 1**

```bash
git add apps/life-call/lib/cfo-financial-source.js apps/life-call/lib/cfo-financial-source.test.js
git commit -m "feat(cfo): validate financial source results"
git push
```

---

### Task 2: Synthetic state fixtures and normal test wiring

**Files:**
- Create: `apps/life-call/test/fixtures/cfo-financial-source.json`
- Modify: `apps/life-call/lib/cfo-financial-source.test.js`
- Modify: `apps/life-call/package.json`

- [ ] **Step 1: Add RED fixture tests**

The JSON root is `{ "schemaVersion": 1, "cases": [...] }`. Add exactly four named cases:

1. `fresh_complete`: one synthetic deposit, provider-reported amount, no liability, no action.
2. `fresh_partial`: one deposit plus one positive synthetic loan liability, `partial: true`, both provider-reported.
3. `stale_auto_retry`: one stale deposit, `partial: true`, no owner action.
4. `reconsent_required`: unavailable deposit with null amount, expired consent, reconsent action.

Use only `source_account:synthetic_*`, `evidence:synthetic_*`, `action:synthetic_*`, the labels `サンプル銀行`, `サンプルローン`, and arbitrary amounts unrelated to the owner.

```js
test("synthetic fixture covers the four closed source states", () => {
  const fixture = JSON.parse(fs.readFileSync(FIXTURE_PATH, "utf8"));
  assert.equal(fixture.schemaVersion, 1);
  assert.deepEqual(fixture.cases.map((entry) => entry.name), [
    "fresh_complete", "fresh_partial", "stale_auto_retry", "reconsent_required",
  ]);
  for (const entry of fixture.cases) assert.doesNotThrow(() => validateFinancialSourceResult(entry.result));
});

test("fixture is synthetic and contains no private transport material", () => {
  const text = fs.readFileSync(FIXTURE_PATH, "utf8");
  const fixture = JSON.parse(text);
  assert.doesNotMatch(text, /Dais|三菱UFJ|accountNumber|rawPayload|credential|\/Users\/|https?:\/\//i);
  const strings = collectStrings(fixture);
  assert.ok(strings.every((value) => !/\d{6,}/.test(value)));
});
```

`collectStrings` is a test-only recursive helper over arrays/plain objects. Numeric amount values are intentionally ignored; only strings are checked for account-number-like sequences.

RED must be `ENOENT` for the missing fixture, not an assertion typo.

- [ ] **Step 2: Run RED**

```bash
cd apps/life-call
node --test lib/cfo-financial-source.test.js
```

- [ ] **Step 3: Create the exact synthetic fixture and wire normal CFO tests**

Create only the four cases above. Add `lib/cfo-financial-source.test.js` once to `test:cfo`; `pretest` already calls that script, so add no hook.

- [ ] **Step 4: Verify focused and regression paths**

```bash
cd apps/life-call
node --test lib/cfo-financial-source.test.js
npm run test:cfo
npm test
cd ../..
git diff --check
```

Expected: fixture tests, CFO suite, and full package suite pass. No provider or Telegram effect occurs.

- [ ] **Step 5: Fresh review and fix loop**

A fresh read-only reviewer checks:

1. Can a raw/private provider field survive validation or appear in the fixture?
2. Can unavailable become zero, or estimated become provider-reported?
3. Can stale/expired/revoked consent be labeled fresh/current?
4. Can duplicate references or negative liabilities enter the normalized result?
5. Did the implementation add an effect, abstraction, or CFO-1b scope?

Critical/Important findings enter the bounded Superpowers fix loop. Minor findings are recorded for final review.

### Task 3: Position-independent private-path boundary

**Why this task exists:** The first whole-plan review found that the current path check accepts private paths attached directly to preceding text while rejecting a harmless spaced slash. Dais explicitly authorized continuous no-human correction, so this is a visible independent task rather than a hidden second final-review fix wave.

**Files:**
- Modify: `apps/life-call/lib/cfo-financial-source.test.js`
- Modify: `apps/life-call/lib/cfo-financial-source.js`
- Modify: this plan only for task evidence

**Soft target:** production stays at or below 144 LOC; prefer replacing the current broad path expression over adding an abstraction.

- [ ] **Step 1: RED — prove the two attached private-path bypasses and harmless label**

Add behavior tests showing that `Bank/Users/dais/private` and `Bank/home/name/private` throw the stable private-text validation error, while `Bank / Savings` validates. The expected values are literals and the tests exercise the real validator.

```bash
cd apps/life-call
node --test --test-name-pattern='attached private paths|harmless spaced slash' lib/cfo-financial-source.test.js
```

Expected RED: the two private-path cases are accepted and the harmless label is rejected.

- [ ] **Step 2: GREEN — use direct position-independent private-path detection**

Reject literal `/Users/` and `/home/` wherever they occur in a label. Keep the existing URL and credential checks. Do not reject a generic slash or add provider-specific behavior.

- [ ] **Step 3: Verify, commit, push, and review**

```bash
cd apps/life-call
node --test --test-name-pattern='attached private paths|harmless spaced slash' lib/cfo-financial-source.test.js
node --test lib/cfo-financial-source.test.js
npm run test:cfo
cd ../..
test "$(wc -l < apps/life-call/lib/cfo-financial-source.js)" -le 144
git diff --check
```

Commit `fix(cfo): reject attached private paths`, push, then run one fresh task review and a fresh whole-plan review.

- [ ] **Step 4: Close CFO-1a after clean final review**

After the whole-plan review is clean:

- check this plan's completed steps,
- check parent `CFO-1a`,
- set child active item and parent first unfinished item to `CFO-1b`,
- add exact commits/test counts/review result,
- keep every M1 real-source/report acceptance checkbox unchecked.

Commit and push state-only docs separately. Completion is a tested normalized contract and synthetic fixtures only, not a Moneytree read or Telegram delivery.
