# 13c Polymarket Cycle Ledger Implementation Plan

> **For Codex:** Execute each task in order with test-driven development. Do not
> claim 13c complete until a production `lm_agent_earnings` row is read back and
> the report is generated from that row plus a fresh Polygon balance.

**Goal:** Connect one completed Polymarket CAPITAL cycle to Life Manager's
append-only earnings ledger without counting recovered principal as revenue.

**Architecture:** A pure adapter validates a six-decimal USD cycle envelope and
derives the existing cent-denominated ledger rows. The runtime writes those rows
through the existing idempotent Supabase function. The monthly rollup keeps cent
accounting but gains a separate exact atomic balance representation for pUSD.

**Tech stack:** CommonJS Node.js, `node:test`, Supabase REST, Polygon JSON-RPC.

**Design:** `docs/superpowers/specs/2026-07-27-13c-polymarket-cycle-ledger-design.md`

---

## Task 1: Render an exact six-decimal on-chain balance

**Files:**

- Modify: `apps/life-manager/lib/earnings-ledger.js`
- Modify: `apps/life-manager/lib/earnings-ledger.test.js`
- Modify: `apps/life-manager/lib/earnings-runtime.js`
- Modify: `apps/life-manager/lib/earnings-runtime.test.js`

### Step 1: Write failing ledger tests

Add tests proving:

- `rollUpMonth(..., { balanceAtomic: "4422182", balanceDecimals: 6 })` stores
  `balance_atomic="4422182"` and `balance_decimals=6`;
- `formatMonthlyReport` renders `・私の残高: $4.422182`;
- supplying both minor and atomic balance paths, neither path, malformed atomic
  units, or an invalid decimal count fails closed;
- the existing `balanceMinor` path remains byte-for-byte compatible.

Run:

```bash
node --test apps/life-manager/lib/earnings-ledger.test.js
```

Expected: new tests fail because atomic balance options are not implemented.

### Step 2: Implement the smallest pure change

Add:

```js
normaliseAtomicBalance(value, decimals)
formatUsdAtomic(atomic, decimals)
```

Make `rollUpMonth` accept exactly one of `balanceMinor` or
`balanceAtomic + balanceDecimals`. Preserve `balance_minor` for the old path and
add `balance_atomic`/`balance_decimals` for the new path. Make
`formatMonthlyReport` select the matching formatter.

### Step 3: Write failing runtime tests

Add tests that `generateMonthlyReport` accepts:

```js
readBalanceAtomic: async () => "4422182",
balanceDecimals: 6
```

and refuses ambiguous or missing balance readers.

### Step 4: Implement and verify runtime selection

Keep `readBalanceMinor` compatible. Measure only the selected reader and forward
the exact representation to `rollUpMonth`.

Run:

```bash
node --test apps/life-manager/lib/earnings-ledger.test.js \
  apps/life-manager/lib/earnings-runtime.test.js
```

Expected: PASS.

### Step 5: Commit and push

```bash
git fetch origin
git add apps/life-manager/lib/earnings-ledger.js \
  apps/life-manager/lib/earnings-ledger.test.js \
  apps/life-manager/lib/earnings-runtime.js \
  apps/life-manager/lib/earnings-runtime.test.js
git commit -m "feat: report exact atomic agent balances"
git push
```

## Task 2: Map a Polymarket cycle without counting principal

**Files:**

- Create: `apps/life-manager/lib/polymarket-cycle.js`
- Create: `apps/life-manager/lib/polymarket-cycle.test.js`

### Step 1: Write failing pure adapter tests

Use the real Tatiana envelope as a fixture and add cases for:

| Case | Expected rows |
|---|---|
| deployed `3150000`, recovered `0`, fee `0` | one `financial_realized_loss=315` |
| deployed `5000000`, recovered `6000000`, fee `10000` | income `100`, fee `1` |
| deployed equals recovered, fee `20000` | fee `2` only |
| returned principal | never appears as `financial_external_income` |

Also prove rejection before any write for:

- JavaScript numeric money values;
- invalid wallet, condition, transaction hashes, or receipt status;
- `realized_pnl_microusd` formula mismatch;
- a derived delta or fee that is not an exact cent;
- nested secret fields.

Run:

```bash
node --test apps/life-manager/lib/polymarket-cycle.test.js
```

Expected: FAIL because the module does not exist.

### Step 2: Implement `cycleLedgerEntries`

Validate all money as decimal strings and calculate with `BigInt`:

```text
realized = recovered - deployed - fee
economic delta before fee = recovered - deployed
```

Emit deterministic keys:

```text
polymarket:<condition_id>:income
polymarket:<condition_id>:loss
polymarket:<condition_id>:fee
```

Every row's `meta` must contain the four micro-USD components, cycle ID,
condition ID, trade transaction, redeem transaction, and receipt status. Freeze
the rows by passing them through `normaliseEntry`.

### Step 3: Verify and commit

Run:

```bash
node --test apps/life-manager/lib/polymarket-cycle.test.js
```

