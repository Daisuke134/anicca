"use strict";

const { createHmac } = require("node:crypto");
const { validateFinancialSourceResult } = require("./cfo-financial-source.js");

const ERROR_PREFIX = "moneytree_adapter_invalid:";
const RFC3339 = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/;
const REF_PREFIXES = { account: "source_account:mt_", transaction: "transaction:mt_", evidence: "evidence:mt_" };

function plain(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    && Object.getPrototypeOf(value) === Object.prototype;
}

function fail(reason) {
  throw new Error(`${ERROR_PREFIX}${reason}`);
}

function parseJson(value, expectedType) {
  if (typeof value !== "string") fail("invalid_json");
  let parsed;
  try { parsed = JSON.parse(value); } catch { fail("invalid_json"); }
  if (!plain(parsed) || !Object.hasOwn(parsed, "type") || !Object.hasOwn(parsed, "data")) fail("invalid_root");
  if (parsed.type !== expectedType) fail("wrong_type");
  if (!plain(parsed.data)) fail("invalid_data");
  return parsed;
}

function keyBytes(referenceKey) {
  if (typeof referenceKey !== "string" || Buffer.byteLength(referenceKey, "utf8") < 32) fail("weak_reference_key");
}

function digest(referenceKey, message) {
  return createHmac("sha256", referenceKey).update(message).digest("hex").slice(0, 24);
}

function opaqueRef(kind, referenceKey, providerId) {
  keyBytes(referenceKey);
  if (!Number.isSafeInteger(providerId)) fail("invalid_provider_id");
  if (!REF_PREFIXES[kind]) fail("invalid_ref_kind");
  return `${REF_PREFIXES[kind]}${digest(referenceKey, `moneytree:${kind}:${providerId}`)}`;
}

function evidenceRef(referenceKey, observedAt, parsed) {
  keyBytes(referenceKey);
  return `evidence:mt_${digest(referenceKey, `moneytree:evidence:${observedAt}:${JSON.stringify(parsed)}`)}`;
}

function adaptMoneytreeAccounts(input) {
  try {
    if (!plain(input)) fail("invalid_input");
    const { accountsJson, observedAt, referenceKey } = input;
    if (typeof observedAt !== "string" || !RFC3339.test(observedAt)) fail("invalid_observed_at");
    const parsed = parseJson(accountsJson, "accounts");
    if (parsed.data.baseCurrency !== "JPY") fail("unsupported_base_currency");
    const groups = parsed.data.accountGroups;
    if (!plain(groups) || !Array.isArray(groups.banks)) fail("invalid_account_groups");

    const selected = [];
    for (const group of groups.banks) {
      if (!plain(group)) fail("invalid_bank_group");
      if (group.institutionKey !== "mufg_bank") continue;
      if (!Array.isArray(group.accounts)) fail("invalid_accounts");
      selected.push(...group.accounts);
    }
    if (selected.length === 0) fail("no_mufg_accounts");

    const providerIds = new Set();
    const accounts = selected.map((account) => {
      if (!plain(account)) fail("invalid_account");
      if (!Number.isSafeInteger(account.id)) fail("invalid_provider_id");
      if (providerIds.has(account.id)) fail("duplicate_provider_id");
      providerIds.add(account.id);
      if (account.currency !== "JPY") fail("unsupported_account_currency");
      if (!Number.isSafeInteger(account.current_balance)) fail("invalid_balance");
      const savings = account.account_subtype === "savings";
      return {
        accountRef: opaqueRef("account", referenceKey, account.id),
        label: savings ? "MUFG 普通預金" : "MUFG 口座",
        kind: savings ? "deposit" : "other",
        currency: "JPY",
        balanceMinor: account.current_balance,
        verificationStatus: "provider_reported",
      };
    });

    return validateFinancialSourceResult({
      schemaVersion: 1,
      sourceId: "moneytree_mufg",
      consent: "valid",
      freshness: "fresh",
      asOf: observedAt,
      accounts,
      liabilities: [],
      evidenceRef: evidenceRef(referenceKey, observedAt, parsed),
      partial: true,
      actionRequired: null,
    });
  } catch (error) {
    if (error && typeof error.message === "string" && error.message.startsWith(ERROR_PREFIX)) throw error;
    throw new Error(`${ERROR_PREFIX}invalid_payload`);
  }
}

module.exports = { adaptMoneytreeAccounts };
