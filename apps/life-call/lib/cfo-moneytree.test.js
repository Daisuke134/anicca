"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { adaptMoneytreeAccounts, adaptMoneytreeTransactions } = require("./cfo-moneytree.js");

// Mutation targets: totalBalance, raw label/ID, unsafe money, reversible refs,
// weak reference keys, and a missing source incorrectly reported as fresh.
const OBSERVED_AT = "2026-08-08T06:02:00+09:00";
const REFERENCE_KEY = "synthetic-reference-key-32-bytes-long";
const FORBIDDEN = /9999999|secret\.example|1001|秘密口座|invalid-json-with-secret-marker/;

function syntheticAccounts() {
  return {
    type: "accounts",
    data: {
      baseCurrency: "JPY",
      totalBalance: 999999999,
      connectUrl: "https://secret.example/connect",
      accountGroups: {
        banks: [
          {
            institutionKey: "mufg_bank",
            institutionName: "三菱UFJ銀行",
            accounts: [{
              id: 1001,
              account_subtype: "savings",
              current_balance: 420000,
              currency: "JPY",
              institution_account_number: "9999999",
              connectUrl: "https://secret.example/connect",
              nickname: "秘密口座",
              label: "秘密口座",
            }],
          },
          {
            institutionKey: "other_bank",
            accounts: [{ id: 1002, account_subtype: "checking", current_balance: 999999, currency: "JPY" }],
          },
        ],
      },
    },
  };
}

function inputFor(payload = syntheticAccounts()) {
  return { accountsJson: JSON.stringify(payload), observedAt: OBSERVED_AT, referenceKey: REFERENCE_KEY };
}

function invalidInput(mutator) {
  const payload = syntheticAccounts();
  const overrides = mutator(payload) || {};
  return { ...inputFor(payload), ...overrides };
}

function assertInvalid(input) {
  assert.throws(() => adaptMoneytreeAccounts(input), (error) => {
    assert.match(error.message, /^moneytree_adapter_invalid:[a-z_]+$/);
    assert.doesNotMatch(error.message, FORBIDDEN);
    return true;
  });
}

test("projects only MUFG balances into the frozen financial source contract", () => {
  const source = adaptMoneytreeAccounts(inputFor());
  assert.equal(source.schemaVersion, 1);
  assert.equal(source.sourceId, "moneytree_mufg");
  assert.equal(source.consent, "valid");
  assert.equal(source.freshness, "fresh");
  assert.equal(source.asOf, OBSERVED_AT);
  assert.equal(source.partial, true);
  assert.equal(source.actionRequired, null);
  assert.deepEqual(source.liabilities, []);
  assert.equal(source.accounts.length, 1);
  assert.equal(source.accounts[0].label, "MUFG 普通預金");
  assert.equal(source.accounts[0].kind, "deposit");
  assert.equal(source.accounts[0].currency, "JPY");
  assert.equal(source.accounts[0].balanceMinor, 420000);
  assert.equal(source.accounts[0].verificationStatus, "provider_reported");
  assert.match(source.accounts[0].accountRef, /^source_account:mt_[a-f0-9]{24}$/);
  assert.match(source.evidenceRef, /^evidence:mt_[a-f0-9]{24}$/);
  assert.doesNotMatch(JSON.stringify(source), FORBIDDEN);
  assert.equal(Object.isFrozen(source), true);
  assert.equal(Object.isFrozen(source.accounts), true);
  assert.equal(Object.isFrozen(source.accounts[0]), true);
});

test("keeps opaque refs deterministic, tenant-scoped, and domain-separated", () => {
  const sameInput = inputFor();
  const source = adaptMoneytreeAccounts(sameInput);
  const repeated = adaptMoneytreeAccounts(sameInput);
  const otherTenant = adaptMoneytreeAccounts({ ...sameInput, referenceKey: "different-synthetic-reference-key-32" });
  assert.equal(repeated.accounts[0].accountRef, source.accounts[0].accountRef);
  assert.equal(repeated.evidenceRef, source.evidenceRef);
  assert.notEqual(otherTenant.accounts[0].accountRef, source.accounts[0].accountRef);
  assert.notEqual(otherTenant.evidenceRef, source.evidenceRef);
  assert.notEqual(source.accounts[0].accountRef.slice(-24), source.evidenceRef.slice(-24));
});

test("maps non-savings MUFG subtypes to the fixed generic label", () => {
  const payload = syntheticAccounts();
  payload.data.accountGroups.banks[0].accounts[0].account_subtype = "checking";
  const source = adaptMoneytreeAccounts(inputFor(payload));
  assert.equal(source.accounts[0].label, "MUFG 口座");
  assert.equal(source.accounts[0].kind, "other");
});