Expected: PASS.

Then fetch, commit, and push the two files.

## Task 3: Write cycle rows idempotently through the existing runtime

**Files:**

- Modify: `apps/life-manager/lib/polymarket-cycle.js`
- Modify: `apps/life-manager/lib/polymarket-cycle.test.js`

### Step 1: Write failing runtime tests

Inject `recordEntry` and prove:

- every derived row is sent to `recordEarnLoopRevenue`;
- a duplicate response is preserved as an idempotent success;
- a validation failure produces zero calls;
- a later-row transport failure is surfaced, while deterministic keys make the
  next invocation safe to repair.

### Step 2: Implement `recordPolymarketCycle`

The function calls `cycleLedgerEntries` first, then awaits `recordEntry` once per
row in deterministic order and returns:

```js
{ ok: true, cycle_id, entries, writes }
```

Default `recordEntry` to the existing `recordEarnLoopRevenue`.

### Step 3: Verify and commit

Run the Polymarket test file, then all three earnings test files. Fetch, commit,
and push.

## Task 4: Add a production command and committed evidence

**Files:**

- Create: `docs/evidence/agent-economy/2026-07-27-polymarket-tatiana-cycle.json`
- Create: `apps/life-manager/scripts/record-polymarket-cycle.js`
- Create: `apps/life-manager/scripts/record-polymarket-cycle.test.js`

### Step 1: Commit the immutable public evidence envelope

Record:

- wallet and condition;
- deployed/recovered/fee/realized micro-USD strings;
- trade and redeem transaction hashes;
- authenticated order status and fee rate;
- Polygon receipt status/block/gas used;
- Activity API timestamps and source URLs.

Do not include API keys, signatures, private keys, cookies, or authorization
headers.

### Step 2: Write failing command tests

Refactor the command to export `main(deps, argv)` without running when required.
Inject the file reader, cycle recorder, RPC fetch, month-row reader, and output
writer. Prove:

- it reads the evidence and records it before reporting;
- `eth_call balanceOf` is made for the exact wallet and pUSD contract;
- the output contains `-$3.15` and `$4.422182`;
- an RPC or ledger failure exits visibly rather than printing success.

### Step 3: Implement the command

Use Polygon JSON-RPC to read:

```text
balanceOf(0x904B50d2e214Da947d83D6a2D32c4E3Ffc17Eb74)
```

from the live pUSD contract identified by the existing PM deployment. Pass the
six-decimal result to `generateMonthlyReport`. Supply the honest loss explanation:

```text
cause = 片側だけが約定し、勝ち側を持たずに解決したこと
plan = 両脚成立を確認できないcycleを停止し、片側約定を即時解消すること
```

### Step 4: Verify and commit

Run the command tests and the focused earnings suite, then fetch, commit, and
push.

## Task 5: Record the real row and close 13c-PM

**Files:**

- Modify: `docs/evidence/agent-economy/2026-07-27-polymarket-tatiana-cycle.json`
- Modify: `docs/superpowers/specs/2026-07-19-anicca-one-repo-consolidation-spec.md`
- Modify: `docs/handovers/2026-07-27-crypto-track-handoff.md`

### Step 1: Preflight production without exposing credentials

Confirm Supabase variables are present, the migration/table can be read, Polygon
returns receipt status `0x1`, and the pUSD balance is independently observed.
Record only booleans and public values in logs/evidence.

### Step 2: Execute the production command

Run:

```bash
node apps/life-manager/scripts/record-polymarket-cycle.js \
  --evidence docs/evidence/agent-economy/2026-07-27-polymarket-tatiana-cycle.json \
  --month 2026-07
```

This is the required real side effect, not a dry run.

### Step 3: Read back and reconcile

Query `lm_agent_earnings` by wallet and deterministic entry key. Assert:

- exactly one logical row for the loss component;
- `amount_minor=315`, `kind=financial_realized_loss`;
- all four cycle components and both tx hashes match evidence;
- the report uses the read-back row and fresh pUSD balance;
- a second command invocation reports a duplicate and does not double count.

Add the public read-back result and generated report to the evidence JSON.

### Step 4: Update SSOT and handoff

Mark only 13c-PM complete. Keep 13c-SELL, 13c-WORK, REDEEM-1, 13d-b and
FIN-LIVE truthfully open. Set the next cursor to 13c-SELL.

### Step 5: Full verification

Run:

```bash
node --test apps/life-manager/lib/earnings-ledger.test.js \
  apps/life-manager/lib/earnings-runtime.test.js \
  apps/life-manager/lib/earnings-migration.test.js \
  apps/life-manager/lib/polymarket-cycle.test.js \
  apps/life-manager/scripts/record-polymarket-cycle.test.js
git diff --check
git status --short
```

Re-run the live read-only reconciliation after the tests.

### Step 6: Final commit and push

Fetch, add only 13c files, commit, and push. Report exact evidence and the
remaining TODO cursor; do not claim verified external income.
