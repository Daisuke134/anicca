"use strict";

const REQUIRED = Object.freeze({
  account: ["id", "source", "source_ref", "name", "kind", "balance_jpy", "observed_at"],
  transaction: ["id", "source_ref", "account_id", "amount_jpy", "occurred_at"],
  position: ["id", "source_ref", "account_id", "name", "value_jpy", "observed_at"],
  liability: ["id", "source_ref", "name", "balance_jpy", "observed_at"],
});

function validateFinancialRecord(type, record) {
  const fields = REQUIRED[type];
  if (!fields) throw new Error(`unknown financial record type: ${type}`);
  if (!record || typeof record !== "object" || Array.isArray(record)) {
    throw new Error(`${type} must be an object`);
  }
  for (const field of fields) {
    if (record[field] === undefined || record[field] === null || record[field] === "") {
      throw new Error(`${type}.${field} is required`);
    }
  }
  if (record.currency && record.currency !== "JPY") {
    throw new Error(`${type}.currency is unsupported`);
  }
  for (const field of ["balance_jpy", "amount_jpy", "value_jpy"]) {
    if (record[field] !== undefined && !Number.isSafeInteger(record[field])) {
      throw new Error(`${type}.${field} must be an integer JPY amount`);
    }
  }
  return record;
}

module.exports = { REQUIRED, validateFinancialRecord };