const invalidCases = [
  ["invalid JSON", () => ({ accountsJson: "invalid-json-with-secret-marker" })],
  ["non-string JSON", () => ({ accountsJson: 42 })],
  ["wrong root type", () => ({ accountsJson: JSON.stringify([]) })],
  ["wrong connector type", (payload) => { payload.type = "transactions"; }],
  ["missing data", (payload) => { delete payload.data; }],
  ["missing account groups", (payload) => { delete payload.data.accountGroups; }],
  ["missing bank groups", (payload) => { delete payload.data.accountGroups.banks; }],
  ["non-JPY base currency", (payload) => { payload.data.baseCurrency = "USD"; }],
  ["non-JPY account currency", (payload) => { payload.data.accountGroups.banks[0].accounts[0].currency = "USD"; }],
  ["non-integer balance", (payload) => { payload.data.accountGroups.banks[0].accounts[0].current_balance = 420000.5; }],
  ["unsafe balance", (payload) => { payload.data.accountGroups.banks[0].accounts[0].current_balance = Number.MAX_SAFE_INTEGER + 1; }],
  ["null balance", (payload) => { payload.data.accountGroups.banks[0].accounts[0].current_balance = null; }],
  ["missing provider ID", (payload) => { delete payload.data.accountGroups.banks[0].accounts[0].id; }],
  ["nonnumeric provider ID", (payload) => { payload.data.accountGroups.banks[0].accounts[0].id = "1001"; }],
  ["unsafe provider ID", (payload) => { payload.data.accountGroups.banks[0].accounts[0].id = Number.MAX_SAFE_INTEGER + 1; }],
  ["zero MUFG accounts", (payload) => { payload.data.accountGroups.banks[0].institutionKey = "other_bank"; }],
  ["duplicate provider account ID", (payload) => {
    payload.data.accountGroups.banks[0].accounts.push(structuredClone(payload.data.accountGroups.banks[0].accounts[0]));
  }],
  ["weak reference key", () => ({ referenceKey: "a".repeat(31) })],
  ["non-string reference key", () => ({ referenceKey: 32 })],
  ["invalid observedAt", () => ({ observedAt: "2026-08-08T06:02:00" })],
];

for (const [name, mutate] of invalidCases) {
  test(`rejects ${name} with a stable redacted error`, () => assertInvalid(invalidInput(mutate)));
}

function transactionAccounts() {
  const payload = syntheticAccounts();
  payload.data.accountGroups.banks[1].institutionKey = "mufg_bank";
  return payload;
}

function syntheticTransactions() {
  return {
    type: "transactions",
    data: {
      totalCount: 3,
      transactions: [
        {
          id: 2001, account_id: 1001, date: "2026-08-06T00:00:00+09:00", amount: 1234, currency: "JPY",
          account_number: "9999999", description: "merchant-secret", institution_name: "三菱UFJ銀行",
          category_id: "provider-category-id", category_name: "provider-category", balance: 420000,
        },
        {
          id: 2002, account_id: 1002, date: "2026-08-05T00:00:00+09:00", amount: -500, currency: "JPY",
          account_number: "8888888", description: "merchant-secret-2", institution_name: "三菱UFJ銀行",
          category_id: "provider-category-id-2", category_name: "provider-category-2", balance: 419500,
        },
        {
          id: 2003, account_id: 1001, date: "2026-08-04T00:00:00+09:00", amount: 0, currency: "JPY",
          account_number: "9999999", description: "merchant-secret-3", institution_name: "三菱UFJ銀行",
          category_id: "provider-category-id-3", category_name: "provider-category-3", balance: 419500,
        },
      ],
    },
  };
}

function transactionInput({ accounts = transactionAccounts(), transactions = syntheticTransactions(), ...rest } = {}) {
  return {
    accountsJson: JSON.stringify(accounts),
    transactionsJson: JSON.stringify(transactions),
    observedAt: OBSERVED_AT,
    referenceKey: REFERENCE_KEY,
    ...rest,
  };
}

function invalidTransactionInput(mutator) {
  const accounts = transactionAccounts();
  const transactions = syntheticTransactions();
  const overrides = mutator(accounts, transactions) || {};
  return transactionInput({ ...overrides, accounts: overrides.accounts || accounts, transactions: overrides.transactions || transactions });
}

function assertInvalidTransaction(input) {
  assert.throws(() => adaptMoneytreeTransactions(input), (error) => {
    assert.match(error.message, /^moneytree_adapter_invalid:[a-z_]+$/);
    assert.doesNotMatch(error.message, /9999999|merchant-secret|provider-category|1001|2001/);
    return true;
  });
}

