"use strict";
const crypto = require("node:crypto");
const { types: { isProxy } } = require("node:util");

const ERROR = "cfo_provider_billing_invalid:", FIELDS = ["billing_period", "service_period_start", "service_period_end", "subtotal", "tax", "total", "currency"], PROVENANCE = ["billing_account_id", "pdf_sha256", "observed_at"], AMOUNT = ["value", "currency"], SCOPE = ["kind", "ref"], CONFIRMED = ["schema_version", "provider", "billing_period", "scope", "amount", "source", "source_document_ref", "observed_at", "evidence_status"], PROVISIONAL = ["schema_version", "provider", "billing_period", "scope", "amount", "source_event_ref", "evidence_status"];
const DECIMAL = /^(?:0|[1-9]\d*)(?:\.\d*[1-9])?$/, PERIOD = /^\d{4}(?:0[1-9]|1[0-2])$/, HEX = /^sha256:[0-9a-f]{64}$/;
const fail = reason => { throw new Error(ERROR + reason); };
const plain = value => { try { return value !== null && typeof value === "object" && !Array.isArray(value) && !isProxy(value) && (Object.getPrototypeOf(value) === Object.prototype || Object.getPrototypeOf(value) === null); } catch { return false; } };
function exact(value, keys) { try { return plain(value) && Reflect.ownKeys(value).length === keys.length && keys.every(key => { const d = Object.getOwnPropertyDescriptor(value, key); return d && d.enumerable && Object.prototype.hasOwnProperty.call(d, "value"); }); } catch { return false; } }
const text = value => typeof value === "string" && value.length > 0 && value.trim() === value;
function date(value) { if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false; const parsed = Date.parse(value + "T00:00:00Z"); return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 10) === value; }
function timestamp(value) { return typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)); }
const decimal = value => typeof value === "string" && DECIMAL.test(value);
function parts(value) { const [whole, fraction = ""] = value.split("."); return [BigInt(whole + fraction), fraction.length]; }
function sameDecimal(a, b) { const [av, as] = parts(a), [bv, bs] = parts(b), scale = as > bs ? as : bs; return av * 10n ** BigInt(scale - as) === bv * 10n ** BigInt(scale - bs); }
function difference(a, b) { const [av, as] = parts(a), [bv, bs] = parts(b), scale = as > bs ? as : bs, left = av * 10n ** BigInt(scale - as), right = bv * 10n ** BigInt(scale - bs); let value = left >= right ? left - right : right - left, result = value.toString().padStart(scale + 1, "0"); if (scale) result = result.slice(0, -scale) + "." + result.slice(-scale); result = result.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, ""); return value === 0n ? "0" : left < right ? "-" + result : result; }
function freeze(value) { if (value && typeof value === "object") { Object.values(value).forEach(freeze); Object.freeze(value); } return value; }
function validAmount(value, currency) { return exact(value, AMOUNT) && decimal(value.value) && /^[A-Z]{3}$/.test(value.currency) && (!currency || value.currency === currency); }
function validScope(value) { return exact(value, SCOPE) && value.kind === "billing_account" && HEX.test(value.ref); }
function validConfirmed(value) { return exact(value, CONFIRMED) && value.schema_version === 1 && value.provider === "google_cloud" && PERIOD.test(value.billing_period) && validScope(value.scope) && validAmount(value.amount, "JPY") && value.source === "provider_invoice_pdf" && HEX.test(value.source_document_ref) && timestamp(value.observed_at) && value.evidence_status === "provider_billed"; }
function validProvisional(value) { return exact(value, PROVISIONAL) && value.schema_version === 1 && text(value.provider) && PERIOD.test(value.billing_period) && validScope(value.scope) && validAmount(value.amount) && HEX.test(value.source_event_ref) && value.evidence_status === "locally_estimated"; }
function cloneConfirmed(value) { return { schema_version: 1, provider: value.provider, billing_period: value.billing_period, scope: { kind: value.scope.kind, ref: value.scope.ref }, amount: { value: value.amount.value, currency: value.amount.currency }, source: value.source, source_document_ref: value.source_document_ref, observed_at: value.observed_at, evidence_status: value.evidence_status }; }
function cloneProvisional(value) { return { schema_version: 1, provider: value.provider, billing_period: value.billing_period, scope: { kind: value.scope.kind, ref: value.scope.ref }, amount: { value: value.amount.value, currency: value.amount.currency }, source_event_ref: value.source_event_ref, evidence_status: value.evidence_status }; }
function normalizeGoogleCloudInvoice(fields, provenance) {
  try {
    if (!exact(fields, FIELDS)) fail("invalid_fields"); if (!exact(provenance, PROVENANCE)) fail("invalid_provenance");
    if (!PERIOD.test(fields.billing_period) || !date(fields.service_period_start) || !date(fields.service_period_end) || fields.service_period_start > fields.service_period_end) fail("invalid_identity");
    if (fields.currency !== "JPY" || !decimal(fields.subtotal) || !decimal(fields.tax) || !decimal(fields.total)) fail("invalid_numeric");
    if (!text(provenance.billing_account_id) || !/^[0-9a-f]{64}$/.test(provenance.pdf_sha256) || !timestamp(provenance.observed_at)) fail("invalid_provenance");
    if (!sameDecimal(difference(fields.subtotal, "0"), fields.subtotal) || !sameDecimal(difference(fields.tax, "0"), fields.tax) || !sameDecimal(difference(fields.total, "0"), fields.total)) fail("invalid_numeric");
    if (!sameDecimal(add(fields.subtotal, fields.tax), fields.total)) fail("invalid_arithmetic");
    const scopeRef = "sha256:" + crypto.createHash("sha256").update("google_cloud:" + provenance.billing_account_id, "utf8").digest("hex");
    return freeze({ schema_version: 1, provider: "google_cloud", billing_period: fields.billing_period, scope: { kind: "billing_account", ref: scopeRef }, amount: { value: fields.total, currency: "JPY" }, source: "provider_invoice_pdf", source_document_ref: "sha256:" + provenance.pdf_sha256, observed_at: provenance.observed_at, evidence_status: "provider_billed" });
  } catch (error) { if (error && typeof error.message === "string" && error.message.startsWith(ERROR)) throw error; fail("invalid_input"); }
}
function add(a, b) { const [av, as] = parts(a), [bv, bs] = parts(b), scale = as > bs ? as : bs, value = av * 10n ** BigInt(scale - as) + bv * 10n ** BigInt(scale - bs); let result = value.toString().padStart(scale + 1, "0"); if (scale) result = result.slice(0, -scale) + "." + result.slice(-scale); return result.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, ""); }
function reconcileProviderBilling(confirmed, provisional) {
  try {
    if (!validConfirmed(confirmed)) fail("invalid_confirmed"); if (!validProvisional(provisional)) fail("invalid_provisional");
    const frozenConfirmed = cloneConfirmed(confirmed), frozenProvisional = cloneProvisional(provisional), reason = confirmed.provider !== provisional.provider ? "provider_mismatch" : confirmed.billing_period !== provisional.billing_period ? "period_mismatch" : confirmed.scope.ref !== provisional.scope.ref ? "scope_mismatch" : confirmed.amount.currency !== provisional.amount.currency ? "currency_mismatch" : null;
    return freeze({ confirmed: frozenConfirmed, provisional: frozenProvisional, status: reason ? "unresolved" : "reconciled", reason, effective: reason ? null : "confirmed", difference: reason ? null : difference(confirmed.amount.value, provisional.amount.value) });
  } catch (error) { if (error && typeof error.message === "string" && error.message.startsWith(ERROR)) throw error; fail("invalid_input"); }
}
module.exports = { normalizeGoogleCloudInvoice, reconcileProviderBilling };
