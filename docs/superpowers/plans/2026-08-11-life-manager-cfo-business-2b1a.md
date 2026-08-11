# CFO-2b.1a Life Manager Earning Receipt — Implementation Plan

> Use Ponytail `full`, then Superpowers TDD. Sol owns this plan and final verification. Luna owns only the three
> implementation files below. No DB write, launchd change, Telegram send, Stripe call, or production state change.

## Goal and scope

Add one pure boundary that converts already-finalized TaskMarket/uGig `lm_agent_earnings` rows into privacy-safe
Life Manager revenue receipts. This does not aggregate revenue or show business profit.

| Element | Files | Soft target |
|---|---:|---:|
| Production normalizer | `apps/life-call/lib/cfo-life-manager-earning.js` | 35 LOC |
| Focused contract tests | `apps/life-call/lib/cfo-life-manager-earning.test.js` | 55 LOC |
| Durable CFO suite registration | `apps/life-call/package.json` | 1 LOC |
| Total | 3 | <=91 additions; hard stop at 100 |

## Task 1 — RED

Create the test file and import `normalizeLifeManagerEarningReceipt`. Use one exact TaskMarket fixture with the
producer's decimal-string amount and secret-shaped extra fields, plus one uGig fixture. Assert the documented
nine-key result, exact channel mapping, canonical timestamp, decimal string, deep freeze, and unchanged input. Add
one compact invalid table covering only money-truth and privacy failures:

- another business source, wrong kind, non-finalized/non-external meta;
- zero, unsafe numeric, or minor-plus-atomic amount;
- malformed public ref/receipt. The successful fixture's secret sentinel proves unknown/privacy-sensitive source
  fields are stripped rather than propagated.

Every failure must match `^cfo_life_manager_earning_invalid:<fixed_reason>$`; serialized errors/results contain no
sentinel, wallet, transaction hash, entry key, or metadata. Append this test once to `test:cfo`. Run the focused test
and confirm RED is only the missing module/export.

## Task 2 — GREEN

Create `cfo-life-manager-earning.js` with one exported function. Validate before reading nested values where
possible; accept only an ordinary plain row and ordinary plain meta object. Use exact source→channel mapping. Accept
the producers' canonical positive decimal string or a positive safe integer, normalize either to the same base-10
string, and reject unsafe numeric input rather than rounding it. Normalize time with `toISOString()`, construct the
closed result field-by-field, freeze `amount` and the outer result, and catch unexpected input behavior into the
fixed `invalid_input` error. Do not copy or log any raw evidence field.

Run focused tests, then `npm run test:cfo`, `npm test`, syntax checks, `git diff --check`, exact owned-path check, and
the gross-addition gate. Fix only contract failures inside the owned files.

## Task 3 — Verify the real empty state

Sol runs one read-only PostgREST query with the existing service credential and exact filters:
`kind=financial_external_income` and `source in (taskmarket_work,ugig_work)`. Process in memory and print only HTTP
status, row count, normalized receipt count, and whether any redacted forbidden value escaped. The current expected
observation is HTTP 200 and zero receipts. A future non-empty result is normalized and checked, never rejected merely
because this plan observed zero today.

## Task 4 — Review, state, commit, push

Fresh Sol reviews only Critical/Important correctness, money truth, data loss, duplicate external effects, and secret
leakage. Luna fixes bounded findings. Sol marks only `CFO-2b.1a` complete in the child SSOT, records exact test/E2E
evidence, commits docs and code separately, pushes both branches, and sends a `Codex:::` Telegram milestone with the
next active slice `CFO-2b.1b`.
