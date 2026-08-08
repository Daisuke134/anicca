"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");

function validResult() {
  return {
    schemaVersion: 1,
    sourceId: "moneytree_mufg",
    consent: "valid",
    freshness: "fresh",
    asOf: "2026-08-08T06:02:00+09:00",
    accounts: [{
      accountRef: "source_account:synthetic_deposit",
      label: "サンプル銀行",
      kind: "deposit",
      currency: "JPY",
      balanceMinor: 420000,
      verificationStatus: "provider_reported",
    }],
    liabilities: [],
    evidenceRef: "evidence:synthetic_moneytree_read",
    partial: false,
    actionRequired: null,
  };
}

const invalidMutations = [
  ["unknown root key", (value) => { value.unknown = true; }],
  ["unknown account key", (value) => { value.accounts[0].unknown = true; }],
  ["unknown action key", (value) => {
    value.actionRequired = { kind: "provider_outage", sourceLabel: "Moneytree", actionRef: "action:outage" };
    value.actionRequired.unknown = true;
  }],
  ["invalid schema", (value) => { value.schemaVersion = 2; }],
  ["invalid source id", (value) => { value.sourceId = "Moneytree"; }],
  ["invalid consent", (value) => { value.consent = "pending"; }],
  ["invalid freshness", (value) => { value.freshness = "recent"; }],
  ["invalid kind", (value) => { value.accounts[0].kind = "cash"; }],
  ["invalid currency", (value) => { value.accounts[0].currency = "jpy"; }],
  ["invalid status", (value) => { value.accounts[0].verificationStatus = "estimated"; }],
  ["timezone-free date", (value) => { value.asOf = "2026-08-08T06:02:00"; }],
  ["impossible date", (value) => { value.asOf = "2026-02-30T06:02:00Z"; }],
  ["float amount", (value) => { value.accounts[0].balanceMinor = 1.5; }],
  ["unsafe amount", (value) => { value.accounts[0].balanceMinor = Number.MAX_SAFE_INTEGER + 1; }],
  ["string amount", (value) => { value.accounts[0].balanceMinor = "420000"; }],
  ["duplicate account reference", (value) => { value.accounts.push(structuredClone(value.accounts[0])); }],
  ["duplicate liability reference", (value) => {
    value.liabilities = [{ accountRef: value.accounts[0].accountRef, label: "債務", currency: "JPY", balanceMinor: 1, verificationStatus: "provider_reported" }];
  }],
  ["locally estimated amount", (value) => { value.accounts[0].verificationStatus = "locally_estimated"; }],
  ["unavailable amount", (value) => { value.accounts[0].verificationStatus = "unavailable"; value.accounts[0].balanceMinor = 1; }],
  ["provider null amount", (value) => { value.accounts[0].balanceMinor = null; }],
  ["expired without reconsent", (value) => { value.consent = "expired"; value.freshness = "fresh"; }],
  ["revoked without unavailable", (value) => { value.consent = "revoked"; value.freshness = "stale"; value.partial = true; }],
  ["fresh non-valid consent", (value) => { value.consent = "unknown"; }],
  ["fresh without account", (value) => { value.accounts = []; }],
  ["stale without partial", (value) => { value.freshness = "stale"; }],
  ["negative liability", (value) => {
    value.liabilities = [{ accountRef: "source_account:synthetic_loan", label: "サンプルローン", currency: "JPY", balanceMinor: -1, verificationStatus: "provider_reported" }];
    value.partial = true;
  }],
];

function privateMutations() {
  return [
    (value) => { value.accounts[0].label = "口座 123456789012"; return value; },
    (value) => { value.accounts[0].label = "/Users/dais/private/bank"; return value; },
    (value) => { value.accounts[0].label = "https://dais:secret@example.com"; return value; },
    (value) => { value.accounts[0].label = "api_secret_key"; return value; },
    (value) => { value.actionRequired = { kind: "reconsent", sourceLabel: "Moneytree", actionRef: "https://example.com/reconsent" }; return value; },
    (value) => { value.actionRequired = { kind: "reconsent", sourceLabel: "Moneytree", actionRef: "not-an-action" }; return value; },
  ];
}

function assertInvalid(value) {
  assert.throws(() => validateFinancialSourceResult(value), /^Error: cfo_financial_source_invalid:/);
}

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
  for (const mutate of privateMutations()) assertInvalid(mutate(validResult()));
});

test("closed schema and state invariants reject invalid mutations", () => {
  for (const [name, mutate] of invalidMutations) {
    assert.throws(() => validateFinancialSourceResult(mutate(structuredClone(validResult()))), /^Error: cfo_financial_source_invalid:/, name);
  }
});

test("valid stale, partial liability, and reconsent states remain normalized", () => {
  const stale = validResult();
  stale.freshness = "stale";
  stale.partial = true;
  assert.equal(validateFinancialSourceResult(stale).freshness, "stale");

  const partial = validResult();
  partial.partial = true;
  partial.liabilities = [{ accountRef: "source_account:synthetic_loan", label: "サンプルローン", currency: "JPY", balanceMinor: 120000, verificationStatus: "provider_reported" }];
  assert.equal(validateFinancialSourceResult(partial).liabilities[0].balanceMinor, 120000);

  const reconsent = validResult();
  reconsent.consent = "expired";
  reconsent.freshness = "unavailable";
  reconsent.partial = true;
  reconsent.accounts[0].balanceMinor = null;
  reconsent.accounts[0].verificationStatus = "unavailable";
  reconsent.actionRequired = { kind: "reconsent", sourceLabel: "Moneytree", actionRef: "action:moneytree_reconsent" };
  assert.equal(validateFinancialSourceResult(reconsent).actionRequired.kind, "reconsent");
});
