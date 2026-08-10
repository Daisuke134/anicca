"use strict";
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { normalizeGoogleCloudInvoice, reconcileProviderBilling } = require("./cfo-provider-billing-reconciliation.js");

const fields = { billing_period: "202608", service_period_start: "2026-08-01", service_period_end: "2026-08-31", subtotal: "1000", tax: "100", total: "1100", currency: "JPY" };
const provenance = { billing_account_id: "billing-account-secret", pdf_sha256: "a".repeat(64), observed_at: "2026-08-11T00:00:00.000Z" };

test("normalizes a JPY invoice and reconciles same-scope totals exactly", () => {
  const before = structuredClone({ fields, provenance });
  const confirmed = normalizeGoogleCloudInvoice(fields, provenance);
  const provisional = { schema_version: 1, provider: "google_cloud", billing_period: "202608", scope: confirmed.scope, amount: { value: "999.95", currency: "JPY" }, source_event_ref: "sha256:" + "b".repeat(64), evidence_status: "locally_estimated" };
  const result = reconcileProviderBilling(confirmed, provisional);
  assert.equal(confirmed.amount.value, "1100");
  assert.equal(result.status, "reconciled");
  assert.equal(result.effective, "confirmed");
  assert.equal(result.difference, "100.05");
  assert.deepEqual(result.confirmed, confirmed);
  assert.deepEqual(result.provisional, provisional);
  assert.deepEqual({ fields, provenance }, before);
  assert.ok(Object.isFrozen(confirmed) && Object.isFrozen(confirmed.scope) && Object.isFrozen(result) && Object.isFrozen(result.provisional));
});

test("keeps scope and currency mismatches unresolved", () => {
  const confirmed = normalizeGoogleCloudInvoice(fields, provenance);
  const base = { schema_version: 1, provider: "google_cloud", billing_period: "202608", scope: confirmed.scope, amount: { value: "1100", currency: "USD" }, source_event_ref: "sha256:" + "b".repeat(64), evidence_status: "locally_estimated" };
  const otherScope = { ...base, scope: { kind: "billing_account", ref: "sha256:" + "c".repeat(64) } };
  assert.equal(reconcileProviderBilling(confirmed, otherScope).reason, "scope_mismatch");
  assert.equal(reconcileProviderBilling(confirmed, base).reason, "currency_mismatch");
  assert.equal(reconcileProviderBilling(confirmed, base).difference, null);
});

test("rejects invalid input with redacted stable errors without mutation", () => {
  const invalidFields = { ...fields, total: "900" }, invalidProvenance = { ...provenance, billing_account_id: "HOSTILE_SENTINEL " };
  assert.throws(() => normalizeGoogleCloudInvoice(invalidFields, provenance), /^Error: cfo_provider_billing_invalid:invalid_arithmetic$/);
  assert.throws(() => normalizeGoogleCloudInvoice(fields, invalidProvenance), /^Error: cfo_provider_billing_invalid:invalid_provenance$/);
  assert.throws(() => normalizeGoogleCloudInvoice({ ...fields, billing_period: "202613" }, provenance), /^Error: cfo_provider_billing_invalid:invalid_identity$/);
  const confirmed = normalizeGoogleCloudInvoice(fields, provenance);
  const provisional = { schema_version: 1, provider: "google_cloud", billing_period: "202608", scope: confirmed.scope, amount: { value: "1.25", currency: "JPY" }, source_event_ref: "sha256:" + "b".repeat(64), evidence_status: "locally_estimated" };
  assert.throws(() => reconcileProviderBilling({ ...confirmed, billing_period: "202600" }, provisional), /^Error: cfo_provider_billing_invalid:invalid_confirmed$/);
  assert.throws(() => reconcileProviderBilling(confirmed, { ...provisional, billing_period: "202613" }), /^Error: cfo_provider_billing_invalid:invalid_provisional$/);
  for (const nonCanonical of ["1.0", "1.00"]) assert.throws(() => normalizeGoogleCloudInvoice({ ...fields, subtotal: nonCanonical, tax: "0", total: nonCanonical }, provenance), /^Error: cfo_provider_billing_invalid:invalid_numeric$/);
  assert.equal(normalizeGoogleCloudInvoice({ ...fields, subtotal: "1.25", tax: "0", total: "1.25" }, provenance).amount.value, "1.25");
  assert.throws(() => reconcileProviderBilling(confirmed, { ...provisional, amount: { value: "1.0", currency: "JPY" } }), /^Error: cfo_provider_billing_invalid:invalid_provisional$/);
  assert.deepEqual(invalidFields, { ...fields, total: "900" });
  try { normalizeGoogleCloudInvoice(fields, invalidProvenance); } catch (error) { assert.doesNotMatch(error.message, /HOSTILE_SENTINEL/); }
});
