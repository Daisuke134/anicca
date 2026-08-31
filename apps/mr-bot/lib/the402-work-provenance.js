"use strict";

const TERMINAL = new Set(["completed", "settled", "released"]);
const IDENTIFIER = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/;
const TX = /^0x[0-9a-f]{64}$/;

function identifier(value) {
  const raw = String(value == null ? "" : value);
  return IDENTIFIER.test(raw) ? raw : null;
}

function txHash(value) {
  const raw = String(value == null ? "" : value).toLowerCase();
  return TX.test(raw) ? raw : null;
}

function atomicUsd(value) {
  const raw = String(value == null ? "" : value).trim().replace(/^\$/, "");
  if (!/^\d+(?:\.\d{1,6})?$/.test(raw)) return null;
  const [whole, fraction = ""] = raw.split(".");
  return (BigInt(whole) * 1_000_000n + BigInt(fraction.padEnd(6, "0"))).toString();
}

function root(body) {
  return body && typeof body === "object" && !Array.isArray(body) && body.data != null
    ? body.data
    : body;
}

function rows(body, key) {
  const value = root(body);
  if (Array.isArray(value)) return value;
  return Array.isArray(value && value[key]) ? value[key] : [];
}

function firstIdentifier(object, keys) {
  const values = keys.map((key) => identifier(object && object[key])).filter(Boolean);
  return new Set(values).size === 1 ? values[0] : null;
}

function firstTx(object, keys) {
  const values = keys.map((key) => txHash(object && object[key])).filter(Boolean);
  return new Set(values).size === 1 ? values[0] : null;
}

function settlementMatches(row, settlement) {
  const settlementId = firstIdentifier(settlement, ["settlement_id", "settlementId", "id"]);
  const expectedId = String(row.source_sale_id).slice("the402:".length);
  const tx = firstTx(settlement, [
    "tx_hash", "txHash", "transaction_hash", "transactionHash", "transaction",
  ]);
  const amount = [
    "provider_amount_usd", "providerAmountUsd", "amount_usd", "amountUsd", "amount",
  ].map((key) => atomicUsd(settlement && settlement[key])).filter(Boolean);
  const offerIds = [
    "offer_id", "offerId", "service_id", "serviceId", "product_id", "productId",
  ].map((key) => identifier(settlement && settlement[key])).filter(Boolean);
  return settlementId === expectedId
    && tx === String(row.tx).toLowerCase()
    && new Set(amount).size === 1
    && amount[0] === row.usdc_atomic
    && new Set(offerIds).size === 1
    && offerIds[0] === row.offer_id
    && TERMINAL.has(String(settlement && settlement.status || "").toLowerCase());
}

function jobMatches(job, { jobId, postingId, offerId }) {
  const candidateJobId = firstIdentifier(job, ["job_id", "jobId", "id"]);
  const candidatePostingId = firstIdentifier(job, ["posting_id", "postingId"]);
  const serviceIds = ["service_id", "serviceId", "offer_id", "offerId"]
    .map((key) => identifier(job && job[key])).filter(Boolean);
  const identityMatches = (jobId && candidateJobId === jobId)
    || (postingId && candidatePostingId === postingId);
  return Boolean(identityMatches
    && new Set(serviceIds).size === 1
    && serviceIds[0] === offerId
    && TERMINAL.has(String(job && job.status || "").toLowerCase()));
}

function classifyThe402Revenue(row, evidence = {}) {
  if (!row || row.source !== "the402"
    || typeof row.source_sale_id !== "string" || !/^the402:[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(row.source_sale_id)
    || !identifier(row.offer_id) || !txHash(row.tx)
    || typeof row.usdc_atomic !== "string" || !/^\d+$/.test(row.usdc_atomic)
    || BigInt(row.usdc_atomic) <= 0n) {
    return { kind: "rejected", reason: "invalid_inflow" };
  }

  const settlements = rows(evidence.earnings, "recent_settlements")
    .filter((candidate) => settlementMatches(row, candidate));
  if (settlements.length !== 1) return { kind: "rejected", reason: "settlement_mismatch" };

  const settlement = settlements[0];
  const settlementId = firstIdentifier(settlement, ["settlement_id", "settlementId", "id"]);
  const jobId = firstIdentifier(settlement, ["job_id", "jobId"]);
  const postingId = firstIdentifier(settlement, ["posting_id", "postingId"]);
  if (!jobId && !postingId) {
    return { kind: "sale", settlementId, jobId: null, postingId: null };
  }

  const matches = rows(evidence.jobs, "jobs")
    .filter((candidate) => jobMatches(candidate, { jobId, postingId, offerId: row.offer_id }));
  if (matches.length !== 1) return { kind: "rejected", reason: "job_mismatch" };
  return { kind: "work", settlementId, jobId, postingId };
}

module.exports = { classifyThe402Revenue };
