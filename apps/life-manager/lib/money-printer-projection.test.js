"use strict";

const assert = require("node:assert/strict");
const test = require("node:test");

const { projectMoneyPrinter } = require("./money-printer-projection.js");

const TENANT = "tenant-a";
const OBSERVED_AT = "2026-08-29T00:00:00.000Z";

function fixture(overrides = {}) {
  const opportunity = {
    tenant_id: TENANT,
    opportunity_id: "opportunity-1",
    status: "QUALIFYING",
    amount_minor: "50000",
    currency: "JPY",
    title: "A paid opportunity",
    source_url: "https://example.test/opportunity-1",
  };
  const input = {
    tenantId: TENANT,
    observedAt: OBSERVED_AT,
    opportunities: [opportunity],
    runtimeJobs: [],
    generalReceipts: [],
    applicationReceipts: [],
    humanTasks: [],
    earnings: [],
  };
  if (overrides.foreignTenant) {
    input.opportunities = [{ ...opportunity, tenant_id: "tenant-b" }];
  }
  if (overrides.unverifiedCash) {
    input.earnings = [{
      tenant_id: TENANT,
      entry_key: "earning-1",
      kind: "financial_external_income",
      amount_minor: "100",
      currency: "JPY",
      verified: false,
      occurred_at: OBSERVED_AT,
    }];
  }
  return { ...input, ...overrides };
}

test("projection separates opportunity value from verified cash", () => {
  const view = projectMoneyPrinter(fixture());
  assert.deepEqual(view.metrics.opportunity_value, { JPY: "50000" });
  assert.deepEqual(view.metrics.paid_verified, {});
});

test("projection rejects cross-tenant and unverified money", () => {
  assert.throws(() => projectMoneyPrinter(fixture({ foreignTenant: true })), /tenant/);
  assert.throws(() => projectMoneyPrinter(fixture({ unverifiedCash: true })), /verified/);
});

test("projection keeps mixed currency values separate", () => {
  const base = fixture();
  const view = projectMoneyPrinter({
    ...base,
    opportunities: [
      ...base.opportunities,
      { ...base.opportunities[0], opportunity_id: "opportunity-2", amount_minor: "1000", currency: "USD" },
    ],
    earnings: [
      { tenant_id: TENANT, entry_key: "earning-jpy", amount_minor: "100", currency: "JPY", verified: true, occurred_at: OBSERVED_AT },
      { tenant_id: TENANT, entry_key: "earning-usd", amount_minor: "1000", currency: "USD", verified: true, occurred_at: OBSERVED_AT },
    ],
  });
  assert.deepEqual(view.metrics.opportunity_value, { JPY: "50000", USD: "1000" });
  assert.deepEqual(view.metrics.paid_verified, { JPY: "100", USD: "1000" });
  assert.deepEqual(Object.keys(view.metrics.opportunity_value), ["JPY", "USD"]);
  assert.equal(Object.isFrozen(view.metrics.opportunity_value), true);
  assert.equal(Object.isFrozen(view.metrics.paid_verified), true);
});

test("projection rejects missing or invalid currency for valued rows", () => {
  const base = fixture();
  assert.throws(() => projectMoneyPrinter({
    ...base,
    opportunities: [{ ...base.opportunities[0], currency: null }],
  }), /currency/);
  assert.throws(() => projectMoneyPrinter({
    ...base,
    earnings: [{ tenant_id: TENANT, entry_key: "earning-1", amount_minor: "100", currency: "jpy", verified: true, occurred_at: OBSERVED_AT }],
  }), /currency/);
});