test("projects redacted interleaved transactions with exact closed keys", () => {
  const input = transactionInput();
  const source = adaptMoneytreeAccounts({ accountsJson: input.accountsJson, observedAt: OBSERVED_AT, referenceKey: REFERENCE_KEY });
  const result = adaptMoneytreeTransactions(input);
  assert.deepEqual(result.transactions.map((row) => row.flow), ["inflow", "outflow", "neutral"]);
  assert.deepEqual(result.transactions.map((row) => row.amountMinor), [1234, -500, 0]);
  assert.deepEqual(result.transactions.map((row) => row.bookingDate), ["2026-08-06", "2026-08-05", "2026-08-04"]);
  assert.match(result.transactions[0].transactionRef, /^transaction:mt_[a-f0-9]{24}$/);
  assert.equal(result.transactions[0].accountRef, source.accounts[0].accountRef);
  assert.equal(result.transactions[1].accountRef, source.accounts[1].accountRef);
  assert.equal(result.pagePartial, false);
  assert.doesNotMatch(JSON.stringify(result), /9999999|merchant-secret|provider-category|1001|2001/);
  assert.equal(Object.isFrozen(result), true);
  assert.equal(Object.isFrozen(result.transactions), true);
  assert.equal(Object.isFrozen(result.transactions[0]), true);
  const rootKeys = ["asOf", "evidenceRef", "pagePartial", "schemaVersion", "sourceId", "transactions"];
  const rowKeys = ["accountRef", "amountMinor", "bookingDate", "currency", "flow", "transactionRef", "verificationStatus"];
  assert.deepEqual(Object.keys(result).sort(), rootKeys);
  for (const row of result.transactions) assert.deepEqual(Object.keys(row).sort(), rowKeys);
});

test("keeps transaction refs stable, tenant-scoped, and domain-separated", () => {
  const input = transactionInput();
  const result = adaptMoneytreeTransactions(input);
  const repeated = adaptMoneytreeTransactions(input);
  const otherTenant = adaptMoneytreeTransactions({ ...input, referenceKey: "different-synthetic-reference-key-32" });
  assert.deepEqual(repeated.transactions.map((row) => row.transactionRef), result.transactions.map((row) => row.transactionRef));
  assert.deepEqual(otherTenant.transactions.map((row) => row.transactionRef).map((ref, index) => ref !== result.transactions[index].transactionRef), [true, true, true]);
  assert.notEqual(result.transactions[0].transactionRef.slice(-24), result.transactions[0].accountRef.slice(-24));
});

test("reports transaction pagination honestly", () => {
  const partial = syntheticTransactions();
  partial.data.totalCount = 4;
  assert.equal(adaptMoneytreeTransactions(transactionInput({ transactions: partial })).pagePartial, true);
  const complete = syntheticTransactions();
  complete.data.totalCount = complete.data.transactions.length;
  assert.equal(adaptMoneytreeTransactions(transactionInput({ transactions: complete })).pagePartial, false);
});

const invalidTransactionCases = [
  ["invalid transaction JSON", () => ({ transactionsJson: "invalid-json-with-secret-marker" })],
  ["non-string transaction JSON", () => ({ transactionsJson: 42 })],
  ["wrong transaction root type", (_accounts, transactions) => { transactions.type = "accounts"; }],
  ["missing transaction data", (_accounts, transactions) => { delete transactions.data; }],
  ["missing transactions array", (_accounts, transactions) => { delete transactions.data.transactions; }],
  ["missing total count", (_accounts, transactions) => { delete transactions.data.totalCount; }],
  ["missing booking date", (_accounts, transactions) => { delete transactions.data.transactions[0].date; }],
  ["invalid booking date", (_accounts, transactions) => { transactions.data.transactions[0].date = "2026-02-30T00:00:00+09:00"; }],
  ["float amount", (_accounts, transactions) => { transactions.data.transactions[0].amount = 1.5; }],
  ["unsafe amount", (_accounts, transactions) => { transactions.data.transactions[0].amount = Number.MAX_SAFE_INTEGER + 1; }],
  ["string amount", (_accounts, transactions) => { transactions.data.transactions[0].amount = "1234"; }],
  ["non-JPY currency", (_accounts, transactions) => { transactions.data.transactions[0].currency = "USD"; }],
  ["missing transaction ID", (_accounts, transactions) => { delete transactions.data.transactions[0].id; }],
  ["nonnumeric transaction ID", (_accounts, transactions) => { transactions.data.transactions[0].id = "2001"; }],
  ["unsafe transaction ID", (_accounts, transactions) => { transactions.data.transactions[0].id = Number.MAX_SAFE_INTEGER + 1; }],
  ["duplicate transaction ID", (_accounts, transactions) => { transactions.data.transactions[1].id = 2001; }],
  ["unknown account ID", (_accounts, transactions) => { transactions.data.transactions[0].account_id = 9999; }],
  ["unsafe account ID", (_accounts, transactions) => { transactions.data.transactions[0].account_id = Number.MAX_SAFE_INTEGER + 1; }],
  ["negative total count", (_accounts, transactions) => { transactions.data.totalCount = -1; }],
  ["float total count", (_accounts, transactions) => { transactions.data.totalCount = 3.5; }],
  ["unsafe total count", (_accounts, transactions) => { transactions.data.totalCount = Number.MAX_SAFE_INTEGER + 1; }],
  ["string total count", (_accounts, transactions) => { transactions.data.totalCount = "3"; }],
  ["total count smaller than page length", (_accounts, transactions) => { transactions.data.totalCount = 2; }],
];

for (const [name, mutate] of invalidTransactionCases) {
  test(`rejects ${name} with a stable redacted error`, () => assertInvalidTransaction(invalidTransactionInput(mutate)));
}
