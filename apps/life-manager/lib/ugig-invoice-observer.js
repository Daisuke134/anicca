"use strict";

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
const SOLANA_ADDRESS_RE = /^[1-9A-HJ-NP-Za-km-z]{32,44}$/;
const GITHUB_PR_RE = /^https:\/\/github\.com\/[^/]+\/[^/]+\/pull\/[1-9][0-9]*$/;

function validateDelivery(delivery) {
  if (!delivery || typeof delivery !== "object") throw new Error("delivery must be an object");
  if (!UUID_RE.test(delivery.application_id || "")) throw new Error("invalid application_id");
  if (!UUID_RE.test(delivery.gig_id || "")) throw new Error("invalid gig_id");
  if (!Number.isFinite(delivery.amount_usd) || delivery.amount_usd <= 0) {
    throw new Error("amount_usd must be a positive finite number");
  }
  if (delivery.payment_currency !== "sol") throw new Error("payment_currency must be sol");
  if (!SOLANA_ADDRESS_RE.test(delivery.merchant_wallet_address || "")) {
    throw new Error("invalid merchant_wallet_address");
  }
  if (delivery.category !== "code") throw new Error("category must be code");
  if (!Array.isArray(delivery.pr_links) || delivery.pr_links.length === 0 ||
      delivery.pr_links.some((link) => !GITHUB_PR_RE.test(link))) {
    throw new Error("pr_links must contain valid GitHub pull request URLs");
  }
  if (typeof delivery.description !== "string" || delivery.description.trim() === "") {
    throw new Error("description must be non-empty");
  }
}

function invoiceId(invoice) {
  return invoice?.id || invoice?.invoice_id || invoice?.data?.id || invoice?.data?.invoice_id || null;
}

async function observeUgigDeliveries({
  deliveries,
  applications,
  listInvoices,
  isPullRequestMerged,
  createInvoice,
}) {
  if (!Array.isArray(deliveries)) throw new Error("deliveries must be an array");
  if (!Array.isArray(applications)) throw new Error("applications must be an array");
  deliveries.forEach(validateDelivery);

  const result = {
    deliveries_seen: deliveries.length,
    pending: 0,
    waiting_for_merge: 0,
    invoiced: 0,
    invoice_created: 0,
    paid: 0,
    rejected: 0,
    invoices: [],
  };

  for (const delivery of deliveries) {
    const application = applications.find((candidate) =>
      candidate?.id === delivery.application_id &&
      (!candidate.gig_id || candidate.gig_id === delivery.gig_id));

    if (!application) {
      result.rejected += 1;
      continue;
    }
    if (application.status === "pending") {
      result.pending += 1;
      continue;
    }
    if (application.status !== "accepted") {
      result.rejected += 1;
      continue;
    }

    const invoices = await listInvoices(delivery.gig_id);
    const existing = invoices.find((invoice) => invoice?.application_id === delivery.application_id);
    if (existing) {
      result.invoiced += 1;
      if (String(existing.status).toLowerCase() === "paid") result.paid += 1;
      const id = invoiceId(existing);
      if (id) result.invoices.push(id);
      continue;
    }

    const merged = await Promise.all(delivery.pr_links.map(isPullRequestMerged));
    if (merged.some((value) => value !== true)) {
      result.waiting_for_merge += 1;
      continue;
    }

    const payload = {
      application_id: delivery.application_id,
      amount: delivery.amount_usd,
      currency: "USD",
      payment_currency: delivery.payment_currency,
      merchant_wallet_address: delivery.merchant_wallet_address,
      notes: delivery.description,
      category: delivery.category,
      pr_links: delivery.pr_links,
      items: [{
        description: delivery.description,
        quantity: 1,
        unit_price: delivery.amount_usd,
        link: delivery.pr_links[0],
      }],
    };
    const created = await createInvoice(delivery.gig_id, payload);
    const id = invoiceId(created);
    if (!id) throw new Error("uGig invoice creation response did not include an invoice id");
    result.invoice_created += 1;
    result.invoices.push(id);
  }

  return result;
}

module.exports = { observeUgigDeliveries, validateDelivery };
