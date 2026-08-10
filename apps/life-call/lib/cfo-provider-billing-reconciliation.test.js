"use strict";
const assert = require("node:assert/strict");
const { test } = require("node:test");
const { normalizeGoogleCloudInvoice, reconcileProviderBilling, allocateProviderBilling } = require("./cfo-provider-billing-reconciliation.js");

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

test("allocates signed official rows with an exact visible remainder", () => {
  const confirmed = normalizeGoogleCloudInvoice(fields, provenance), ref = n => "sha256:" + n.repeat(64);
  const rows = [
    { billing_period: "202608", project_ref: ref("a"), service_ref: ref("b"), sku_ref: null, cost_type: "usage", amount: "1000.25", currency: "JPY", source_row_ref: ref("c") },
    { billing_period: "202608", project_ref: ref("d"), service_ref: null, sku_ref: ref("e"), cost_type: "credit", amount: "-0.25", currency: "JPY", source_row_ref: ref("f") },
    { billing_period: "202608", project_ref: null, service_ref: null, sku_ref: null, cost_type: "tax", amount: "100", currency: "JPY", source_row_ref: ref("1") }
  ];
  const policy = { version: 1, mappings: [{ project_ref: ref("d"), business_id: "business_b" }, { project_ref: ref("a"), business_id: "business_a" }] }, before = structuredClone({ confirmed, rows, policy });
  const result = allocateProviderBilling(confirmed, rows, policy);
  assert.deepEqual(result, { schema_version: 1, status: "allocated", billing_period: "202608", currency: "JPY", policy_version: 1, account_total: "1100", allocated_total: "1000", unallocated_total: "100", row_count: 3, allocated_row_count: 2, unallocated_row_count: 1, businesses: [{ business_id: "business_a", amount: "1000.25" }, { business_id: "business_b", amount: "-0.25" }], evidence_status: "provider_billed_allocated" });
  assert.ok(Object.isFrozen(result) && Object.isFrozen(result.businesses) && result.businesses.every(Object.isFrozen));
  assert.deepEqual({ confirmed, rows, policy }, before);
});

test("fails closed with stable redacted allocation errors", () => {
  const confirmed = normalizeGoogleCloudInvoice(fields, provenance), ref = n => "sha256:" + n.repeat(64), row = amount => ({ billing_period: "202608", project_ref: ref("a"), service_ref: null, sku_ref: null, cost_type: "usage", amount, currency: "JPY", source_row_ref: ref("b") }), policy = { version: 1, mappings: [{ project_ref: ref("a"), business_id: "business" }] };
  for (const input of [
    () => allocateProviderBilling(confirmed, [row("1099")], policy),
    () => allocateProviderBilling(confirmed, [{ ...row("1100"), billing_period: "202607" }], policy),
    () => allocateProviderBilling(confirmed, [{ ...row("1100"), currency: "USD" }], policy),
    () => allocateProviderBilling(confirmed, [row("1100")], { version: 1, mappings: [policy.mappings[0], policy.mappings[0]] }),
    () => allocateProviderBilling(confirmed, [row("1.0")], policy),
    () => allocateProviderBilling(confirmed, new Proxy([row("1100")], {}), policy),
    () => allocateProviderBilling(confirmed, [row("1100")], { version: 1, mappings: [{ get project_ref() { throw new Error("HOSTILE_SENTINEL"); }, business_id: "business" }] })
  ]) assert.throws(input, /^Error: cfo_provider_billing_invalid:invalid_allocation$/);
});

test("rejects coercible nested allocation values without freezing inputs", () => {
  const confirmed = normalizeGoogleCloudInvoice(fields, provenance), ref = n => "sha256:" + n.repeat(64), row = extra => ({ billing_period: "202608", project_ref: ref("a"), service_ref: null, sku_ref: null, cost_type: "usage", amount: "1100", currency: "JPY", source_row_ref: ref("b"), ...extra }), policy = { version: 1, mappings: [{ project_ref: ref("a"), business_id: "business" }] };
  const hostileRef = Object.create({ toString: () => ref("a") }), refRows = [row({ project_ref: hostileRef })], refPolicy = { version: 1, mappings: [{ project_ref: hostileRef, business_id: "business" }] };
  assert.throws(() => allocateProviderBilling(confirmed, refRows, refPolicy), /^Error: cfo_provider_billing_invalid:invalid_allocation$/); assert.equal(Object.isFrozen(hostileRef), false);
  for (const field of ["service_ref", "sku_ref", "source_row_ref"]) { const hostile = Object.create({ toString: () => ref("b") }); assert.throws(() => allocateProviderBilling(confirmed, [row({ [field]: hostile })], policy), /^Error: cfo_provider_billing_invalid:invalid_allocation$/); assert.equal(Object.isFrozen(hostile), false); }
  const hostilePeriod = Object.create({ toString: () => "202608" }), periodConfirmed = { ...confirmed, billing_period: hostilePeriod };
  assert.throws(() => allocateProviderBilling(periodConfirmed, [row({ billing_period: hostilePeriod })], policy), /^Error: cfo_provider_billing_invalid:invalid_allocation$/); assert.equal(Object.isFrozen(hostilePeriod), false);
});
