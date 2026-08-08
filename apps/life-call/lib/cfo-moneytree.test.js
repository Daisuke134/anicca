"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { adaptMoneytreeAccounts } = require("./cfo-moneytree.js");

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
